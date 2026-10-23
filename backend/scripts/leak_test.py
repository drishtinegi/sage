import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brief import extract_json
from evaluate import evaluate
from llm import generate
from persona import ask_beginner
from schemas import EvalResult, TopicBrief

ROOT = Path(__file__).resolve().parents[2]
RUBRICS = ROOT / "evals" / "rubrics"
EXPL = ROOT / "evals" / "explanations"
RESULTS = ROOT / "evals" / "results"
TOPICS = json.loads((ROOT / "evals" / "topics.json").read_text(encoding="utf-8"))
PROFILES = ["vague", "partial", "misconception", "strong", "messy"]
SAMPLES = 2  # persona questions per student -> 5 topics x 5 profiles x 2 = 50

def make_students(title: str, brief: TopicBrief, attempts: int = 3) -> dict[str, str]:
    prompt = f"""You are simulating undergraduate CSE students to test a study tool.
Topic: {title}
Common misconceptions: {json.dumps(brief.misconceptions)}

Write five DIFFERENT explanations of the topic, 50 to 120 words each, in a student's
own voice. Return only ONE JSON object with exactly these keys, each a plain string:
- "vague": confident tone but only generic statements, no real mechanism or detail
- "partial": accurate, but covers only the first half of the topic and stops
- "misconception": mostly fine, but states one of the common misconceptions as fact
- "strong": accurate and fairly complete
- "messy": casual, run-on wording, a mix of correct and slightly wrong points
Write complete, correctly spaced English words."""
    last = None
    for _ in range(attempts):
        try:
            out = extract_json(generate(prompt, "LLM_MODEL_CHEAP", temperature=0.8))
            if all(isinstance(out.get(p), str) and out[p].strip() for p in PROFILES):
                return out
            last = "missing or non-string keys"
        except (ValueError, json.JSONDecodeError) as e:
            last = str(e)
        print(f"  (retrying student generation: {last[:80]})")
    raise RuntimeError(f"could not generate students: {last}")


def cell(s: str) -> str:
    return s.replace("|", "/").replace("\n", " ").strip()


def main() -> None:
    rows, flagged, skipped = [], 0, 0
    for t in TOPICS:
        tid = t["id"]
        rubric_file = RUBRICS / f"{tid}.json"
        if not rubric_file.exists():
            print(f"skip {tid}: no rubric")
            continue
        brief = TopicBrief.model_validate_json(rubric_file.read_text(encoding="utf-8"))

        missing = [p for p in PROFILES if not (EXPL / f"{tid}_{p}.txt").exists()]
        if missing:
            print(f"[{tid}] generating student explanations...")
            try:
                students = make_students(brief.title, brief)
            except RuntimeError as e:
                print(f"[{tid}] {e}")
                continue
            for p in PROFILES:
                if p in students and p in missing:
                    (EXPL / f"{tid}_{p}.txt").write_text(str(students[p]), encoding="utf-8")

        for p in PROFILES:
            f = EXPL / f"{tid}_{p}.txt"
            if not f.exists():
                continue
            text = f.read_text(encoding="utf-8")
            cache = RESULTS / f"leak_{tid}_{p}.json"
            try:
                if cache.exists():
                    result = EvalResult.model_validate_json(cache.read_text(encoding="utf-8"))
                else:
                    result = evaluate(brief, text)
                    RESULTS.mkdir(parents=True, exist_ok=True)
                    cache.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            except RuntimeError as e:
                print(f"[{tid}/{p}] evaluator failed: {e}")
                skipped += 1
                continue

            if result.target_item is None:
                print(f"[{tid}/{p}] everything covered, no question asked")
                continue

            for s in range(SAMPLES):
                q, problems = ask_beginner(brief, brief.title, [text], [], result.target_focus)
                flagged += bool(problems)
                rows.append((tid, p, result.target_item, result.target_focus, q, "; ".join(problems)))
                print(f"[{tid}/{p}#{s + 1}] {q}" + (f"   <-- FLAG: {problems}" if problems else ""))

    out = ROOT / "evals" / "leak_review.md"
    lines = [
        "| # | topic | student | target | focus | question | auto flags | leak? | lecture? | natural? |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n, (tid, p, ti, focus, q, fl) in enumerate(rows, 1):
        lines.append(f"| {n} | {tid} | {p} | {ti} | {cell(focus)} | {cell(q)} | {cell(fl)} | | | |")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{len(rows)} questions, {flagged} flagged by the automatic check, {skipped} students skipped")
    print(f"Review table: {out}")


if __name__ == "__main__":
    main()