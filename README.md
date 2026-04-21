# persona-chat-lab

A prompt-engineering lab for persona-based character chat.
Portfolio project targeting **prompt-engineer roles at character-chat
services** (Babechat-style).

> This repo isn't trying to ship a product. It makes
> prompt-engineering decisions — structure, guardrails, tone knobs, RAG
> grounding, prompt versioning, evaluation — **legible and defensible in a
> 30-minute interview**.

**Highlight:** a 12-criterion prompt-structure rubric scores
`v1` → `v2` at **+33.3 percentage points** (12.0/18 → 18.0/18 per prompt,
mean across 3 characters). Full breakdown in
[`docs/prompt-versions.md`](docs/prompt-versions.md).

---

## Architecture

```mermaid
flowchart LR
    subgraph Client
        U[User message]
    end

    subgraph "persona-chat-lab"
        U --> API[/api/chat]
        API --> ORCH[generate_reply]

        subgraph "Prompt surface"
            YAML[characters/*.yaml<br/>personality + tone + few-shot]
            RENDER[character_prompts.py<br/>v1 / v2 renderers]
        end

        subgraph "Retrieval"
            LORE[data/lore/*.md]
            KEY[KeywordRetriever<br/>korean bigrams]
            FAISS[FaissRetriever<br/>embeddings]
            FB[fallback chain]
        end

        ORCH --> RETR{RAG_ENABLED?}
        RETR -- no --> NULL[NullRetriever]
        RETR -- yes --> FAISS
        FAISS -. index missing .-> KEY
        KEY --> LORE

        YAML --> RENDER
        NULL --> RENDER
        KEY --> RENDER
        FAISS --> RENDER
        RENDER --> MODEL{API key?}

        MODEL -- yes --> OAI[OpenAIChatService<br/>gpt-4o-mini]
        MODEL -- no --> DUM[DummyChatService<br/>pipeline observable]

        OAI --> RESP[ChatResponse<br/>reply + rag_hits + rendered_prompt]
        DUM --> RESP
    end

    subgraph "Evaluation"
        RENDER --> LINT[eval_prompts.py<br/>12-criterion linter<br/>no key]
        OAI --> JUDGE[run_eval.py<br/>gpt-4o judge<br/>5 dimensions]
        LINT --> REPORT1[docs/transcripts/<br/>prompt-scores.md]
        JUDGE --> REPORT2[docs/transcripts/<br/>llm-judge.md]
    end
```

The diagram is the whole repo. Four boxes — prompt surface, retrieval,
model service, evaluation — each with explicit fallbacks so nothing
breaks when a key is absent, an index is missing, or a prompt version
doesn't exist.

---

## What's inside

```
persona-chat-lab/
├── app/
│   ├── main.py                       # FastAPI entry point
│   ├── config.py                     # env loading
│   ├── models/schemas.py             # Character / ChatRequest / ToneConfig
│   ├── prompts/character_prompts.py  # v1 / v2 renderers ← the PE surface
│   ├── services/
│   │   ├── character_loader.py       # YAML → Character
│   │   ├── retrieval_service.py      # Null / Keyword / FAISS + Embedder
│   │   └── chat_service.py           # OpenAI + deterministic Dummy
│   └── api/
│       ├── chat.py                   # POST /api/chat
│       └── characters.py             # GET /api/characters
├── characters/                       # one YAML per persona
│   ├── aria_knight.yaml              # 격식체 판타지 기사 (formality: high)
│   ├── nori_librarian.yaml           # 다정한 사서 (formality: mid)
│   └── zen_hacker.yaml               # 시니컬 사이버펑크 해커 (formality: low)
├── data/
│   ├── lore/*.md                     # per-character world facts
│   └── faiss/                        # generated vector index (gitignored)
├── evals/
│   ├── dataset.jsonl                 # 20 probes (greet / break / emo / lore / real_world)
│   └── rubrics.md                    # 2 rubric specs (structural + LLM-judge)
├── scripts/
│   ├── build_faiss_index.py          # embed lore → FAISS (real or fake)
│   ├── rag_demo.py                   # RAG on/off + isolation transcript
│   ├── eval_prompts.py               # structural linter (no key)
│   └── run_eval.py                   # LLM-judge harness (key required)
├── tests/                            # pytest — 24 tests green
└── docs/
    ├── rebuild-plan.md               # 4-day plan
    ├── rag-notes.md                  # RAG design rationale
    ├── prompt-versions.md            # v1 → v2 with scored delta
    ├── design-decisions.md           # why each choice was made
    ├── interview-prep.md             # 3-min / 5-min pitches + 10 Q&A
    └── transcripts/                  # captured linter + RAG demo output
```

---

## Five design choices this repo is built around

### 1. Persona is data; prompt is a pure function
Characters live in YAML. The system prompt is `render(character, rag_hits, version)`
— a pure function. Making the prompt a function of explicit inputs is what
lets the A/B linter score v1 vs v2 fairly, and what lets tests snapshot
structure without touching content.

### 2. Every external dependency has a silent fallback
- No API key → `DummyChatService` (pipeline still runs; reports `[RAG: on/off]`)
- No FAISS index → `KeywordRetrievalService` (Korean bigrams over lore files)
- No lore file → empty hits, prompt still renders cleanly
- Failed embedding call → falls back to keyword retriever
- Unknown prompt version → 400 with the available list

This is not defensive over-engineering. It is what makes the whole thing
demoable offline and testable without an account.

### 3. Cross-character isolation is structural, not probabilistic
The keyword retriever opens **only** `{character_id}.md`. The FAISS
retriever filters by `character_id` in chunk metadata **before** ranking.
A pytest asserts all three cross-character probes return 0 hits. Leakage
isn't a tuning problem — it's a code path that does not exist.

### 4. Prompts are versioned at the HTTP boundary
```json
POST /api/chat { "character_id": "aria_knight", "prompt_version": "v2", ... }
```
Eval runs pin a version. A/B ships by flipping one field. `v2` was not
a content rewrite — it was a structural rework (few-shot placement,
guardrail split, real-world handling) whose hypothesized wins map
cleanly to dimensions of the LLM-judge rubric.

### 5. Two evaluators, one dataset
- **Structural linter** (`scripts/eval_prompts.py`) — no key, no model
  calls. Scores prompt structure on 12 criteria.
- **LLM-judge** (`scripts/run_eval.py`) — full pipeline × real model ×
  `gpt-4o` judge on 5 dimensions.

They measure different things. A prompt can score 18/18 on structure and
still lose on LLM-judge because the tone descriptors were poorly chosen.
That disagreement is a PE signal — the linter tells you whether the
prompt is **well-formed**; the judge tells you whether it **works**.

---

## v1 vs v2 — scored

From the structural linter, mean across 3 characters:

| Version | Total | Per-character | % of 18 |
|---------|------:|--------------:|--------:|
| `v1` | 36 / 54 | 12.0 / 18 | 66.7% |
| `v2` | 54 / 54 | 18.0 / 18 | **100.0%** |

v2 wins all three differentiating criteria:

| Criterion | v1 | v2 |
|-----------|---:|---:|
| Few-shot primacy (examples before rules) | 0 / 6 | **6 / 6** |
| Guardrails separated (identity vs topic) | 0 / 6 | **6 / 6** |
| Real-world question handling explicit | 0 / 6 | **6 / 6** |

Full per-criterion breakdown in
[`docs/transcripts/prompt-scores.md`](docs/transcripts/prompt-scores.md).
Rationale in [`docs/prompt-versions.md`](docs/prompt-versions.md).

---

## Run it (Windows)

```powershell
# 1) install uv once
#    irm https://astral.sh/uv/install.ps1 | iex

cd D:\projects\persona-chat-lab

# 2) install deps + run tests (24 green, no key needed)
uv sync
uv run pytest -q

# 3) structural eval (no key)
uv run python -m scripts.eval_prompts --write docs/transcripts/prompt-scores.md

# 4) RAG demo (no key)
uv run python -m scripts.rag_demo

# 5) optional — real model + LLM-judge eval
copy .env.example .env
# edit .env: OPENAI_API_KEY=sk-...  RAG_ENABLED=true
uv run python -m scripts.build_faiss_index
uv run python -m scripts.run_eval --versions v1,v2 --write docs/transcripts/llm-judge.md

# 6) start the server
uv run uvicorn app.main:app --reload
# open http://localhost:8000/docs
```

API smoke test:

```powershell
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/chat?debug=true ^
  -H "Content-Type: application/json" ^
  -d "{\"character_id\":\"aria_knight\",\"prompt_version\":\"v2\",\"messages\":[{\"role\":\"user\",\"content\":\"네 가문 이야기 좀 해줘.\"}]}"
```

With no API key, responses carry a `DUMMY 모드 · [RAG: on|off]` marker.
`?debug=true` returns the fully rendered system prompt in the response
so reviewers can see exactly what the model would see.

---

## Further reading

- [`docs/rebuild-plan.md`](docs/rebuild-plan.md) — 4-day build plan (where each day's scope stopped)
- [`docs/rag-notes.md`](docs/rag-notes.md) — RAG design rationale, isolation guarantees, Embedder abstraction
- [`docs/prompt-versions.md`](docs/prompt-versions.md) — v1 → v2 with scored delta and per-criterion breakdown
- [`docs/design-decisions.md`](docs/design-decisions.md) — one page per non-obvious choice
- [`docs/interview-prep.md`](docs/interview-prep.md) — 3-min / 5-min pitch templates, 10 Q&A
