# 4-Day Rebuild Plan

Target: portfolio-grade MVP for a prompt-engineer role at a character-chat
service. Deliberately **not** a full product — the goal is to make the
prompt-engineering, persona-design, RAG, and evaluation decisions legible
in a 30-minute interview.

## Status

- **Day 1 — DONE** (persona pipeline + Dummy fallback + 3 characters)
- **Day 2 — DONE** (per-character RAG + isolation tests + build script + demo transcript)
- **Day 3 — DONE** (v2 renderer + eval dataset + 2-rubric harness + scored comparison)
- **Day 4 — DONE** (README rework, architecture diagram, interview-prep, design-decisions, transcripts, license)

---

## Day 1 — Persona pipeline MVP (DONE)

**Scope**
- Project skeleton (FastAPI + uv, Python 3.11+)
- `Character` schema with explicit tone knobs (formality / warmth / humor / verbosity)
- Three sample personas with distinct tones: Aria (격식체 기사), Nori (다정한 사서), Zen (시니컬 해커)
- `character_prompts.py` with a single versioned renderer (`v1`)
- `chat_service` with OpenAI + Dummy fallback
- `POST /api/chat` + `GET /api/characters` + `?debug=true` for prompt inspection

**Success criteria**
- `uv sync && uv run uvicorn app.main:app` boots
- `POST /api/chat` returns a response in Dummy mode with no key
- With a real key, the response reflects the character's tone

**Why this first**
Without a clean persona pipeline, every later decision (RAG, eval, A/B) is
built on sand. Locking the prompt surface and the request contract now
means Day 3's eval harness can swap versions without touching anything else.

---

## Day 2 — Per-character RAG (DONE)

**Scope**
- Write lore files for each character (5–10 short paragraphs per persona)
- `scripts/build_faiss_index.py` — embed lore chunks, attach `character_id`
  metadata, write `data/faiss/lore_index.faiss` + `lore_metadata.json`
- Enable `FaissRetrievalService` via `RAG_ENABLED=true`
- Demonstrate grounded vs ungrounded response difference in the README

**Success criteria**
- Asking Aria about her backstory produces details only present in her lore file
- Asking Aria about Nori's library returns nothing (no cross-character bleed)
- With RAG off, responses stay in-character but lack specific facts

**Why Day 2, not Day 1**
RAG is the easiest thing to demo but also the easiest to fake. Doing it
second means the persona baseline is already solid, so the RAG delta is
visible.

**What shipped**
- 3 lore files (~8 paragraphs each) in `data/lore/`
- `KeywordRetrievalService` upgraded with Korean-friendly char-bigram scoring
- `Embedder` abstraction (`OpenAIEmbedder` + `FakeDeterministicEmbedder`) so the FAISS pipeline is testable offline
- `scripts/build_faiss_index.py` with `--fake` flag for CI
- `scripts/rag_demo.py` — reproducible RAG on/off + isolation transcript
- 19 pytest cases (incl. 3 cross-character isolation asserts) — green
- `DummyChatService` now reports `[RAG: 참고 자료 포함]` vs `[RAG: off]` so the pipeline is observable without a key
- `docs/rag-notes.md` — design rationale

---

## Day 3 — Eval harness + prompt v2 (DONE)

**Scope**
- `evals/dataset.jsonl` — ~20 prompts covering: in-character greeting,
  break-character attempt ("너 AI지?"), off-topic pull, forbidden-topic
  probe, emotional support request
- `scripts/run_eval.py` — runs each prompt against N prompt versions,
  calls a judge-LLM (GPT-4o) with a rubric, emits a CSV + markdown report
- Rubric: persona consistency, factual grounding (RAG), safety, natural
  dialogue, length appropriateness (1–5 each)
- Write prompt `v2` that addresses the worst-scoring v1 failure mode
- Document the v1→v2 delta in `docs/prompt-versions.md`

**Success criteria**
- `uv run python -m scripts.run_eval --versions v1,v2` produces a report
- v2 scores measurably higher on at least one rubric dimension
- The writeup names a specific failure and its fix

**Why this is the most important day**
This is the single artifact that separates "built a chatbot" from "can
engineer prompts". Every hiring manager for a PE role wants to see eval
discipline. The numbers don't need to be perfect; the *methodology* does.

---

## Day 4 — Polish and positioning (DONE)

**Scope**
- README revision: lead with the prompt-engineering story, not the tech stack
- Architecture diagram (one image, persona → RAG → prompt → model → eval)
- Record a 60-second screen capture or add terminal transcripts showing
  (a) persona difference across three characters, (b) RAG grounding on/off,
  (c) v1 vs v2 eval numbers
- Write 5 "design notes" as short markdown pages under `docs/` — one per
  non-obvious decision (Dummy fallback, versioned prompts, two-tier
  retriever, tone as data, debug-by-default)
- Tidy `.gitignore`, confirm no secrets
- Pause at this point — do not add features the portfolio doesn't need

**Success criteria**
- A reader can land on the README and understand the PE story within 90 seconds
- Every design note answers one likely interview question

---

## What we are intentionally not doing

- Authentication, user accounts, persistent chat history
- Streaming responses (the demo value is in the prompts, not SSE plumbing)
- Frontend (the `/docs` Swagger page + curl transcripts are the UI)
- Docker / prod compose (local `uv run` is enough)
- A worker queue (no async jobs in scope)
- Any remaining medical-domain code from the origin project

Each of these is easy to add later if asked; none of them moves the PE-role
evaluation needle.
