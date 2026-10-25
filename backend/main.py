import logging
import os;

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from brief import make_brief
from db import Base, engine, get_db
from models import RubricItem, Topic
from schemas import TopicCreate, TopicOut
from sessions import router as sessions_router

log = logging.getLogger("explainback")

Base.metadata.create_all(engine)  # creates the tables if they don't exist

app = FastAPI(title="Explain-Back")
app.include_router(sessions_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def to_out(topic: Topic) -> TopicOut:
    count = sum(1 for i in topic.items if not i.is_misconception)
    return TopicOut(id=topic.id, title=topic.title, rubric_count=count)


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}


@app.post("/topics", response_model=TopicOut)
def create_topic(body: TopicCreate, db: Session = Depends(get_db)):
    title = body.title.strip()
    notes = (body.notes or "").strip()

    # Reuse a stored rubric for a plain topic name, so it stays stable and saves API calls
    if not notes:
        existing = db.scalars(
            select(Topic).where(
                func.lower(Topic.title) == title.lower(),
                Topic.source_notes.is_(None),
            )
        ).first()
        if existing:
            return to_out(existing)

    try:
        brief = make_brief(title, notes)
    except Exception:
        log.exception("brief generation failed")
        raise HTTPException(502, "Could not build the topic right now. Please try again.")

    topic = Topic(
        title=title,
        source_notes=notes or None,
        concept_map=brief.concept_map.model_dump(),
    )
    for pos, item in enumerate(brief.rubric, 1):
        topic.items.append(
            RubricItem(position=pos, text=item.text, weight=item.weight, is_misconception=False)
        )
    for pos, m in enumerate(brief.misconceptions, len(brief.rubric) + 1):
        topic.items.append(
            RubricItem(position=pos, text=m, weight=0, is_misconception=True)
        )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return to_out(topic)

@app.get("/topics", response_model=list[TopicOut])
def list_topics(db: Session = Depends(get_db)):
    topics = db.scalars(
        select(Topic).where(Topic.source_notes.is_(None)).order_by(Topic.title)
    ).all()
    return [to_out(t) for t in topics]

@app.get("/topics/{topic_id}/rubric")
def dev_rubric(topic_id: int, db: Session = Depends(get_db)):
    if os.getenv("DEV_ENDPOINTS") != "1":
        raise HTTPException(404, "not found")
        
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "topic not found")
    return {
        "title": topic.title,
        "concept_map": topic.concept_map,
        "rubric": [
            {"position": i.position, "weight": i.weight, "text": i.text}
            for i in topic.items if not i.is_misconception
        ],
        "misconceptions": [i.text for i in topic.items if i.is_misconception],
    }