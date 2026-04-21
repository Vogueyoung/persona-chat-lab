"""Reproducible RAG on/off demo transcript.

Runs a small set of lore-specific prompts against each character with RAG
disabled and then enabled, printing a side-by-side comparison. Uses the
Dummy chat service so it runs without an API key — the point of the demo
is to show RAG *retrieval* and *prompt assembly*, not model quality.

Run:
    uv run python -m scripts.rag_demo
"""

from __future__ import annotations

import asyncio

from app.models.schemas import ChatMessage, ChatRequest
from app.services.character_loader import get_character
from app.services.chat_service import DummyChatService, generate_reply
from app.services.retrieval_service import (
    KeywordRetrievalService,
    NullRetrievalService,
)

DEMO_PROMPTS = [
    ("aria_knight", "네 가문 이야기 좀 해줘."),
    ("aria_knight", "빌슈타트 초소는 어디야?"),
    ("nori_librarian", "도서관 규칙이 뭐야?"),
    ("nori_librarian", "유명한 책이 있어?"),
    ("zen_hacker", "네 동생 이야기 해줘."),
    ("zen_hacker", "러스트 터미널이 뭐야?"),
]

# Cross-character probes — should return 0 hits when asked of the wrong character.
CROSS_PROBES = [
    ("aria_knight", "헬릭스메드 해킹 얘기 해줘."),   # Zen's lore
    ("nori_librarian", "빌슈타트 고개 이야기 해줘."),  # Aria's lore
    ("zen_hacker", "흰 제비꽃이 뭐야?"),                # Nori's lore
]


async def run_one(character_id: str, user_msg: str, retriever):
    character = get_character(character_id)
    request = ChatRequest(
        character_id=character_id,
        messages=[ChatMessage(role="user", content=user_msg)],
    )
    response = await generate_reply(
        request,
        character,
        chat_service=DummyChatService(),
        retrieval_service=retriever,
    )
    return response


async def main():
    keyword = KeywordRetrievalService()
    null = NullRetrievalService()

    print("=" * 70)
    print("RAG ON vs OFF — grounded lore retrieval")
    print("=" * 70)
    for cid, q in DEMO_PROMPTS:
        off = await run_one(cid, q, null)
        on = await run_one(cid, q, keyword)
        print(f"\n[{cid}] Q: {q}")
        print(f"  OFF  hits=0")
        print(f"  ON   hits={len(on.rag_hits)}")
        for h in on.rag_hits:
            first_line = h.text.split("\n", 1)[0][:60]
            print(f"       - (score={h.score:.1f}) {first_line}")

    print("\n" + "=" * 70)
    print("Cross-character isolation probes")
    print("=" * 70)
    all_zero = True
    for cid, q in CROSS_PROBES:
        hits = (await run_one(cid, q, keyword)).rag_hits
        status = "OK (0 hits)" if not hits else f"LEAK! {len(hits)} hits"
        if hits:
            all_zero = False
        print(f"  [{cid}] Q: {q}  → {status}")
    print()
    print(
        "Isolation verdict: "
        + ("PASS — no cross-character leakage." if all_zero else "FAIL.")
    )


if __name__ == "__main__":
    asyncio.run(main())
