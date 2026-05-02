from __future__ import annotations

from fastapi import APIRouter

from ..services import gemini

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def status() -> dict:
    enabled = gemini.is_enabled()
    return {
        "ai_enabled": enabled,
        "has_key": gemini.has_key(),
        "circuit_open": gemini.circuit_open(),
        "model": gemini.DEFAULT_MODEL if enabled else None,
    }
