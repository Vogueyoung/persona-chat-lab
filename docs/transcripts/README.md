# Captured transcripts

These files are the "screenshots" of this repo. They are produced by
running the scripts in `scripts/` with no API key. Everything here is
reproducible in under 5 seconds.

| File | Produced by | What it shows |
|------|-------------|---------------|
| `prompt-scores.md` | `uv run python -m scripts.eval_prompts --write ...` | Structural linter: 12-criterion scores per (character × version). **Main result: v1 66.7% → v2 100%.** |
| `rag-demo.txt` | `uv run python -m scripts.rag_demo > ...` | RAG on/off comparison on 6 lore queries + 3 cross-character isolation probes. Verdict: no leakage. |
| `rendered-prompt-v1.txt` | inline Python snippet in `docs/design-decisions.md` | The actual system prompt Aria sees under v1, with one RAG hit injected. |
| `rendered-prompt-v2.txt` | same, with `version="v2"` | Same, under v2. Compare the two files side-by-side to see the structural rework. |
| `api-calls.txt` | `TestClient` in-memory calls | Health + list + two `POST /api/chat` samples (greeting, break-character). Dummy mode. |
| `llm-judge.md` (not yet populated) | `uv run python -m scripts.run_eval --write ...` | LLM-judge scores. Requires `OPENAI_API_KEY`. |

## How to regenerate

```powershell
uv run python -m scripts.eval_prompts --write docs/transcripts/prompt-scores.md
uv run python -m scripts.rag_demo > docs/transcripts/rag-demo.txt
uv run python -m scripts.run_eval --versions v1,v2 --write docs/transcripts/llm-judge.md
```
