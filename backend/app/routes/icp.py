from __future__ import annotations

from fastapi import APIRouter

from ..db import ICP, get_session
from ..models import ICPIn, ICPOut

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
