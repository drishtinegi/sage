from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    source_notes: Mapped[str | None] = mapped_column(Text, default=None)
    concept_map: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    items: Mapped[list["RubricItem"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
        order_by="RubricItem.position",
    )


class RubricItem(Base):
    __tablename__ = "rubric_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    position: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    weight: Mapped[int]  # 1 to 3 for rubric items, 0 for misconceptions
    is_misconception: Mapped[bool] = mapped_column(default=False)

    topic: Mapped["Topic"] = relationship(back_populates="items")

class StudySession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    persona_level: Mapped[str] = mapped_column(default="beginner")
    status: Mapped[str] = mapped_column(default="active")  # active | finished
    ended_by: Mapped[str | None] = mapped_column(default=None)
    score: Mapped[float | None] = mapped_column(default=None)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(default=None)

    topic: Mapped["Topic"] = relationship()
    turns: Mapped[list["Turn"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Turn.id"
    )
    statuses: Mapped[list["ItemStatus"]] = relationship(cascade="all, delete-orphan")


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    number: Mapped[int]                 # exchange number, 1, 2, 3...
    role: Mapped[str]                   # "student" or "beginner"
    text: Mapped[str] = mapped_column(Text)
    target_item: Mapped[int | None] = mapped_column(default=None)
    focus: Mapped[str | None] = mapped_column(default=None)
    leak_problems: Mapped[list] = mapped_column(JSON, default=list)
    seconds: Mapped[float | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    session: Mapped["StudySession"] = relationship(back_populates="turns")


class ItemStatus(Base):
    __tablename__ = "item_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    turn_number: Mapped[int]
    position: Mapped[int]               # rubric item number, 1..n
    status: Mapped[str]
    evidence: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")