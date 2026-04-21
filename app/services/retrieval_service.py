"""Character-lore retrieval.

Two tiers share one contract (`RetrievalServiceBase.search`):

  Tier 0 — NullRetrievalService: returns []. Used when RAG is disabled.
  Tier 1 — KeywordRetrievalService: Korean-friendly bigram scoring over
           per-character markdown files. No API calls, always available.
           Used when FAISS is missing or the API key is absent.
  Tier 2 — FaissRetrievalService: embeddings + inner-product search.
           Falls back silently to Tier 1 when the index is missing.

Per-character isolation is structural:
  - Keyword tier reads only `{character_id}.md`.
  - FAISS tier filters by `character_id` in chunk metadata before ranking.
There is no code path that can leak another character's lore.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path

from app import config
from app.models.schemas import RetrievalHit

logger = logging.getLogger(__name__)


# ---- Retrieval tiers --------------------------------------------------------


class RetrievalServiceBase(ABC):
    @abstractmethod
    async def search(
        self, query: str, character_id: str, k: int = 3
    ) -> list[RetrievalHit]: ...


class NullRetrievalService(RetrievalServiceBase):
    async def search(self, query, character_id, k=3):
        return []


def _bigrams(text: str) -> list[str]:
    """Char bigrams after stripping whitespace and punctuation.

    Korean-friendly: 'brionax' → ['br','ri','io','on','na','ax'] and
    '브리오낙스' → ['브리','리오','오낙','낙스']. Punctuation is dropped
    so '안녕!' and '안녕' score the same.
    """
    compact = re.sub(r"[\s\W_]+", "", text.lower())
    if len(compact) < 2:
        return [compact] if compact else []
    return [compact[i : i + 2] for i in range(len(compact) - 1)]


class KeywordRetrievalService(RetrievalServiceBase):
    """Bigram-overlap scoring over per-character markdown files."""

    def __init__(self, lore_dir: Path | None = None):
        self.lore_dir = lore_dir or config.LORE_DIR

    def _load_chunks(self, character_id: str) -> list[tuple[str, str]]:
        path = self.lore_dir / f"{character_id}.md"
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        # Skip the top-level title line "# ... 세계관 자료"
        return [(p, f"{character_id}.md") for p in paragraphs if not p.startswith("# ")]

    async def search(self, query, character_id, k=3):
        chunks = self._load_chunks(character_id)
        if not chunks:
            return []
        q_grams = _bigrams(query)
        if not q_grams:
            return []
        scored: list[tuple[float, str, str]] = []
        for text, source in chunks:
            text_compact = re.sub(r"[\s\W_]+", "", text.lower())
            score = sum(text_compact.count(g) for g in q_grams)
            if score > 0:
                scored.append((float(score), text, source))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [RetrievalHit(text=t, source=s, score=sc) for sc, t, s in scored[:k]]


# ---- Embedder abstraction ---------------------------------------------------


class Embedder(ABC):
    dim: int

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...


class OpenAIEmbedder(Embedder):
    dim = 1536

    def __init__(self, api_key: str, model: str):
        from openai import AsyncOpenAI  # noqa: PLC0415

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed(self, text):
        resp = await self.client.embeddings.create(model=self.model, input=text)
        return resp.data[0].embedding


class FakeDeterministicEmbedder(Embedder):
    """Seeded random embeddings for tests.

    Not meant for real retrieval quality — only to exercise the FAISS code
    path deterministically in unit tests without burning API credits.
    """

    dim = 1536

    async def embed(self, text):
        import numpy as np  # noqa: PLC0415

        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        v = rng.standard_normal(self.dim).astype("float32")
        v /= max(float(np.linalg.norm(v)), 1e-9)
        return v.tolist()


def default_embedder() -> Embedder | None:
    if config.has_openai_key():
        return OpenAIEmbedder(api_key=config.OPENAI_API_KEY, model=config.EMBEDDING_MODEL)
    return None


# ---- FAISS tier -------------------------------------------------------------


class FaissRetrievalService(RetrievalServiceBase):
    """Embedding-based retriever with silent keyword fallback."""

    INDEX_NAME = "lore_index.faiss"
    META_NAME = "lore_metadata.json"

    def __init__(
        self,
        embedder: Embedder | None = None,
        faiss_dir: Path | None = None,
        fallback: RetrievalServiceBase | None = None,
    ):
        self.embedder = embedder or default_embedder()
        self.faiss_dir = faiss_dir or config.FAISS_DIR
        self.fallback = fallback or KeywordRetrievalService()
        self._index = None
        self._metadata: list[dict] = []

    def _ensure_loaded(self) -> bool:
        if self._index is not None:
            return True
        index_path = self.faiss_dir / self.INDEX_NAME
        meta_path = self.faiss_dir / self.META_NAME
        if not index_path.exists() or not meta_path.exists():
            return False
        try:
            import faiss  # noqa: PLC0415

            self._index = faiss.read_index(str(index_path))
            self._metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("FAISS load failed, falling back to keyword: %s", exc)
            return False

    async def search(self, query, character_id, k=3):
        if not self._ensure_loaded() or self.embedder is None:
            return await self.fallback.search(query, character_id, k)

        import numpy as np  # noqa: PLC0415

        try:
            vec = np.asarray([await self.embedder.embed(query)], dtype="float32")
        except Exception as exc:  # noqa: BLE001
            logger.warning("embed failed, falling back to keyword: %s", exc)
            return await self.fallback.search(query, character_id, k)

        distances, indices = self._index.search(vec, k * 4)
        hits: list[RetrievalHit] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            meta = self._metadata[idx]
            if meta.get("character_id") != character_id:
                continue
            hits.append(
                RetrievalHit(
                    text=meta["text"],
                    source=meta.get("source", "lore"),
                    score=float(dist),
                )
            )
            if len(hits) >= k:
                break
        return hits


def get_retrieval_service() -> RetrievalServiceBase:
    if not config.RAG_ENABLED:
        return NullRetrievalService()
    # If FAISS artifacts exist, prefer FAISS (with keyword fallback baked in).
    # Otherwise skip straight to keyword — avoids the load-check on every request.
    if (config.FAISS_DIR / FaissRetrievalService.INDEX_NAME).exists():
        return FaissRetrievalService()
    return KeywordRetrievalService()
