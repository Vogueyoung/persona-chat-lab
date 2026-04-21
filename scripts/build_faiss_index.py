"""Build the lore FAISS index from per-character markdown files.

For each character_id found under LORE_DIR, split the file by blank-line
paragraphs (skipping the top-level title), embed each paragraph, and
write a single FAISS inner-product index plus a parallel metadata list.

Usage (real embeddings — needs OPENAI_API_KEY):
    uv run python -m scripts.build_faiss_index

Usage (fake deterministic embeddings — CI / no-key):
    uv run python -m scripts.build_faiss_index --fake

The --fake flag lets the FAISS pipeline be exercised end-to-end offline
so tests can verify isolation and ranking contracts without credits.
Fake-built indices have no semantic quality; keyword retrieval is a
better fallback for real use.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from app import config
from app.services.retrieval_service import (
    Embedder,
    FakeDeterministicEmbedder,
    OpenAIEmbedder,
)


def iter_lore_chunks(lore_dir: Path):
    for path in sorted(lore_dir.glob("*.md")):
        character_id = path.stem
        text = path.read_text(encoding="utf-8")
        for paragraph in (p.strip() for p in text.split("\n\n") if p.strip()):
            if paragraph.startswith("# "):
                continue
            yield character_id, paragraph, path.name


def pick_embedder(fake: bool) -> Embedder:
    if fake:
        print("[build] Using FakeDeterministicEmbedder (no API calls).")
        return FakeDeterministicEmbedder()
    if not config.has_openai_key():
        print(
            "[build] OPENAI_API_KEY is not set. Rerun with --fake for a dummy "
            "index, or export the key for real embeddings.",
            file=sys.stderr,
        )
        sys.exit(2)
    print(f"[build] Using OpenAIEmbedder (model={config.EMBEDDING_MODEL}).")
    return OpenAIEmbedder(api_key=config.OPENAI_API_KEY, model=config.EMBEDDING_MODEL)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fake",
        action="store_true",
        help="Use deterministic fake embeddings. For CI and offline smoke tests.",
    )
    args = parser.parse_args()

    import faiss  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    config.FAISS_DIR.mkdir(parents=True, exist_ok=True)
    embedder = pick_embedder(args.fake)

    chunks = list(iter_lore_chunks(config.LORE_DIR))
    if not chunks:
        print(f"[build] No lore files found under {config.LORE_DIR}.", file=sys.stderr)
        sys.exit(1)
    print(f"[build] {len(chunks)} chunks across {len({c[0] for c in chunks})} characters.")

    vectors: list[list[float]] = []
    metadata: list[dict] = []
    for character_id, text, source in chunks:
        vec = await embedder.embed(text)
        vectors.append(vec)
        # First line of the paragraph (without the leading '##') as a title hint.
        title = re.sub(r"^#+\s*", "", text.split("\n", 1)[0]).strip()
        metadata.append(
            {
                "character_id": character_id,
                "text": text,
                "source": source,
                "title": title,
            }
        )

    arr = np.asarray(vectors, dtype="float32")
    # L2-normalize for inner-product == cosine similarity on unit vectors.
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    arr = arr / np.clip(norms, 1e-9, None)

    index = faiss.IndexFlatIP(embedder.dim)
    index.add(arr)

    index_path = config.FAISS_DIR / "lore_index.faiss"
    meta_path = config.FAISS_DIR / "lore_metadata.json"
    faiss.write_index(index, str(index_path))
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[build] Wrote {index_path} and {meta_path}.")


if __name__ == "__main__":
    asyncio.run(main())
