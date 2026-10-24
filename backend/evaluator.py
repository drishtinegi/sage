import re
from pathlib import Path

from pydantic import ValidationError

from brief import extract_json
from llm import generate
from schemas import EvalResult, TopicBrief

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "evaluator.md"

POINTS = {"covered": 1.0, "partial": 0.5, "missing": 0.0, "wrong": 0.0}


def norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def check_result(result: EvalResult, n_items: int, explanation: str) -> None:
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
    if result.target_item is not None and not result.target_focus.strip():
        raise ValueError("target_item is set, so target_focus must not be empty")


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