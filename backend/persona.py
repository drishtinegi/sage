import re
from pathlib import Path

from llm import generate
from schemas import TopicBrief

from wordfreq import word_frequency

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "persona.md"

WORD = re.compile(r"[a-z]{5,}")

# everyday words that are fine in a beginner's question (extend as false alarms appear)
COMMON = {
    "about", "after", "again", "always", "because", "before", "being", "could", "does",
    "doing", "every", "explain", "explains", "first", "happens", "happen", "other",
    "right", "should", "still", "their", "there", "these", "thing", "things", "think",
    "those", "through", "under", "using", "where", "which", "while", "would", "works",
    "work", "means", "makes", "called", "simple", "exactly", "different", "understand",
    "basically", "confused", "wondering", "actually", "really", "never", "something",
    "anything", "example", "states", "describes", "defines", "mean", "stuff", "another",
    "without", "another", "running", "run", "start",
}

def _words(s: str) -> set[str]:
    out = set()
    for w in WORD.findall(s.lower()):
        for suf in ("ing", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[: -len(suf)]
                if len(w) >= 3 and w[-1] == w[-2]:   # runn -> run
                    w = w[:-1]
                break
        out.add(w)
    return out

def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def _ngrams(tokens: list[str], n: int = 4) -> set[str]:
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def leak_problems(question, brief: TopicBrief, student_text, title, earlier) -> list[str]:
    problems = []
    q = question.strip()
    if q.count("?") != 1 or not q.endswith("?"):
        problems.append("must be exactly one question ending with a question mark")
    if len(q.split()) > 40:
        problems.append("too long, keep it under 35 words")

    key_texts = [i.text for i in brief.rubric] + brief.misconceptions
    q_grams = _ngrams(_tokens(q))
    if any(q_grams & _ngrams(_tokens(t)) for t in key_texts):
        problems.append("copies wording from the answer key")

    vocab = set()
    for t in key_texts:
        vocab |= _words(t)
    allowed = _words(student_text) | _words(title) | _words(" ".join(earlier))
    leaked = sorted((_words(q) & vocab) - allowed - COMMON)
    if leaked:
        problems.append(f"uses terms the student never said: {', '.join(leaked)}")
    
    qw = _words(q)
    for prev in earlier:
        pw = _words(prev)
        if qw and pw and len(qw & pw) / len(qw | pw) > 0.6:
            problems.append("repeats an earlier question")
            break

    seen = set(re.findall(r"[a-z]+", student_text.lower()))
    glued = [
        w for w in re.findall(r"[a-z]{8,}", q.lower())
        if w not in seen and word_frequency(w, "en") == 0
    ]
    if glued:
        problems.append(f"contains words stuck together: {', '.join(glued)}")
        
    return problems


def ask_beginner(brief, title, student_turns, beginner_turns, focus, attempts=3):
    """Returns (question, problems). problems is [] when the question passed the leak check."""
    dialogue = []
    for i, s in enumerate(student_turns):
        dialogue.append(f"Student: {s}")
        if i < len(beginner_turns):
            dialogue.append(f"Beginner: {beginner_turns[i]}")

    base = (
        PROMPT_FILE.read_text(encoding="utf-8")
        .replace("<<TOPIC>>", title)
        .replace("<<DIALOGUE>>", "\n".join(dialogue))
        .replace("<<FOCUS>>", focus)
    )
    student_text = "\n".join(student_turns)
    last, question, problems = None, "", []
    for _ in range(attempts):
        content = base
        if last:
            content += f"\n\nYour previous question was rejected: {last}\nWrite a new one."
        question = generate(content, "LLM_MODEL_CHEAP", json_mode=False, temperature=0.7).strip().strip('"')
        problems = leak_problems(question, brief, student_text, title, beginner_turns)
        if not problems:
            return question, []
        last = "; ".join(problems)
    return question, problems