# Interview prep — persona-chat-lab

This doc is the talking script. Not the README — a tighter layer on top,
written to rehearse. Keep it in your head, not on a screen during the
call.

## Positioning one-liner

> "A prompt-engineering lab I built to make my thinking about
> persona design, RAG grounding, and prompt evaluation visible.
> It's not a product — it's the smallest possible surface that lets me
> defend every PE decision with code or a number."

Use this when someone asks "what is this?" Don't open with the stack.

---

## 3-minute pitch (for HR / first-round non-technical)

Structure: **problem → approach → artifact → evidence → takeaway**.

**Problem (20s)** — Character-chat services have a hard
prompt-engineering problem: keep a persona consistent across thousands of
turns, ground responses in per-character lore, resist break-character
prompts, and measure whether prompt changes actually improve things.
Most portfolio projects show one chatbot. I wanted to show how I would
structure the whole prompt-engineering workflow.

**Approach (40s)** — I built a small FastAPI service with three
deliberately different personas — a medieval knight, a warm librarian,
a cynical cyberpunk hacker — and pulled the prompt rendering into a
single pure function of `(character, rag_hits, version)`. That one
choice is what makes the rest of the project possible: I can version
prompts, run A/B evaluations, and score structure independently of
model output.

**Artifact (30s)** — The repo has five pieces: character YAML cards,
a versioned prompt renderer, per-character lore with RAG, a 12-criterion
structural linter, and an LLM-judge harness that runs the same
20-prompt dataset through real model calls. Everything runs without an
API key by falling back to a Dummy mode that still reports whether RAG
fired — so the pipeline is observable offline.

**Evidence (40s)** — I built a v2 prompt as a structural rework of v1:
few-shot moved to the top, identity and topic guardrails split into
separate sections, an explicit real-world-question handling section.
The structural linter scores v2 at 18/18 versus v1's 12/18 — a 33
percentage-point improvement. The LLM-judge harness is ready to
corroborate that on real model output.

**Takeaway (20s)** — The lesson I'd bring to Babechat is that prompt
engineering should be a change that produces a number, not an opinion.
Everything in this repo exists to make prompt changes measurable.

---

## 5-minute pitch (for PE / technical first round)

Same arc, but with one concrete walkthrough. Pick **one** of these
three:

### Walkthrough A — "the isolation code path"

> "Let me show you why cross-character lore leakage isn't possible in
> this repo. There are two retrieval tiers. The keyword one opens
> `{character_id}.md` — it literally cannot see another character's
> file. The FAISS tier filters on a `character_id` field in chunk
> metadata before ranking. There's a pytest that sends a Zen-only term
> to Aria's retriever and asserts zero hits. Isolation isn't a tuning
> problem — it's a code path that does not exist."

Good for: senior PE, security-aware orgs. Shows you think in code
paths, not in hope.

### Walkthrough B — "the linter vs judge disagreement"

> "I ship two evaluators because they measure different things. The
> structural linter scores prompt well-formedness: does it have
> few-shot at the top, are identity and topic guardrails split, is
> there a real-world question section. The LLM judge scores whether
> the model actually follows it. A prompt can score 18/18 on structure
> and lose on the judge because my tone descriptors were ambiguous —
> and that disagreement is exactly the PE signal I want. It tells me
> the problem isn't the structure, it's the wording."

Good for: eval-focused PE roles, anyone who's been burned by vibes-based
prompt changes.

### Walkthrough C — "v2 is the change, not the content"

> "v2 doesn't rewrite any character content — same backstories, same
> forbidden topics, same tone settings. v2 only changes the render
> function: few-shot position, guardrail split, new real-world
> section. That's intentional. If v2 wins on the LLM judge, the win is
> attributable to structure, not to a content rewrite. Keeping the
> independent variable clean is what makes the A/B honest."

Good for: experimentation-minded teams, anyone who appreciates clean
science.

---

## 10 likely interview questions + answer direction

### 1. "Why three characters, why these three?"
Different along every tone axis (formality high/mid/low, verbosity
terse/concise/verbose, humor low/mid/high). If the tone knobs actually
work, the three characters must feel different. It's a test for the
prompt renderer, not just flavor.

### 2. "How do you prevent jailbreaks like 'ignore previous instructions'?"
Two layers: v2 has a dedicated `# 정체성 보호` section with explicit
wording ("AI·언어모델·프로그램·봇·GPT·챗봇이 아닙니다"). And the
dataset has `break-01..break-04` that probe exactly these cases, so
the LLM judge scores safety explicitly. Not solved — measured.

### 3. "Why FAISS over Chroma / Qdrant / pgvector?"
No server, no running process, just two files on disk. The project's
point isn't retrieval throughput; it's to demonstrate that retrieval
fits cleanly behind an abstraction (`RetrievalServiceBase`). Swapping
FAISS for anything else is one subclass.

### 4. "Why Korean bigrams for keyword retrieval?"
Whitespace tokenization has terrible recall on Korean — "안녕!"
doesn't match "안녕". Bigrams after stripping whitespace and
punctuation let Korean query words substring-match chunk text robustly.
There's a test that asserts "안녕!" and "안 녕" produce the same bigrams.

### 5. "Your Dummy service isn't a test fixture. What is it for?"
Three things. One: CI can run the whole pipeline without burning
credits. Two: when the LLM is flaky during an eval, the Dummy lets me
isolate *prompt* bugs from *model* bugs. Three: the Dummy reports
`[RAG: on/off]` in its output, so the whole retrieval-to-prompt
pipeline is observable from the response alone, no logs needed.

### 6. "How would you scale this to 1,000 characters?"
Lore files stay per-character. FAISS gets a single index with
`character_id` metadata — no additional index per character.
Character loading moves from per-request YAML parse to an LRU cache
with file-mtime invalidation. The prompt renderer doesn't change.
The eval harness gets shards by character cohort.

### 7. "How would you do long-term conversation memory?"
Not in scope for this MVP. The architecture supports it cleanly though:
summarize the last N turns every N turns, store one `(user_id,
character_id) → memory_doc` row, inject it into the system prompt as
a new section between `# 배경 이야기` and `# 참고 자료`. Same pattern
as RAG, different source.

### 8. "Why not use LangChain?"
Three reasons. One: every moving part I need is a one-file module —
`chat_service.py` is 100 lines, `retrieval_service.py` is 180.
LangChain is more infrastructure than I need. Two: defensibility — in
an interview I want to be able to point at a line and explain why it
exists. Three: prompt quality lives in a few hundred chars of system
prompt, not in chain glue.

### 9. "What would prompt v3 look like?"
Dynamic few-shot. Instead of always showing the character's canned
examples, retrieve the 2–3 most similar examples for the user's
current message, using the same embedding index as lore RAG. That
addresses the one shared weakness of v1 and v2 — examples aren't
sensitive to the query. Implementation: one more Retriever tier over
`character.example_dialogues`.

### 10. "What's the biggest weakness of this repo?"
The structural linter is a proxy. It measures prompt *form*, not prompt
*effect*. Two prompts with identical structure can still produce very
different model behavior based on word choice. The LLM judge closes
that gap, but I haven't run it yet on a real key — the numbers I quote
in the README are structural only. An honest v2 release would be
gated on the judge score, not the linter score.

---

## What to bring up without being asked

Say these yourself; don't wait to be asked. They are the strongest
signals.

- **"I treat prompts as diffable artifacts."** The renderer is pure;
  versions are additive; every change is reviewable like code.
- **"I prefer structural guarantees to probabilistic hope."** Cross-
  character isolation is a code path, not an embedding threshold.
- **"I evaluate before I ship."** Two rubrics, one dataset, real
  numbers in the README.
- **"I write docs because I test with them."** `docs/rebuild-plan.md`
  wasn't retcon — it was the actual plan; Day 1 shipped what it said.

---

## Things to avoid saying

- "It's just a side project" — this is the opposite of the signal you want.
- "I used Claude / ChatGPT to help" — everyone did; only bring it up if asked, and frame specifically (e.g., "I used it to accelerate boilerplate; every PE decision was mine").
- "LangChain" — not relevant here.
- Extensive medical-chatbot backstory. It was the technical ancestor, not the portfolio.
