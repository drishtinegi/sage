import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluator import evaluate, score
from schemas import EvalResult, TopicBrief

ROOT = Path(__file__).resolve().parents[2]
PROMPT_FILE = ROOT / "prompts" / "evaluator.md"
RUBRIC_DIR = ROOT / "evals" / "rubrics"
EXPL_DIR = ROOT / "evals" / "explanations"
RESULT_DIR = ROOT / "evals" / "results"


def show(brief: TopicBrief, result: EvalResult) -> None:
    by_item = {i.item: i for i in result.items}
    print()
    for n, it in enumerate(brief.rubric, 1):
        e = by_item[n]
        print(f"{n:>2}. [{e.status.upper():<7}] (w{it.weight}) {it.text}")
        if e.evidence:
            print(f"      quote: \"{e.evidence}\"")
        if e.note:
            print(f"      note:  {e.note}")
    print(f"\nScore: {score(brief, result)}%")
    if result.target_item:
        t = brief.rubric[result.target_item - 1]
        print(f"Next target: item {result.target_item} - {t.text}")
        print(f"Why: {result.target_reason}")
    else:
        print("Next target: none (everything covered)")


def find_explanation(name: str) -> Path:
    p = Path(name)
    if p.exists():
        return p
    for candidate in (EXPL_DIR / name, EXPL_DIR / f"{name}.txt"):
        if candidate.exists():
            return candidate
    sys.exit(f"Explanation not found: {name} (looked in {EXPL_DIR})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True, help="topic id, e.g. recursion")
    ap.add_argument("--explanation", required=True, help="file name in evals/explanations")
    ap.add_argument("--runs", type=int, default=1, help="repeat to test consistency")
    args = ap.parse_args()

    rubric_file = RUBRIC_DIR / f"{args.topic}.json"
    if not rubric_file.exists():
        sys.exit(f"No rubric at {rubric_file}. Run make_rubric.py first.")
    brief = TopicBrief.model_validate_json(rubric_file.read_text(encoding="utf-8"))

    expl_file = find_explanation(args.explanation)
    explanation = expl_file.read_text(encoding="utf-8")

    results, times = [], []
    for r in range(args.runs):
        start = time.time()
        results.append(evaluate(brief, explanation))
        times.append(time.time() - start)

    show(brief, results[0])
    print(f"\nEvaluator time: {', '.join(f'{t:.1f}s' for t in times)}")

    if args.runs > 1:
        print("\nConsistency across runs:")
        stable = 0
        for n in range(1, len(brief.rubric) + 1):
            statuses = [next(i.status for i in res.items if i.item == n) for res in results]
            same = len(set(statuses)) == 1
            stable += same
            print(f"  item {n}: {', '.join(statuses)}  {'OK' if same else 'DIFFERS'}")
        print(f"  {stable}/{len(brief.rubric)} items identical in every run")

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULT_DIR / f"{args.topic}_{expl_file.stem}.json"
    out.write_text(results[0].model_dump_json(indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()