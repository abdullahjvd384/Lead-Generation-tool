from __future__ import annotations

from fastapi import APIRouter

from ..db import DEFAULT_SCORING_WEIGHTS, ICP, ScoringConfig, get_session
from ..models import ICPIn, ICPOut, ScoringConfigIn, ScoringConfigOut

router = APIRouter(prefix="/icp", tags=["icp"])


@router.get("", response_model=ICPOut)
def get_icp() -> ICPOut:
    with get_session() as s:
        row = s.get(ICP, 1)
        return ICPOut.model_validate(row)


@router.put("", response_model=ICPOut)
def put_icp(payload: ICPIn) -> ICPOut:
    with get_session() as s:
        row = s.get(ICP, 1)
        row.industry_keywords = payload.industry_keywords
        row.size_min = payload.size_min
        row.size_max = payload.size_max
        row.value_prop = payload.value_prop
        s.commit()
        s.refresh(row)
        return ICPOut.model_validate(row)


@router.get("/scoring", response_model=ScoringConfigOut)
def get_scoring_config() -> ScoringConfigOut:
    with get_session() as s:
        row = s.get(ScoringConfig, 1)
        if row is None:
            row = ScoringConfig(
                id=1,
                template="Balanced",
                weights=DEFAULT_SCORING_WEIGHTS.copy(),
                version=1,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
        return ScoringConfigOut(
            id=row.id,
            template=row.template or "Balanced",
            weights=row.weights or DEFAULT_SCORING_WEIGHTS.copy(),
            version=row.version or 1,
            updated_at=row.updated_at,
        )


@router.put("/scoring", response_model=ScoringConfigOut)
def put_scoring_config(payload: ScoringConfigIn) -> ScoringConfigOut:
    cleaned: dict[str, float] = {}
    for signal, default in DEFAULT_SCORING_WEIGHTS.items():
        try:
            cleaned[signal] = max(0.0, float(payload.weights.get(signal, default)))
        except (TypeError, ValueError, AttributeError):
            cleaned[signal] = float(default)

    total = sum(cleaned.values())
    if total <= 0:
        cleaned = {signal: float(weight) for signal, weight in DEFAULT_SCORING_WEIGHTS.items()}
    else:
        cleaned = {signal: round((weight / total) * 100, 2) for signal, weight in cleaned.items()}

    with get_session() as s:
        row = s.get(ScoringConfig, 1)
        if row is None:
            row = ScoringConfig(id=1, version=0)
            s.add(row)
            s.flush()
        row.template = payload.template.strip() or "Custom"
        row.weights = cleaned
        row.version = int(row.version or 0) + 1
        s.commit()
        s.refresh(row)
        return ScoringConfigOut(
            id=row.id,
            template=row.template,
            weights=row.weights or cleaned,
            version=row.version,
            updated_at=row.updated_at,
        )
