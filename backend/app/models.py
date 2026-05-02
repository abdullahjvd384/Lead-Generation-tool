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
    quality: dict[str, Any] = Field(default_factory=dict)
    stage: str = "new"
    stage_reason: str = ""
    stage_updated_by: Optional[str] = None
    stage_updated_at: Optional[datetime] = None


class RankedLeadOut(LeadOut):
    rank: int
    next_step: str
    rank_reason: str


class RankedLeadListOut(BaseModel):
    limit: int
    total: int
    items: list[RankedLeadOut]


class PipelineStageIn(BaseModel):
    stage: str
    reason: str = ""
    updated_by: str = "system"


class PipelineStageOut(BaseModel):
    lead_id: int
    stage: str
    reason: str = ""
    updated_by: str = "system"
    updated_at: datetime


class PipelineHistoryOut(BaseModel):
    id: int
    lead_id: int
    from_stage: str
    to_stage: str
    reason: str = ""
    updated_by: str = "system"
    updated_at: datetime


class PipelineSummaryItem(BaseModel):
    stage: str
    count: int


class PipelineSummaryOut(BaseModel):
    total: int
    items: list[PipelineSummaryItem]


class LookalikeReasonOut(BaseModel):
    signal: str
    weight: float
    raw: float
    contribution: float
    details: list[str] = Field(default_factory=list)


class LookalikeMatchOut(BaseModel):
    lead: LeadOut
    similarity: float
    reasons: list[LookalikeReasonOut] = Field(default_factory=list)


class LookalikeListOut(BaseModel):
    seed_lead: LeadOut
    total: int
    limit: int
    items: list[LookalikeMatchOut]


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
