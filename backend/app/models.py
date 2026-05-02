from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ICPIn(BaseModel):
    industry_keywords: str = ""
    size_min: int = 0
    size_max: int = 10000
    value_prop: str = ""


class ICPOut(ICPIn):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadIn(BaseModel):
    company_name: str
    website: str = ""
    industry: str = ""
    employee_count: int = 0
    location: str = ""


class LeadOut(BaseModel):
    id: int
    company_name: str
    website: str
    domain: str
    industry: str
    employee_count: int
    location: str
    score: Optional[float] = None
    tier: Optional[str] = None
    why: Optional[str] = None
    status: Optional[str] = None  # enrichment status
    title: Optional[str] = None
    description: Optional[str] = None
    tech_stack: list[str] = Field(default_factory=list)
    contacts: dict[str, Any] = Field(default_factory=dict)
    signals: dict[str, Any] = Field(default_factory=dict)
    reasons: list[dict[str, Any]] = Field(default_factory=list)


class UploadResult(BaseModel):
    inserted: int
    duplicates: int
    invalid: int
    total_leads: int
    mapping_used: dict[str, str] = Field(default_factory=dict)
    mapping_source: str = "exact"  # exact | alias | gemini | none


class ScoreResult(BaseModel):
    scored: int
    cached: int
    failed: int


class OutreachOut(BaseModel):
    subject: str
    body: str
