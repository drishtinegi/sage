import re
from pathlib import Path

from pydantic import ValidationError

from brief import extract_json
from evaluator import norm
from llm import generate
from schemas import TopicBrief, WriterResult

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "report.md"
RANK = {"wrong": 0, "missing": 1, "partial": 2}

# statuses: {item number: (status, evidence, note)}
Statuses = dict[int, tuple[str, str, str]]


def gap_order(brief: TopicBrief, statuses: Statuses) -> list[int]:
    gaps = [n for n, (st, _, _) in statuses.items() if st != "covered"]
    return sorted(
        gaps,
        key=lambda n: (
            statuses[n][0] != "wrong",
            -brief.rubric[n - 1].weight,
            RANK[statuses[n][0]],
            n,
        ),
    )


def _grams(s: str, n: int = 6) -> set[str]:
    t = re.findall(r"[a-z0-9]+", s.lower())
    return {" ".join(t[i : i + n]) for i in range(len(t) - n + 1)}


def check_writer(result: WriterResult, gaps: list[int], student_text: str, brief: TopicBrief) -> None:
    got = [p.item for p in result.plan]
    if sorted(got) != sorted(gaps):
        raise ValueError(f"plan must have exactly one entry for each gap {sorted(gaps)}, got {sorted(got)}")

    if not 20 <= len(result.summary) <= 700:
        raise ValueError("summary must be 2 to 3 sentences")
    if "%" in result.summary or re.search(r"\d", result.summary):
        raise ValueError("summary must not contain numbers or percentages")

    text = norm(student_text)
    for m in result.misconceptions:
        parts = [p for p in re.split(r"\.\.\.|…", m.evidence) if norm(p)]
        if not parts:
            raise ValueError("every misconception needs an evidence quote")
        for p in parts:
            if norm(p) not in text:
                raise ValueError(f"misconception evidence is not an exact quote from the student: {p!r}")

    for step in result.plan:
        words = len(step.practice_prompt.split())
        if not 8 <= words <= 60:
            raise ValueError(f"item {step.item}: practice_prompt must be 8 to 50 words, got {words}")
        if not step.why.strip():
            raise ValueError(f"item {step.item}: 'why' is empty")
        if _grams(step.practice_prompt) & _grams(brief.rubric[step.item - 1].text):
            raise ValueError(f"item {step.item}: practice_prompt copies the gap wording, rewrite it")


def write_plan(
    brief: TopicBrief, statuses: Statuses, student_text: str, score: float, attempts: int = 3
) -> WriterResult:
    gaps = gap_order(brief, statuses)
    gap_lines = []
    for n in gaps:
        st, ev, note = statuses[n]
        spec = brief.rubric[n - 1]
        line = f"{n}. [{st.upper()}] (importance {spec.weight} of 3) {spec.text}"
        if ev:
            line += f'\n   student wrote: "{ev}"'
        if note:
            line += f"\n   grader note: {note}"
        gap_lines.append(line)

    prompt = (
        PROMPT_FILE.read_text(encoding="utf-8")
        .replace("<<TOPIC>>", brief.title)
        .replace("<<SCORE>>", f"{score:.0f} out of 100")
        .replace("<<EXPLANATION>>", student_text.strip())
        .replace("<<GAPS>>", "\n".join(gap_lines) or "(none, everything was covered)")
        .replace("<<MISCONCEPTIONS>>", "\n".join(f"- {m}" for m in brief.misconceptions))
    )

    last_error = None
    for _ in range(attempts):
        content = prompt
        if last_error:
            content += f"\n\nYour previous answer was invalid: {last_error}\nFix it and return only the JSON."
        raw = generate(content, "LLM_MODEL_STRONG", temperature=0.3)
        try:
            result = WriterResult.model_validate(extract_json(raw))
            check_writer(result, gaps, student_text, brief)
            by_item = {p.item: p for p in result.plan}
            result.plan = [by_item[n] for n in gaps]  # priority order set by code
            return result
        except (ValueError, ValidationError) as e:
            last_error = str(e)
            print(f"  (writer retrying: {last_error[:140]})")
    raise RuntimeError(f"report writer failed after {attempts} attempts: {last_error}")