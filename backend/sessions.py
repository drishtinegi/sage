import logging
import os
import time
from datetime import datetime
import re

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session, object_session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db import get_db
from evaluator import evaluate, score
from models import ItemStatus, StudySession, Topic, Turn, Plan
from persona import ask_beginner
from schemas import (
    ConceptMap, EvalResult, ItemEval, ReportItem, ReportOut, RubricItem as RubricSpec,
    SessionCreate, SessionOut, TopicBrief, TurnCreate, TurnOut, MessageOut, SessionState, MisconceptionShown, PlanOut, PlanStepOut, HistoryItem
)
from report_writer import write_plan



log = logging.getLogger("explainback")
router = APIRouter(prefix="/sessions", tags=["sessions"])

TURN_CAP = int(os.getenv("TURN_CAP", "12"))
FALLBACK_QUESTION = "Wait, can you explain that part again in simpler words?"
DONE_MESSAGE = "Oh, I think I get it now. Thank you!"
CAP_MESSAGE = "Thanks, that really helped. Let's see how you did!"


def load_brief(topic: Topic) -> TopicBrief:
    return TopicBrief(
        title=topic.title,
        concept_map=ConceptMap(**topic.concept_map),
        misconceptions=[i.text for i in topic.items if i.is_misconception],
        rubric=[RubricSpec(text=i.text, weight=i.weight) for i in topic.items if not i.is_misconception],
    )


def learner_id(x_learner: str | None = Header(default=None)) -> str | None:
    if x_learner and re.fullmatch(r"[A-Za-z0-9-]{16,64}", x_learner):
        return x_learner
    return None


def get_session(db: Session, session_id: int, learner: str | None = None) -> StudySession:
    s = db.get(StudySession, session_id)
    if not s or (s.owner and s.owner != learner):
        raise HTTPException(404, "session not found")
    return s

def last_statuses(s: StudySession) -> dict[int, tuple[str, str, str]]:
    last = max(r.turn_number for r in s.statuses)
    return {r.position: (r.status, r.evidence, r.note) for r in s.statuses if r.turn_number == last}

def attempt_info(s: StudySession):
    """Returns (attempt number, previous score, items fixed since last attempt)."""
    if not s.owner:
        return 1, None, []
    db = object_session(s)
    rows = db.scalars(
        select(StudySession)
        .where(
            StudySession.owner == s.owner,
            StudySession.topic_id == s.topic_id,
            StudySession.status == "finished",
        )
        .order_by(StudySession.started_at, StudySession.id)
    ).all()
    ids = [r.id for r in rows]
    if s.id not in ids:
        return 1, None, []
    idx = ids.index(s.id)
    if idx == 0:
        return 1, None, []
    prev = rows[idx - 1]
    prev_st = last_statuses(prev) if prev.statuses else {}
    cur = last_statuses(s)
    fixed = [n for n, (st, _, _) in cur.items()
             if st == "covered" and prev_st.get(n, ("", "", ""))[0] != "covered"]
    return idx + 1, prev.score, fixed

def plan_to_out(s: StudySession, plan: Plan) -> PlanOut:
    brief = load_brief(s.topic)
    statuses = last_statuses(s)
    steps = []
    for st in plan.steps:
        n = st["item"]
        spec = brief.rubric[n - 1]
        steps.append(PlanStepOut(
            position=n, text=spec.text, weight=spec.weight, status=statuses[n][0],
            kind=st["kind"], why=st["why"], practice_prompt=st["practice_prompt"],
        ))
    return PlanOut(
        summary=plan.summary,
        misconceptions=[MisconceptionShown(**m) for m in plan.misconceptions],
        steps=steps,
    )


@router.get("/{session_id}/plan", response_model=PlanOut)
def get_plan(session_id: int, db: Session = Depends(get_db), learner: str | None = Depends(learner_id)):
    s = get_session(db, session_id, learner)
    if s.status == "active":
        raise HTTPException(409, "the plan is available after the session ends")
    if not s.statuses:
        raise HTTPException(400, "nothing to plan yet")

    plan = db.scalars(select(Plan).where(Plan.session_id == s.id)).first()
    if not plan:
        student_text = "\n".join(t.text for t in s.turns if t.role == "student")
        try:
            data = write_plan(load_brief(s.topic), last_statuses(s), student_text, s.score or 0.0)
        except Exception as e:
            log.exception("report writer failed")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                raise HTTPException(503, "The AI service has reached its usage limit. Please try again later.")
            raise HTTPException(502, "Could not process that right now. Please try again.")
        plan = Plan(
            session_id=s.id,
            summary=data.summary,
            misconceptions=[m.model_dump() for m in data.misconceptions],
            steps=[p.model_dump() for p in data.plan],
        )
        db.add(plan)
        try:
            db.commit()
        except IntegrityError:  # a parallel request stored it first
            db.rollback()
            plan = db.scalars(select(Plan).where(Plan.session_id == session_id)).first()
    return plan_to_out(s, plan)

def build_report(s: StudySession) -> ReportOut:
    brief = load_brief(s.topic)
    last = max(r.turn_number for r in s.statuses)
    rows = {r.position: r for r in s.statuses if r.turn_number == last}
    items = []
    for n, spec in enumerate(brief.rubric, 1):
        r = rows[n]
        items.append(ReportItem(
            position=n, text=spec.text, weight=spec.weight,
            status=r.status, evidence=r.evidence, note=r.note,
        ))
    attempt, prev_score, fixed = attempt_info(s)
    return ReportOut(
        session_id=s.id, topic_title=s.topic.title, score=s.score or 0.0,
        ended_by=s.ended_by or "", items=items,
        attempt=attempt, previous_score=prev_score, fixed=fixed,
    )


@router.post("", response_model=SessionOut)
def create_session(body: SessionCreate, db: Session = Depends(get_db), learner: str | None = Depends(learner_id)):
    topic = db.get(Topic, body.topic_id)
    if not topic:
        raise HTTPException(404, "topic not found")
    s = StudySession(topic_id=topic.id, owner=learner)
    db.add(s)
    db.commit()
    db.refresh(s)
    return SessionOut(
        session_id=s.id,
        topic_title=topic.title,
        opening=f"Hi! I know nothing about {topic.title}. Can you explain it to me?",
        turn_cap=TURN_CAP,
    )


@router.post("/{session_id}/turns", response_model=TurnOut)
def add_turn(session_id: int, body: TurnCreate, db: Session = Depends(get_db), learner: str | None = Depends(learner_id)):
    s = get_session(db, session_id, learner)
    if s.status != "active":
        raise HTTPException(409, "this session has ended")
    text = body.text.strip()
    if not text:
        raise HTTPException(422, "message is empty")

    brief = load_brief(s.topic)
    student = [t.text for t in s.turns if t.role == "student"]
    beginner = [t.text for t in s.turns if t.role == "beginner"]
    number = len(student) + 1
    student.append(text)

    t0 = time.time()
    try:
        result = evaluate(brief, "\n".join(student))
    except Exception as e:
        log.exception("evaluator failed")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise HTTPException(503, "The AI service has reached its usage limit. Please try again later.")
        raise HTTPException(502, "Could not process that right now. Please try again.")

    ended_by, question, problems = None, None, []
    if result.target_item is None:
        ended_by = "all items covered"
    elif number >= TURN_CAP:
        ended_by = "turn cap"
    else:
        try:
            question, problems = ask_beginner(brief, brief.title, student, beginner, result.target_focus)
        except Exception:
            log.exception("persona failed")
            question, problems = "", ["persona call failed"]
        if problems or not question:
            problems = problems + [f"rejected: {question}"]
            question = FALLBACK_QUESTION  # safe generic question instead of a flagged one
    elapsed = round(time.time() - t0, 1)

    db.add(Turn(session_id=s.id, number=number, role="student", text=text))
    for e in result.items:
        db.add(ItemStatus(
            session_id=s.id, turn_number=number, position=e.item,
            status=e.status, evidence=e.evidence, note=e.note,
        ))
    if question:
        db.add(Turn(
            session_id=s.id, number=number, role="beginner", text=question,
            target_item=result.target_item, focus=result.target_focus,
            leak_problems=problems, seconds=elapsed,
        ))
    if ended_by:
        s.status = "finished"
        s.ended_by = ended_by
        s.ended_at = datetime.utcnow()
        s.score = score(brief, result)
    db.commit()

    reply = question or (DONE_MESSAGE if ended_by == "all items covered" else CAP_MESSAGE)
    return TurnOut(turn=number, beginner=reply, ended=bool(ended_by), ended_by=ended_by, seconds=elapsed)


@router.post("/{session_id}/finish", response_model=ReportOut)
def finish_session(session_id: int, db: Session = Depends(get_db), learner: str | None = Depends(learner_id)):
    s = get_session(db, session_id, learner)
    if s.status == "active":
        if not s.statuses:
            raise HTTPException(400, "Nothing to report yet. Explain the topic first.")
        brief = load_brief(s.topic)
        last = max(r.turn_number for r in s.statuses)
        result = EvalResult(items=[
            ItemEval(item=r.position, status=r.status, evidence=r.evidence, note=r.note)
            for r in s.statuses if r.turn_number == last
        ])
        s.status = "finished"
        s.ended_by = "student tapped finish"
        s.ended_at = datetime.utcnow()
        s.score = score(brief, result)
        db.commit()
        db.refresh(s)
    return build_report(s)

@router.get("/{session_id}", response_model=SessionState)
def get_state(session_id: int, db: Session = Depends(get_db), learner: str | None = Depends(learner_id)):
    s = get_session(db, session_id, learner)
    opening = f"Hi! I know nothing about {s.topic.title}. Can you explain it to me?"
    msgs = [MessageOut(role="beginner", text=opening)]
    msgs += [MessageOut(role=t.role, text=t.text) for t in s.turns]
    if s.status == "finished" and s.ended_by == "all items covered":
        msgs.append(MessageOut(role="beginner", text=DONE_MESSAGE))
    elif s.status == "finished" and s.ended_by == "turn cap":
        msgs.append(MessageOut(role="beginner", text=CAP_MESSAGE))
    return SessionState(
        session_id=s.id, topic_id=s.topic_id, topic_title=s.topic.title,
        turn_cap=TURN_CAP, status=s.status, ended_by=s.ended_by,
        turn=sum(1 for t in s.turns if t.role == "student"),
        messages=msgs,
    )

@router.get("/{session_id}/report", response_model=ReportOut)
def get_report(session_id: int, db: Session = Depends(get_db), learner: str | None = Depends(learner_id)):
    s = get_session(db, session_id, learner)
    if s.status == "active":
        raise HTTPException(409, "the report is available after the session ends")
    return build_report(s)


history_router = APIRouter(tags=["history"])


@history_router.get("/history", response_model=list[HistoryItem])
def history(db: Session = Depends(get_db), learner: str | None = Depends(learner_id)):
    if not learner:
        return []
    rows = db.scalars(
        select(StudySession)
        .where(StudySession.owner == learner, StudySession.status == "finished")
        .order_by(StudySession.started_at, StudySession.id)
    ).all()
    counts, out = {}, []
    for r in rows:
        counts[r.topic_id] = counts.get(r.topic_id, 0) + 1
        out.append(HistoryItem(
            session_id=r.id, topic_id=r.topic_id, topic_title=r.topic.title,
            attempt=counts[r.topic_id], score=r.score or 0.0,
            ended_by=r.ended_by or "", ended_at=r.ended_at,
        ))
    return list(reversed(out))[:30]