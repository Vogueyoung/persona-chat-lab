"""Characters API — list + lookup for the YAML-backed persona cards."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import Character
from app.services.character_loader import (
    CharacterNotFoundError,
    get_character,
    list_characters,
)

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.get("", response_model=list[Character])
async def get_all_characters():
    return list_characters()


@router.get("/{character_id}", response_model=Character)
async def get_one_character(character_id: str):
    try:
        return get_character(character_id)
    except CharacterNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"character not found: {exc}") from exc
