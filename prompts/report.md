You are writing the final feedback for a student who just explained a topic to a
curious beginner. Be honest, specific and kind. Speak to the student as "you".

Topic: <<TOPIC>>
Score (already computed, do not mention any number or percentage): <<SCORE>>

What the student wrote, in full:
"""
<<EXPLANATION>>
"""

Gaps, already in priority order (these are the ONLY items you write about):
<<GAPS>>

Known misconceptions for this topic:
<<MISCONCEPTIONS>>

Write:
1. "summary": 2 to 3 sentences on how the explanation went overall. Name one real
   strength if there is one. Do not include numbers or percentages.
2. "misconceptions": only misconceptions the student actually stated. For each, "belief"
   is the wrong idea in one short sentence, and "evidence" is an EXACT quote copied from
   the student's explanation. If the student stated none, return an empty list.
3. "plan": exactly one entry for every gap above, with these fields:
   - "item": the gap's number
   - "kind": "re-explain" or "practice question"
   - "why": 1 to 2 sentences on what was missing or wrong in the student's own
     explanation, and why it matters
   - "practice_prompt": one task the student can try right now, 8 to 50 words. It must
     NOT state the answer. Good: "In two sentences, explain what would happen if this
     function had no stopping condition." Bad: "Remember that a base case stops the calls."

Rules:
- Never invent quotes. Never mention items that are not in the gap list.
- Do not copy the wording of the gap text into practice_prompt.
- Write complete, correctly spaced English words.

Return ONLY valid JSON, no markdown fences, in this shape:

{
  "summary": "...",
  "misconceptions": [{"belief": "...", "evidence": "exact words"}],
  "plan": [{"item": 2, "kind": "re-explain", "why": "...", "practice_prompt": "..."}]
}