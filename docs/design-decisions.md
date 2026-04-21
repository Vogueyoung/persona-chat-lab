# Design decisions

One page per non-obvious choice. Each section answers "what, why, and
what I'd do differently at scale".

---

## 1. Persona as YAML, not as a long Python string

**What.** Each character is a declarative YAML file (`id`, `name`,
`tone.*`, `personality`, `speaking_style`, `backstory`,
`forbidden_topics`, `example_dialogues`, `greeting`). The system prompt
is rendered from that structure.

**Why.** If persona data is embedded in a Python string, every tweak is
a commit + deploy, and there's no schema to enforce across characters.
By forcing every persona to declare the same slots, A/B tests stay
apples-to-apples: v1 and v2 see the same inputs, the only difference is
how the renderer orders and frames them.

**At scale.** Move to a CMS or DB-backed persona editor, same schema.
Keep the renderer as the read path.

---

## 2. Prompt as a pure function `render(character, rag_hits, version)`

**What.** `app/prompts/character_prompts.py` holds every version. A
registry maps `"v1" / "v2"` to renderer callables. `render_system_prompt`
is the only public entry point.

**Why.** Pure functions are diffable, versionable, and testable without
fixtures. The linter scores output; the unit tests snapshot structure.
Versioning at this layer — instead of, say, env-toggled flags — keeps
the HTTP API simple: the client picks `prompt_version`.

**At scale.** The registry becomes a shared-service config: add `v3`,
run a percentage-of-traffic experiment, collect judge scores, promote.

---

## 3. Two retrieval tiers behind one interface

**What.** `RetrievalServiceBase` has three implementations:
`NullRetrievalService` (returns `[]`), `KeywordRetrievalService`
(Korean-bigram substring scoring over `{character_id}.md`), and
`FaissRetrievalService` (embeddings + IP search, falls back silently
to keyword).

**Why.** Character-lore RAG has to work before the user has wired up
an API key. The keyword tier gives useful results on small lore files
(~8 paragraphs per character) and serves as a working demo. FAISS is
the semantic layer for production. Both satisfy the same contract so
the chat pipeline doesn't branch.

**At scale.** Replace the internal keyword implementation with a
lexical tier like BM25; swap FAISS for a hosted vector store. The
interface doesn't move.

---

## 4. Cross-character isolation is structural

**What.** The keyword retriever only reads
`{character_id}.md`. The FAISS retriever filters by `character_id` in
metadata before ranking. Three pytest cases assert cross-character
probes return 0 hits.

**Why.** Making isolation a code-path property rather than an embedding
score threshold means it cannot be tuned away by accident. A poorly
tuned similarity threshold would "probably" keep characters separate.
A metadata filter *does* keep them separate.

**At scale.** Same pattern, just with user-scoped or tenant-scoped
filters stacked on top. FAISS's `IndexIVFFlat` with filtered search
scales this comfortably.

---

## 5. Dummy service as a pipeline observability tool

**What.** When `OPENAI_API_KEY` is unset, the factory returns a
`DummyChatService`. Its responses include `[RAG: 참고 자료 포함]` or
`[RAG: off]` depending on whether the rendered system prompt has the
RAG block.

**Why.** I wanted the pipeline to be debuggable without running a
model. The Dummy reports whether retrieval fired and whether the
renderer accepted RAG hits, which is enough to tell if a bug is in the
retrieval layer, the renderer, or somewhere downstream. That separation
is invaluable during eval runs where model variance otherwise drowns
the signal.

**At scale.** Keep it. Add a `StubOpenAIChatService` that returns
canned per-character replies from fixtures — useful for UI development
and contract tests.

---

## 6. Embedder abstraction with a fake implementation

**What.** `Embedder` is a tiny interface (`dim`, `embed(text)`).
`OpenAIEmbedder` wraps the real API; `FakeDeterministicEmbedder` hashes
the input to seed NumPy's RNG and returns a normalized random vector.

**Why.** The FAISS code path (build index → load index → query →
filter → rank) is brittle. I wanted to exercise it end-to-end in CI
without spending on embedding calls. A deterministic fake embedder
gives the FAISS pipeline something to chew on; the retrieval results
are random but reproducible, and character-id filtering still works
so the isolation tests stay valid.

**At scale.** Add a `HuggingFaceEmbedder` behind the same interface.
Pin dimension at 1536 to keep FAISS indexes interchangeable.

---

## 7. Two eval rubrics, one dataset

**What.** `evals/dataset.jsonl` has 20 prompts across 5 categories
(greet / self-intro / break-character / emotional-support /
lore-grounded / forbidden-topic / real-world-probe). Two evaluators
score it: a **structural linter** (12 criteria, no key) and an
**LLM judge** (5 dimensions, key required).

**Why.** A single rubric lies in one of two directions. Either the
rubric is fast but shallow (linter), or deep but expensive (LLM). Using
both gives me a fast feedback loop for iteration (linter, seconds, no
cost) and a credible release gate (judge, minutes, ~$0.50).

**At scale.** Linter runs in PR CI on every prompt change. Judge runs
on a schedule and on release candidates. Add human-evaluated spot
checks for top-5 % of high-stakes prompts.

---

## 8. v2 is structure-only, not content

**What.** v1 → v2 is a renderer change. No character cards were
modified. No backstories rewritten. No forbidden topics adjusted.

**Why.** To keep the A/B honest. If v2 beats v1 on the LLM judge too,
the win is attributable to the three structural changes (few-shot
primacy, guardrail split, real-world handling) and not to a content
rewrite that coincidentally improved tone. Clean independent variables
make the result interpretable.

**At scale.** Same discipline. A change is either content, structure,
or model. Never mix.

---

## 9. Debug by default — `?debug=true` returns the rendered prompt

**What.** `POST /api/chat?debug=true` includes
`rendered_system_prompt` in the response.

**Why.** Reviewers (and my interviewer) can see exactly what the model
sees without digging through code. This is surprisingly rare in
production chatbots; it makes prompt engineering legible at the
network boundary.

**At scale.** Gate behind an auth claim or a dev-only header. Keep the
capability.

---

## 10. What I deliberately did not do

- **Authentication, user accounts, chat history persistence.** Out of
  scope. The API is stateless; each call carries its own history.
- **Streaming responses (SSE).** The interesting demo is the prompt,
  not the plumbing. Added it in the medical-chat ancestor; not here.
- **Frontend.** The `/docs` Swagger UI + `curl` is the UI. Any React
  shell added now would be time spent not on prompt/eval quality.
- **Docker / prod compose / CI / auth middleware.** Portfolio target
  is a PE role, not a platform role. All of the above are easy to add
  later; none of them move the PE-evaluation needle this week.
- **Long-term memory.** Genuinely interesting; explicitly scoped to
  "v3 / next iteration". Said so in `docs/prompt-versions.md`.

Each of those is a defensible choice in an interview. "Why didn't you
build X?" has a specific answer: **it would not have moved the signal I
wanted this repo to send.**
