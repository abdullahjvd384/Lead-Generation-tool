from __future__ import annotations

import csv
import io
import os
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from ..db import (
    Enrichment,
    ICP,
    Lead,
    LeadPipeline,
    LeadPipelineHistory,
    Score,
    get_session,
)
from ..models import (
    LeadOut,
    LookalikeListOut,
    LookalikeMatchOut,
    LookalikeReasonOut,
    PipelineHistoryOut,
    PipelineStageIn,
    PipelineStageOut,
    PipelineSummaryItem,
    PipelineSummaryOut,
    RankedLeadListOut,
    RankedLeadOut,
    UploadResult,
)
from ..services import csv_mapper
from ..services.dedupe import normalize_domain
from ..services.quality import assess_lead_quality
from ..services.workflows import lookalike_matches, rank_leads

router = APIRouter(prefix="/leads", tags=["leads"])


def _hydrate(s, leads: list[Lead]) -> list[LeadOut]:
    out: list[LeadOut] = []
    icp_row = s.get(ICP, 1)
    icp = {
        "size_min": icp_row.size_min if icp_row else 0,
        "size_max": icp_row.size_max if icp_row else 10000,
    }
    for lead in leads:
        e = s.get(Enrichment, lead.id)
        sc = s.get(Score, lead.id)
        pipeline = s.get(LeadPipeline, lead.id)
        lead_dict = {
            "company_name": lead.company_name or "",
            "website": lead.website or "",
            "domain": lead.domain or "",
            "industry": lead.industry or "",
            "employee_count": lead.employee_count or 0,
            "location": lead.location or "",
        }
        enrich_dict = {
            "contacts": (e.contacts if e else {}) or {},
            "status": (e.status if e else None),
        }
        score_dict = (
            {
                "score": sc.score,
                "tier": sc.tier,
                "reasons": (sc.reasons or []),
            }
            if sc
            else None
        )
        out.append(
            LeadOut(
                id=lead.id,
                company_name=lead.company_name,
                website=lead.website or "",
                domain=lead.domain or "",
                industry=lead.industry or "",
                employee_count=lead.employee_count or 0,
                location=lead.location or "",
                title=(e.title if e else None),
                description=(e.description if e else None),
                tech_stack=(e.tech_stack if e else []) or [],
                contacts=(e.contacts if e else {}) or {},
                signals=(e.signals if e else {}) or {},
                status=(e.status if e else None),
                score=(sc.score if sc else None),
                tier=(sc.tier if sc else None),
                why=(sc.why if sc else None),
                reasons=(sc.reasons if sc else []) or [],
                quality=assess_lead_quality(lead_dict, enrich_dict, score_dict, icp),
                stage=(pipeline.stage if pipeline else "new"),
                stage_reason=(pipeline.reason if pipeline else ""),
                stage_updated_by=(pipeline.updated_by if pipeline else None),
                stage_updated_at=(pipeline.updated_at if pipeline else None),
            )
        )
    return out


def _stage_row(s, lead_id: int) -> LeadPipeline:
    row = s.get(LeadPipeline, lead_id)
    if row is None:
        row = LeadPipeline(lead_id=lead_id, stage="new", reason="", updated_by="system")
        s.add(row)
        s.flush()
    return row


@router.get("/ranked", response_model=RankedLeadListOut)
def ranked_leads(
    limit: int = Query(10, ge=1, le=100),
    stage: Optional[str] = Query(default=None),
    tier: Optional[str] = Query(default=None),
) -> RankedLeadListOut:
    with get_session() as s:
        leads = _hydrate(s, s.query(Lead).order_by(Lead.id.asc()).all())

    rows = leads
    if stage:
        stage_filter = stage.strip().lower()
        rows = [row for row in rows if row.stage == stage_filter]
    if tier:
        tier_filter = tier.strip().upper()
        rows = [row for row in rows if (row.tier or "") == tier_filter]

    ranked = rank_leads([row.model_dump() for row in rows])
    items = [RankedLeadOut(**item) for item in ranked[:limit]]
    return RankedLeadListOut(limit=limit, total=len(ranked), items=items)


@router.get("/pipeline", response_model=PipelineSummaryOut)
def pipeline_summary() -> PipelineSummaryOut:
    with get_session() as s:
        leads = s.query(Lead).all()
        counts = {"new": 0, "contacted": 0, "qualified": 0, "dead": 0}
        for lead in leads:
            row = s.get(LeadPipeline, lead.id)
            stage = (row.stage if row else "new").strip().lower()
            if stage not in counts:
                stage = "new"
            counts[stage] += 1
    return PipelineSummaryOut(
        total=sum(counts.values()),
        items=[PipelineSummaryItem(stage=stage, count=count) for stage, count in counts.items()],
    )


@router.put("/{lead_id}/stage", response_model=PipelineStageOut)
def update_lead_stage(lead_id: int, payload: PipelineStageIn) -> PipelineStageOut:
    stage = payload.stage.strip().lower()
    if stage not in {"new", "contacted", "qualified", "dead"}:
        raise HTTPException(status_code=400, detail="invalid stage")

    with get_session() as s:
        lead = s.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="lead not found")

        row = _stage_row(s, lead_id)
        previous_stage = row.stage or "new"
        row.stage = stage
        row.reason = payload.reason or ""
        row.updated_by = payload.updated_by or "system"

        s.add(
            LeadPipelineHistory(
                lead_id=lead_id,
                from_stage=previous_stage,
                to_stage=stage,
                reason=payload.reason or "",
                updated_by=payload.updated_by or "system",
            )
        )
        s.commit()
        s.refresh(row)

    return PipelineStageOut(
        lead_id=lead_id,
        stage=row.stage,
        reason=row.reason or "",
        updated_by=row.updated_by or "system",
        updated_at=row.updated_at,
    )


@router.get("/{lead_id}/stage/history", response_model=list[PipelineHistoryOut])
def lead_stage_history(lead_id: int) -> list[PipelineHistoryOut]:
    with get_session() as s:
        rows = (
            s.query(LeadPipelineHistory)
            .filter(LeadPipelineHistory.lead_id == lead_id)
            .order_by(LeadPipelineHistory.updated_at.desc(), LeadPipelineHistory.id.desc())
            .all()
        )
    return [
        PipelineHistoryOut(
            id=row.id,
            lead_id=row.lead_id,
            from_stage=row.from_stage,
            to_stage=row.to_stage,
            reason=row.reason or "",
            updated_by=row.updated_by or "system",
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/{lead_id}/lookalikes", response_model=LookalikeListOut)
def lead_lookalikes(lead_id: int, limit: int = Query(10, ge=1, le=50)) -> LookalikeListOut:
    with get_session() as s:
        lead = s.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="lead not found")
        seed = _hydrate(s, [lead])[0]
        candidates = _hydrate(s, s.query(Lead).filter(Lead.id != lead_id).all())

    matches = lookalike_matches(seed.model_dump(), [candidate.model_dump() for candidate in candidates], limit=limit)
    items = [
        LookalikeMatchOut(
            lead=LeadOut(**match["lead"]),
            similarity=match["similarity"],
            reasons=[LookalikeReasonOut(**reason) for reason in match["reasons"]],
        )
        for match in matches
    ]
    return LookalikeListOut(seed_lead=seed, total=len(matches), limit=limit, items=items)


@router.get("", response_model=list[LeadOut])
def list_leads() -> list[LeadOut]:
    with get_session() as s:
        leads = s.query(Lead).order_by(Lead.id.asc()).all()
        return _hydrate(s, leads)


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int) -> LeadOut:
    with get_session() as s:
        lead = s.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="lead not found")
        return _hydrate(s, [lead])[0]


def _ingest_records(
    records: list[dict],
    *,
    mapping_used: dict[str, str] | None = None,
    mapping_source: str = "exact",
) -> UploadResult:
    inserted = duplicates = invalid = 0
    with get_session() as s:
        for rec in records:
            name = (rec.get("company_name") or "").strip()
            if not name:
                invalid += 1
                continue
            website = (rec.get("website") or "").strip()
            domain = normalize_domain(website) if website else ""
            # Dedupe on domain when present, else on (lowercased) name.
            dedup_key = domain or name.lower()

            existing = None
            if domain:
                existing = s.query(Lead).filter(Lead.domain == domain).first()
            else:
                existing = s.query(Lead).filter(
                    Lead.domain == "", Lead.company_name.ilike(name)
                ).first()
            if existing:
                duplicates += 1
                continue

            try:
                emp = int(rec.get("employee_count") or 0)
            except (TypeError, ValueError):
                emp = 0

            s.add(
                Lead(
                    company_name=name,
                    website=website,
                    domain=domain or dedup_key,  # ensures uniqueness even with no website
                    industry=(rec.get("industry") or "").strip(),
                    employee_count=emp,
                    location=(rec.get("location") or "").strip(),
                )
            )
            inserted += 1
        s.commit()
        total = s.query(Lead).count()
    return UploadResult(
        inserted=inserted,
        duplicates=duplicates,
        invalid=invalid,
        total_leads=total,
        mapping_used=mapping_used or {},
        mapping_source=mapping_source,
    )


@router.post("/upload", response_model=UploadResult)
async def upload_csv(file: UploadFile = File(...)) -> UploadResult:
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"could not parse CSV: {exc}")

    df, mapping_used, source = csv_mapper.normalize_columns(df)

    if "company_name" not in df.columns:
        cols = ", ".join(str(c) for c in df.columns)
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not find a company-name column in the CSV. "
                f"Found columns: [{cols}]. "
                "Please rename one of them to 'company_name' (or 'Company', 'Account Name', "
                "'Business Name', etc.) and re-upload."
            ),
        )

    records = df.to_dict(orient="records")
    return _ingest_records(records, mapping_used=mapping_used, mapping_source=source)


@router.post("/seed", response_model=UploadResult)
def seed_demo() -> UploadResult:
    here = os.path.dirname(os.path.dirname(__file__))
    seed_path = os.path.join(here, "seed", "demo_leads.csv")
    if not os.path.exists(seed_path):
        raise HTTPException(status_code=500, detail=f"seed file missing: {seed_path}")
    df = pd.read_csv(seed_path)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return _ingest_records(df.to_dict(orient="records"))


@router.delete("", response_model=UploadResult)
def reset_leads() -> UploadResult:
    with get_session() as s:
        s.query(Score).delete()
        s.query(Enrichment).delete()
        s.query(LeadPipelineHistory).delete()
        s.query(LeadPipeline).delete()
        s.query(Lead).delete()
        s.commit()
    return UploadResult(inserted=0, duplicates=0, invalid=0, total_leads=0)


@router.get("/export/csv")
def export_csv(tier: Optional[str] = None) -> StreamingResponse:
    with get_session() as s:
        leads = s.query(Lead).all()
        rows = _hydrate(s, leads)

    if tier:
        rows = [r for r in rows if (r.tier or "") == tier.upper()]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["company", "website", "industry", "employee_count", "location",
         "score", "tier", "recommended_action", "confidence", "risk_flags",
         "why", "primary_email", "linkedin"]
    )
    for r in rows:
        contacts = r.contacts or {}
        emails = contacts.get("emails") or []
        social = contacts.get("social") or {}
        quality = r.quality or {}
        writer.writerow(
            [
                r.company_name,
                r.website,
                r.industry,
                r.employee_count,
                r.location,
                r.score if r.score is not None else "",
                r.tier or "",
                quality.get("recommended_action", ""),
                quality.get("confidence", ""),
                "; ".join(quality.get("risk_flags") or []),
                r.why or "",
                emails[0] if emails else "",
                social.get("linkedin", ""),
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
