from typing import Literal

from pydantic import BaseModel, Field, field_validator

from datetime import datetime

class ConceptMap(BaseModel):
    key_ideas: list[str]
    prerequisites: list[str]


class RubricItem(BaseModel):
    text: str
    weight: int = Field(ge=1, le=3)  # 1 = minor, 2 = important, 3 = essential


class TopicBrief(BaseModel):
    title: str
    concept_map: ConceptMap
    misconceptions: list[str]
    rubric: list[RubricItem]

    @field_validator("rubric")
    @classmethod
    def rubric_size(cls, v):
        if not 4 <= len(v) <= 10:
            raise ValueError(f"rubric must have 4 to 10 items, got {len(v)}")
        return v

class TopicCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    notes: str | None = Field(default=None, max_length=20000)


class TopicOut(BaseModel):
    id: int
    title: str
    rubric_count: int
    status: str = "ready"

class ItemEval(BaseModel):
    item: int                      # rubric item number, starting at 1
    status: Literal["covered", "partial", "missing", "wrong"]
    evidence: str = ""             # exact words from the student ("" if missing)
    note: str = ""                 # one short reason



class EvalResult(BaseModel):
    items: list[ItemEval]
    target_item: int | None = None
    target_reason: str = ""
    target_focus: str = ""   # neutral area for the beginner to ask about

class SessionCreate(BaseModel):
    topic_id: int


class SessionOut(BaseModel):
    session_id: int
    topic_title: str
    opening: str
    turn_cap: int


class TurnCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class TurnOut(BaseModel):
    turn: int
    beginner: str
    ended: bool
    ended_by: str | None = None
    seconds: float


class ReportItem(BaseModel):
    position: int
    text: str
    weight: int
    status: str
    evidence: str
    note: str

class ReportOut(BaseModel):
    session_id: int
    topic_title: str
    score: float
    ended_by: str
    items: list[ReportItem]
    attempt: int = 1
    previous_score: float | None = None
    fixed: list[int] = []     # rubric items not covered last time, covered now


class MessageOut(BaseModel):
    role: str
    text: str


class SessionState(BaseModel):
    session_id: int
    topic_id: int
    topic_title: str
    turn_cap: int
    status: str            # active | finished
    ended_by: str | None = None
    turn: int
    messages: list[MessageOut]

class MisconceptionShown(BaseModel):
    belief: str
    evidence: str


class WriterStep(BaseModel):
    item: int
    kind: Literal["re-explain", "practice question"]
    why: str
    practice_prompt: str


class WriterResult(BaseModel):
    summary: str
    misconceptions: list[MisconceptionShown] = []
    plan: list[WriterStep]


class PlanStepOut(BaseModel):
    position: int
    text: str
    weight: int
    status: str
    kind: str
    why: str
    practice_prompt: str


class PlanOut(BaseModel):
    summary: str
    misconceptions: list[MisconceptionShown]
    steps: list[PlanStepOut]

class HistoryItem(BaseModel):
    session_id: int
    topic_id: int
    topic_title: str
    attempt: int
    score: float
    ended_by: str
    ended_at: datetime | None = None