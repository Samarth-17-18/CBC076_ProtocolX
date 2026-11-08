# Demo answer key (do not show the model or the audience before the demo)

Prompt: "Explain the main causes of the First World War."

| Submission | What it really is |
|---|---|
| student_A | Original answer. |
| student_B | Copied from A: 4 sentences with synonym swaps, 2 sentences word for word. |
| student_C | Paraphrase of A: same ideas in the same order, almost no shared wording. |
| student_D | Independent honest answer: same historical facts (alliances, Sarajevo, 1914) but its own wording and structure. Should NOT be flagged strongly. |
| student_E | Partial copy: sentences 1, 4 and 5 lifted verbatim from A, the rest original. |
| student_F | Original answer with a different angle (economics, Ottoman decline, mobilisation). Should not match anyone. |

Template wording: the opening and closing sentences ("In this essay I will explain..." / "In conclusion, ...")
appear in A, B, C, E and F. They should be shown as Common/Template, not as copying.

## Expected flags (sentence level)

| Pair | Expected | Why |
|---|---|---|
| A <-> B sentences 3, 5 | verbatim, High | identical sentences |
| A <-> B sentences 1, 2, 4, 6 | near_verbatim, High | synonym swaps, same structure |
| A <-> C sentences 1-6 | paraphrase, Medium/High | same meaning, little shared wording |
| A <-> E sentences 1, 4, 5 | verbatim, High | lifted word for word |
| B <-> E (A's sentences 1, 4, 5 vs B's edited versions) | near_verbatim / verbatim | both derive from A |
| C <-> B, C <-> E | paraphrase of the same source | shared origin A |
| A <-> D | None or Low | independent answer, shared facts only (false-positive test) |
| F <-> anything | None | different content |
| Intro and conclusion sentences | Common / Template | identical in 5 of 6 submissions |
