from __future__ import annotations

from fastapi import APIRouter

from ..services import openai_client

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def status() -> dict:
    enabled = openai_client.is_enabled()
    return {
        "ai_enabled": enabled,
        "has_key": openai_client.has_key(),
        "circuit_open": openai_client.circuit_open(),
        "model": openai_client.DEFAULT_MODEL if enabled else None,
    }
