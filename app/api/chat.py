"""Chat API — the only endpoint a reviewer really needs to try.

Accepts a character_id + message history + prompt_version, routes through
the persona pipeline, and returns the reply plus diagnostic fields (RAG
hits, rendered prompt when requested) so the response itself doubles as
a debugging view.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ChatRequest, ChatResponse
from app.prompts.character_prompts import available_versions
from app.services.character_loader import CharacterNotFoundError, get_character
from app.services.chat_service import generate_reply

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    debug: bool = Query(
        default=False,
        description="If true, include the rendered system prompt in the response.",
    ),
):
    try:
        character = get_character(request.character_id)
    except CharacterNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"character not found: {exc}") from exc

    if request.prompt_version not in available_versions():
        raise HTTPException(
            status_code=400,
            detail=f"unknown prompt_version. available: {available_versions()}",
        )

    return await generate_reply(request, character, include_prompt=debug)
