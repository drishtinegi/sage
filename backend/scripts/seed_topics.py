import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from db import Base, SessionLocal, engine
from models import RubricItem, Topic
from schemas import TopicBrief

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for f in sorted((ROOT / "evals" / "rubrics").glob("*.json")):
            brief = TopicBrief.model_validate_json(f.read_text(encoding="utf-8"))
            exists = db.scalars(
                select(Topic).where(
                    func.lower(Topic.title) == brief.title.lower(),
                    Topic.source_notes.is_(None),
                )
            ).first()
            if exists:
                print(f"skip {brief.title} (id {exists.id}, already stored)")
                continue
            topic = Topic(title=brief.title, source_notes=None, concept_map=brief.concept_map.model_dump())
            for pos, item in enumerate(brief.rubric, 1):
                topic.items.append(RubricItem(position=pos, text=item.text, weight=item.weight, is_misconception=False))
            for pos, m in enumerate(brief.misconceptions, len(brief.rubric) + 1):
                topic.items.append(RubricItem(position=pos, text=m, weight=0, is_misconception=True))
            db.add(topic)
            db.commit()
            print(f"added {brief.title} (id {topic.id}, {len(brief.rubric)} items)")


if __name__ == "__main__":
    main()