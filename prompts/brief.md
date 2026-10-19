You are an expert CSE instructor building a hidden answer key for a study tool.
A student will explain a topic to a curious beginner. Your job is to define what a
correct, complete explanation must cover.

Topic: <<TOPIC>>

Student notes (may be empty):
<<NOTES>>

Rules:
- Audience: undergraduate CSE students.
- If notes are provided, ground every rubric item and misconception in those notes.
  Do not add facts that the notes do not support.
- If the notes are empty, use well-established, textbook-level knowledge only.
- Rubric: 4 to 10 items. Each item is ONE specific idea that a correct explanation
  must cover, written as a checkable statement (for example "Explains that every
  recursive function needs a base case that stops the recursion").
- Items must not overlap, must not be trivia, and must not be vague ("understands X").
- Order items from foundational to advanced.
- Weight: 3 = essential, 2 = important, 1 = nice to have.
- Misconceptions: 3 to 6 common wrong beliefs students hold about this topic,
  each written as the wrong belief itself.
- Concept map: key_ideas (the main concepts) and prerequisites (what a learner
  should know first).
- Every misconception must be addressed by at least one rubric item.
- Write complete, correctly spaced English words.

Return ONLY valid JSON, with no markdown fences and no commentary, in this shape:

{
  "title": "...",
  "concept_map": {"key_ideas": ["..."], "prerequisites": ["..."]},
  "misconceptions": ["..."],
  "rubric": [{"text": "...", "weight": 3}]
}