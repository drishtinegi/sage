import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluate import evaluate, score, show
from persona import ask_beginner
from schemas import TopicBrief

from evaluator import POINTS, check_result, evaluate, score  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
RUBRIC_DIR = ROOT / "evals" / "rubrics"
OUT_DIR = ROOT / "evals" / "transcripts"
TURN_CAP = 12


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--title", help="display title (default: from rubric)")
    ap.add_argument("--replay", help="text file: each non-empty line is one student turn")
    args = ap.parse_args()

    brief = TopicBrief.model_validate_json(
        (RUBRIC_DIR / f"{args.topic}.json").read_text(encoding="utf-8")
    )
    title = args.title or brief.title
    replay = None
    if args.replay:
        lines = Path(args.replay).read_text(encoding="utf-8").splitlines()
        replay = [l.strip() for l in lines if l.strip()]

    print(f"\nBeginner: Hi! I know nothing about {title}. Can you explain it to me?")
    print("(type your explanation; /finish to end)\n")

    student, beginner, log, latencies = [], [], [], []
    result, ended_by = None, "turn cap"

    for turn in range(1, TURN_CAP + 1):
        if replay is not None:
            if not replay:
                ended_by = "replay finished"
                break
            msg = replay.pop(0)
            print(f"You: {msg}")
        else:
            msg = input("You: ").strip()
            if msg.lower() in {"/finish", "/quit"}:
                ended_by = "student tapped finish"
                break
            if not msg:
                continue

        student.append(msg)
        t0 = time.time()
        result = evaluate(brief, "\n".join(student))
        t1 = time.time()

        if result.target_item is None:
            print("\nBeginner: Oh, I think I get it now. Thank you!\n")
            ended_by = "all items covered"
            break

        question, problems = ask_beginner(brief, title, student, beginner, result.target_focus)
        t2 = time.time()
        beginner.append(question)
        latencies.append(t2 - t0)

        print(f"\nBeginner: {question}")
        print(f"  [eval {t1 - t0:.1f}s + persona {t2 - t1:.1f}s | target item {result.target_item}: {result.target_focus}]")
        if problems:
            print(f"  [LEAK WARNING: {'; '.join(problems)}]")
        print()

        log.append({
            "turn": turn, "student": msg, "beginner": question,
            "target_item": result.target_item, "focus": result.target_focus,
            "leak_problems": problems, "seconds": round(t2 - t0, 1),
        })
    else:
        ended_by = "turn cap"

    if not student or result is None:
        print("No explanation given, nothing to report.")
        return

    print(f"\n=== Session ended ({ended_by}). Hidden report ===")
    show(brief, result)
    if latencies:
        print(f"\nMedian reply time: {statistics.median(latencies):.1f}s over {len(latencies)} turns (target: under 5s)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.topic}_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps({
        "topic": args.topic, "ended_by": ended_by,
        "score": score(brief, result), "turns": log,
    }, indent=2), encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()