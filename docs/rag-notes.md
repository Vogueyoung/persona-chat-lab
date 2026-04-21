# RAG design notes

## Why RAG in a persona-chat service
Persona cards are tiny (~30 lines). World lore, side characters, relationships,
and specific facts do not fit there and should not — bloating the system
prompt costs tokens on every turn and dilutes the strong persona signal.
RAG lets lore grow independently of the prompt: the system prompt stays
short and stylistic, the lore file holds the long tail of facts, and only
the relevant 2–3 chunks are pulled in per turn.

## Per-character isolation is structural, not probabilistic
Every chunk in the FAISS index carries a `character_id` in its metadata.
Retrieval filters by that id **before** ranking, so Nori's queries cannot
surface Zen's cyberpunk lore even if the embeddings happen to be close.
The keyword tier is even simpler: it reads only `{character_id}.md`.
Isolation is a property of the code path, not of the retrieval score.

A pytest in `tests/test_retrieval.py` asserts this directly: querying Aria
for a term that appears only in Nori's lore returns zero hits.

## Two retrieval tiers, one contract
- **KeywordRetriever** — always available, no API calls, Korean bigrams.
  Fine for small lore files (ours are ~8 paragraphs) and perfect for CI
  and for eval runs that want to isolate prompt effects from retrieval
  quality.
- **FaissRetriever** — OpenAI embeddings + inner-product search. Better
  semantic recall ("가문 이야기 해줘" → matches "페르시우스 가문" chunk).
  Falls back silently to keyword when the index or API key is missing.

Both implement `RetrievalServiceBase.search(query, character_id, k)`.
The chat pipeline does not branch on retriever type.

## The Embedder abstraction
`Embedder` is a tiny interface (`dim`, `embed(text)`) so the FAISS service
can be unit-tested without an API key by injecting a seeded deterministic
embedder. Production uses `OpenAIEmbedder`; tests use a fake one whose
vectors are reproducible from a hash.

## Prompt integration
RAG hits are rendered as a `# 참고 자료 (당신의 세계관/지식)` block near
the end of the system prompt, with explicit instructions:
"있는 내용은 사실로 취급, 없는 내용은 지어내지 않는다". This mirrors the
guardrail pattern from medical chat — factual grounding is the same
engineering problem regardless of domain.

## What RAG does not do here
- Long-term conversation memory (planned for a later iteration, not in MVP)
- Cross-character fact sharing (explicitly prevented — see above)
- User-profile personalization (out of scope for a portfolio)
