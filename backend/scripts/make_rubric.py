import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError

from llm import generate
from schemas import TopicBrief

from brief import make_brief

ROOT = Path(__file__).resolve().parents[2]

PROMPT_FILE = ROOT / "prompts" / "brief.md"
TOPICS_FILE = ROOT / "evals" / "topics.json"
OUT_DIR = ROOT / "evals" / "rubrics"

# client = Anthropic()


# def extract_json(raw: str) -> dict:
#     start, end = raw.find("{"), raw.rfind("}")
#     if start == -1 or end == -1:
#         raise ValueError("no JSON object found in model output")
#     return json.loads(raw[start : end + 1])

# def make_brief(title: str, notes: str = "", attempts: int = 2) -> TopicBrief:
#     prompt = (
#         PROMPT_FILE.read_text(encoding="utf-8")
#         .replace("<<TOPIC>>", title)
#         .replace("<<NOTES>>", notes or "(none)")
#     )
#     last_error = None
#     for _ in range(attempts):
#         content = prompt
#         if last_error:
#             content += f"\n\nYour previous answer was invalid: {last_error}\nFix it and return only the JSON."
#         raw = generate(content, "LLM_MODEL_STRONG")
#         try:
#             return TopicBrief.model_validate(extract_json(raw))
#         except (ValueError, ValidationError) as e:
#             last_error = str(e)
#     raise RuntimeError(f"brief failed after {attempts} attempts: {last_error}")


def show(brief: TopicBrief) -> None:
    print(f"\n=== {brief.title} ===")
    print("Key ideas:     ", "; ".join(brief.concept_map.key_ideas))
    print("Prerequisites: ", "; ".join(brief.concept_map.prerequisites))
    print("Misconceptions:")
    for m in brief.misconceptions:
        print(f"  - {m}")
    print("Rubric:")
    for i, item in enumerate(brief.rubric, 1):
        print(f"  {i:>2}. [w{item.weight}] {item.text}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="topic id from evals/topics.json")
    ap.add_argument("--all", action="store_true", help="run all topics")
    ap.add_argument("--notes", help="path to a text file of notes (use with --topic)")
    args = ap.parse_args()

    topics = {t["id"]: t for t in json.loads(TOPICS_FILE.read_text(encoding="utf-8"))}
    ids = list(topics) if args.all else [args.topic]
    if not ids or ids == [None] or any(i not in topics for i in ids):
        sys.exit(f"Use --all or --topic one of: {', '.join(topics)}")

    notes = Path(args.notes).read_text(encoding="utf-8") if args.notes else ""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for tid in ids:
        brief = make_brief(topics[tid]["title"], notes)
        (OUT_DIR / f"{tid}.json").write_text(brief.model_dump_json(indent=2), encoding="utf-8")
        show(brief)


if __name__ == "__main__":
    main()