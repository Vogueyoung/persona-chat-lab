"""Load Character cards from YAML files on disk.

One file per character. Hot-reload on every request for dev ergonomics —
tuning a persona should not require a server restart.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app import config
from app.models.schemas import Character


class CharacterNotFoundError(KeyError):
    pass


def _load_one(path: Path) -> Character:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Character(**data)


def list_characters() -> list[Character]:
    files = sorted(config.CHARACTERS_DIR.glob("*.yaml")) + sorted(
        config.CHARACTERS_DIR.glob("*.yml")
    )
    return [_load_one(p) for p in files]


def get_character(character_id: str) -> Character:
    for path in config.CHARACTERS_DIR.glob("*.y*ml"):
        if path.stem == character_id:
            return _load_one(path)
    raise CharacterNotFoundError(character_id)


@lru_cache(maxsize=1)
def _cached_ids() -> tuple[str, ...]:
    return tuple(c.id for c in list_characters())


def known_ids() -> tuple[str, ...]:
    return _cached_ids()
