"""Chat service: OpenAI when a key is present, deterministic Dummy otherwise.

The Dummy service is not just a test fixture — it lets the whole persona
pipeline run (prompt rendering, RAG, API contract) without spending tokens
or requiring network. That matters for CI, for offline demos, and for
isolating prompt bugs from model variance during eval.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from app import config
from app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Character,
    RetrievalHit,
)
from app.prompts.character_prompts import render_system_prompt
from app.services.retrieval_service import (
    RetrievalServiceBase,
    get_retrieval_service,
)


class ChatServiceBase(ABC):
    model_name: str = "unknown"

    @abstractmethod
    async def reply(
        self,
        character: Character,
        messages: Iterable[ChatMessage],
        system_prompt: str,
    ) -> str: ...


class OpenAIChatService(ChatServiceBase):
    model_name = "openai"

    def __init__(self, api_key: str, model: str):
        from openai import AsyncOpenAI  # noqa: PLC0415

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.model_name = model

    async def reply(self, character, messages, system_prompt):
        payload = [{"role": "system", "content": system_prompt}]
        payload.extend({"role": m.role, "content": m.content} for m in messages)
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=payload,
            temperature=character.temperature
            if character.temperature is not None
            else config.DEFAULT_TEMPERATURE,
            max_tokens=character.max_tokens
            if character.max_tokens is not None
            else config.DEFAULT_MAX_TOKENS,
        )
        return resp.choices[0].message.content or ""


class DummyChatService(ChatServiceBase):
    """Deterministic persona-flavored stub. No network calls.

    Produces a response that reflects the character's tone settings and
    reports whether RAG context was injected into the system prompt — so
    the whole pipeline (persona + retrieval + renderer) is observable
    without an API key.
    """

    model_name = "dummy"

    async def reply(self, character, messages, system_prompt):
        last_user = next(
            (m.content for m in reversed(list(messages)) if m.role == "user"),
            "...",
        )
        opener = {
            "high": f"흐음... {character.name}이(가) 그대의 말을 들었소.",
            "mid": f"안녕하세요, 저는 {character.name}이에요.",
            "low": f"...어. 나 {character.name}.",
        }[character.tone.formality]
        echo = last_user if len(last_user) <= 40 else last_user[:40] + "..."
        rag_marker = "[RAG: 참고 자료 포함]" if "# 참고 자료" in system_prompt else "[RAG: off]"
        return (
            f"{opener} \"{echo}\" — 그대의 말은 잘 들었소. "
            f"(DUMMY 모드 · {rag_marker})"
        )


def get_chat_service() -> ChatServiceBase:
    if config.has_openai_key():
        return OpenAIChatService(api_key=config.OPENAI_API_KEY, model=config.OPENAI_MODEL)
    return DummyChatService()


async def generate_reply(
    request: ChatRequest,
    character: Character,
    chat_service: ChatServiceBase | None = None,
    retrieval_service: RetrievalServiceBase | None = None,
    include_prompt: bool = False,
) -> ChatResponse:
    """Orchestrate the full persona pipeline: RAG → prompt render → model call.

    This function is the single choke point every request passes through,
    which is exactly what eval harnesses need: one place to swap prompt
    versions, retrievers, or models and re-run a fixed dataset.
    """
    chat_service = chat_service or get_chat_service()
    retrieval_service = retrieval_service or get_retrieval_service()

    last_user = next(
        (m.content for m in reversed(request.messages) if m.role == "user"),
        "",
    )
    hits: list[RetrievalHit] = (
        await retrieval_service.search(last_user, character.id, k=3)
        if last_user
        else []
    )

    system_prompt = render_system_prompt(
        character, rag_hits=hits, version=request.prompt_version
    )

    reply_text = await chat_service.reply(
        character=character,
        messages=request.messages,
        system_prompt=system_prompt,
    )

    return ChatResponse(
        character_id=character.id,
        reply=reply_text,
        prompt_version=request.prompt_version,
        model=chat_service.model_name,
        rag_hits=hits,
        rendered_system_prompt=system_prompt if include_prompt else None,
    )
