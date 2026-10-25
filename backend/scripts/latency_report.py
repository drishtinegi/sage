import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import SessionLocal
from models import Turn


def main() -> None:
    with SessionLocal() as db:
        rows = db.query(Turn).filter(Turn.role == "beginner", Turn.seconds.is_not(None)).all()
    secs = sorted(r.seconds for r in rows)
    if not secs:
        print("no timed turns yet")
        return
    p90 = secs[int(0.9 * (len(secs) - 1))]
    print(f"turns: {len(secs)}")
    print(f"median: {statistics.median(secs):.1f}s   p90: {p90:.1f}s   max: {secs[-1]:.1f}s")
    print(f"under 5s: {100 * sum(s < 5 for s in secs) / len(secs):.0f}%  (PRD target: median under 5s)")


if __name__ == "__main__":
    main()