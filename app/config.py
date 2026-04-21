"""Runtime configuration loaded from environment.

Kept as a flat module (not pydantic-settings) so that tests and scripts can
monkey-patch values without instantiating a settings object.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

CHARACTERS_DIR: Path = PROJECT_ROOT / os.environ.get("CHARACTERS_DIR", "characters")
LORE_DIR: Path = PROJECT_ROOT / os.environ.get("LORE_DIR", "data/lore")
FAISS_DIR: Path = PROJECT_ROOT / os.environ.get("FAISS_DIR", "data/faiss")

RAG_ENABLED: bool = os.environ.get("RAG_ENABLED", "false").lower() == "true"

DEFAULT_TEMPERATURE: float = float(os.environ.get("DEFAULT_TEMPERATURE", "0.8"))
DEFAULT_MAX_TOKENS: int = int(os.environ.get("DEFAULT_MAX_TOKENS", "600"))


def has_openai_key() -> bool:
    return bool(OPENAI_API_KEY.strip())
