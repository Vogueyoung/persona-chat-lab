"""FastAPI entry point for persona-chat-lab."""

from __future__ import annotations

from fastapi import FastAPI

from app import config
from app.api import characters, chat

app = FastAPI(
    title="persona-chat-lab",
    description=(
        "Prompt-engineering lab for persona-based character chat. "
        "Explore the system prompts with `?debug=true` on /api/chat."
    ),
    version="0.1.0",
)

app.include_router(characters.router)
app.include_router(chat.router)


@app.get("/api/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "model_mode": "openai" if config.has_openai_key() else "dummy",
        "rag_enabled": config.RAG_ENABLED,
    }
