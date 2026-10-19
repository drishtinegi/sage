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