"""Pydantic schemas for characters, chat requests, and API responses.

The Character schema is the contract between a YAML persona card and the
prompt renderer. Keeping it explicit (rather than a free-form dict) is a
prompt-engineering discipline: it forces every persona to declare tone,
style, and guardrails in the same slots so prompt versions stay comparable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["low", "mid", "high"]
Verbosity = Literal["terse", "concise", "verbose"]


class ToneConfig(BaseModel):
    formality: Level = "mid"
    warmth: Level = "mid"
    humor: Level = "low"
    verbosity: Verbosity = "concise"


class DialogueExample(BaseModel):
    user: str
    assistant: str


class Character(BaseModel):
    id: str
    name: str
    title: str | None = None
    language: str = "ko"
    tone: ToneConfig = Field(default_factory=ToneConfig)
    personality: list[str] = Field(default_factory=list)
    speaking_style: list[str] = Field(default_factory=list)
    backstory: str = ""
    forbidden_topics: list[str] = Field(default_factory=list)
    example_dialogues: list[DialogueExample] = Field(default_factory=list)
    greeting: str | None = None
    lore_tags: list[str] = Field(default_factory=list)

    # Per-character generation overrides (optional).
    temperature: float | None = None
    max_tokens: int | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    character_id: str
    messages: list[ChatMessage]
    # Prompt-engineering knob: let callers force a specific prompt version
    # for A/B comparison without changing the character file.
    prompt_version: str = "v1"


class RetrievalHit(BaseModel):
    text: str
    source: str
    score: float


class ChatResponse(BaseModel):
    character_id: str
    reply: str
    prompt_version: str
    model: str
    rag_hits: list[RetrievalHit] = Field(default_factory=list)
    rendered_system_prompt: str | None = None  # debugging aid; omitted in prod
