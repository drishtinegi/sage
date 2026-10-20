import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError

from brief import extract_json
from llm import generate
from schemas import EvalResult, TopicBrief

ROOT = Path(__file__).resolve().parents[2]
PROMPT_FILE = ROOT / "prompts" / "evaluator.md"
RUBRIC_DIR = ROOT / "evals" / "rubrics"
EXPL_DIR = ROOT / "evals" / "explanations"
RESULT_DIR = ROOT / "evals" / "results"

POINTS = {"covered": 1.0, "partial": 0.5, "missing": 0.0, "wrong": 0.0}


def norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def check_result(result: EvalResult, n_items: int, explanation: str) -> None:
    """Raise ValueError if the evaluator output breaks the rules."""
    numbers = sorted(i.item for i in result.items)
    if numbers != list(range(1, n_items + 1)):
        raise ValueError(f"need exactly one entry for items 1..{n_items}, got {numbers}")

    text = norm(explanation)
    for it in result.items:
        if it.status == "missing":
            continue
        parts = [p for p in re.split(r"\.\.\.|…", it.evidence) if norm(p)]
        if not parts:
            raise ValueError(f"item {it.item} is '{it.status}' but has no evidence quote")
        for p in parts:
            if norm(p) not in text:
                raise ValueError(
                    f"item {it.item}: evidence is not an exact quote from the student: {p!r}"
                )

    not_covered = [i.item for i in result.items if i.status != "covered"]
    if not_covered:
        if result.target_item not in not_covered:
            raise ValueError(f"target_item must be one of the uncovered items {not_covered}")
    elif result.target_item is not None:
        raise ValueError("all items covered, so target_item must be null")


def evaluate(brief: TopicBrief, explanation: str, attempts: int = 3) -> EvalResult:
    rubric = "\n".join(f"{i}. [w{it.weight}] {it.text}" for i, it in enumerate(brief.rubric, 1))
    misc = "\n".join(f"- {m}" for m in brief.misconceptions)
    prompt = (
        PROMPT_FILE.read_text(encoding="utf-8")
        .replace("<<RUBRIC>>", rubric)
        .replace("<<MISCONCEPTIONS>>", misc)
        .replace("<<EXPLANATION>>", explanation.strip())
    )
    last_error = None
    for _ in range(attempts):
        content = prompt
        if last_error:
            content += f"\n\nYour previous answer was invalid: {last_error}\nFix it and return only the JSON."
        raw = generate(content, "LLM_MODEL_CHEAP", temperature=0.0)
        try:
            result = EvalResult.model_validate(extract_json(raw))
            check_result(result, len(brief.rubric), explanation)
            return result
        except (ValueError, ValidationError) as e:
            last_error = str(e)
            print(f"  (retrying: {last_error[:120]})")
    raise RuntimeError(f"evaluator failed after {attempts} attempts: {last_error}")


def score(brief: TopicBrief, result: EvalResult) -> float:
    by_item = {i.item: i for i in result.items}
    total = sum(it.weight for it in brief.rubric)
    got = sum(it.weight * POINTS[by_item[n].status] for n, it in enumerate(brief.rubric, 1))
    return round(100 * got / total, 1)


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