import json
from pathlib import Path

from pydantic import ValidationError

from llm import generate
from schemas import TopicBrief

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "brief.md"


def extract_json(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model output")
    return json.loads(raw[start : end + 1])


def make_brief(title: str, notes: str = "", attempts: int = 2) -> TopicBrief:
    prompt = (
        PROMPT_FILE.read_text(encoding="utf-8")
        .replace("<<TOPIC>>", title)
        .replace("<<NOTES>>", notes or "(none)")
    )
    last_error = None
    for _ in range(attempts):
        content = prompt
        if last_error:
            content += f"\n\nYour previous answer was invalid: {last_error}\nFix it and return only the JSON."
        raw = generate(content, "LLM_MODEL_STRONG")
        try:
            return TopicBrief.model_validate(extract_json(raw))
        except (ValueError, ValidationError) as e:
            last_error = str(e)
    raise RuntimeError(f"brief failed after {attempts} attempts: {last_error}")