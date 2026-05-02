from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query

from ..db import Enrichment, ICP, Lead, OutreachDraft, Score, get_session
from ..models import OutreachOut
from ..services import openai_client, outreach_llm
from ..services.outreach import generate_email

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/{lead_id}", response_model=OutreachOut)
async def make_email(
    lead_id: int,
    tone: str = Query("direct", pattern="^(direct|warm|executive)$"),
) -> OutreachOut:
    with get_session() as s:
        lead = s.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="lead not found")
        e = s.get(Enrichment, lead_id)
        sc = s.get(Score, lead_id)
        icp_row = s.get(ICP, 1)

    lead_dict = {
        "company_name": lead.company_name,
        "industry": lead.industry,
    }
    enrich_dict = {
        "title": e.title if e else "",
        "description": e.description if e else "",
        "tech_stack": (e.tech_stack if e else []) or [],
        "contacts": (e.contacts if e else {}) or {},
        "signals": (e.signals if e else {}) or {},
    }
    score_dict = {
        "score": sc.score if sc else 0,
        "tier": sc.tier if sc else "C",
        "reasons": (sc.reasons if sc else []) or [],
        "why": sc.why if sc else "",
    }
    icp_dict = {
        "industry_keywords": icp_row.industry_keywords,
        "value_prop": icp_row.value_prop,
        "tone": tone,
    }

    out: dict | None = None
    if openai_client.is_enabled():
        # SDK is sync — push to a thread so we don't block the event loop.
        out = await asyncio.to_thread(
            outreach_llm.generate_email_llm, lead_dict, enrich_dict, score_dict, icp_dict
        )
    if out is None:
        out = generate_email(lead_dict, enrich_dict, score_dict, icp_dict)

    with get_session() as s:
        draft = OutreachDraft(
            lead_id=lead_id,
            tone=tone,
            subject=out["subject"],
            body=out["body"],
        )
        s.add(draft)
        s.commit()
        s.refresh(draft)

    return OutreachOut(
        id=draft.id,
        tone=draft.tone,
        subject=draft.subject,
        body=draft.body,
        created_at=draft.created_at,
    )


@router.get("/{lead_id}/drafts", response_model=list[OutreachOut])
def list_drafts(lead_id: int) -> list[OutreachOut]:
    with get_session() as s:
        rows = (
            s.query(OutreachDraft)
            .filter(OutreachDraft.lead_id == lead_id)
            .order_by(OutreachDraft.created_at.desc(), OutreachDraft.id.desc())
            .all()
        )
    return [
        OutreachOut(
            id=row.id,
            tone=row.tone or "direct",
            subject=row.subject or "",
            body=row.body or "",
            created_at=row.created_at,
        )
        for row in rows
    ]
