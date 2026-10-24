import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brief import extract_json
from llm import generate

ROOT = Path(__file__).resolve().parents[2]


def letters(s: str) -> str:
    return re.sub(r"\s+", "", s)


def fix(texts: list[str]) -> list[str]:
    prompt = (
        "Fix ONLY spacing errors (words stuck together, like 'asa' -> 'as a') in each string. "
        "Do not change, add or remove any letters, words or punctuation otherwise. "
        'Return JSON: {"texts": [...]} with the same number of strings in the same order.\n\n'
        + json.dumps({"texts": texts})
    )
    out = extract_json(generate(prompt, "LLM_MODEL_CHEAP", temperature=0.0))["texts"]
    if len(out) != len(texts):
        return texts
    return [new if letters(new) == letters(old) else old for old, new in zip(texts, out)]


def main() -> None:
    for f in sorted((ROOT / "evals" / "rubrics").glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        data["title"] = data["title"].replace(" Answer Key", "").strip()
        texts = [i["text"] for i in data["rubric"]] + data["misconceptions"]
        fixed = fix(texts)
        n = len(data["rubric"])
        for item, t in zip(data["rubric"], fixed[:n]):
            item["text"] = t
        data["misconceptions"] = fixed[n:]
        changed = [(o, t) for o, t in zip(texts, fixed) if o != t]
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{f.name}: {len(changed)} texts fixed")
        for o, t in changed:
            print(f"   - {o}\n   + {t}")


if __name__ == "__main__":
    main()