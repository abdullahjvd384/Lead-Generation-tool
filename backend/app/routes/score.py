from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
from fastapi import APIRouter, Query

from ..db import Enrichment, ICP, Lead, Score, ScoreHistory, ScoringConfig, get_session
from ..models import ScoreResult
from ..services import enricher, openai_client, scorer, scorer_llm
from ..services.scraper import USER_AGENT, fetch_homepage

router = APIRouter(prefix="/score", tags=["score"])


async def _enrich_one(s, client, lead: Lead) -> tuple[str, dict]:
    """Returns (status, enrichment_dict). 'skipped' if the lead has no website."""
    if not lead.domain:
        return "skipped", enricher.enrich("", {})

    html, headers, fetch_status = await fetch_homepage(s, lead.domain, client=client)
    if fetch_status != "ok":
        return "error", enricher.enrich("", {})
    return "ok", enricher.enrich(html, headers)


async def _score_one(lead_dict: dict, enrich_dict: dict, icp: dict, use_llm: bool) -> dict:
    """Score one lead, falling back to rule-based on any LLM failure."""
    if use_llm:
        # The OpenAI SDK is sync; run it in a thread so we can gather() many at once.
        result = await asyncio.to_thread(scorer_llm.score_lead_llm, lead_dict, enrich_dict, icp)
        if result is not None:
            return result
    return scorer.score_lead(lead_dict, enrich_dict, icp)


@router.post("", response_model=ScoreResult)
async def run_score(
    only_unscored: bool = Query(
        False,
        description="When true, score only leads that don't yet have a row in the scores table.",
    ),
) -> ScoreResult:
    use_llm = openai_client.is_enabled()

    with get_session() as s:
        if only_unscored:
            scored_ids = {row[0] for row in s.query(Score.lead_id).all()}
            leads = [l for l in s.query(Lead).all() if l.id not in scored_ids]
        else:
            leads = s.query(Lead).all()

        if not leads:
            return ScoreResult(scored=0, cached=0, failed=0)

        icp_row = s.get(ICP, 1)
        config = s.get(ScoringConfig, 1)
        icp = {
            "industry_keywords": icp_row.industry_keywords,
            "size_min": icp_row.size_min,
            "size_max": icp_row.size_max,
            "value_prop": icp_row.value_prop,
            "weights": (config.weights if config else {}) or {},
        }

        # Phase 1 — scrape + enrich all leads in parallel.
        async with httpx.AsyncClient(
            timeout=5.0,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            enrich_results = await asyncio.gather(
                *[_enrich_one(s, client, lead) for lead in leads]
            )

        # Phase 2 — score all leads in parallel (OpenAI calls run in threads).
        score_inputs = []
        for lead, (_status, enrich_dict) in zip(leads, enrich_results):
            score_inputs.append(
                (
                    {
                        "company_name": lead.company_name,
                        "industry": lead.industry,
                        "employee_count": lead.employee_count,
                        "location": lead.location,
                    },
                    enrich_dict,
                )
            )
        score_results = await asyncio.gather(
            *[_score_one(ld, ed, icp, use_llm) for ld, ed in score_inputs]
        )

        # Phase 3 — write everything to SQLite in one transaction.
        scored = cached = failed = 0
        for lead, (status, enrich_dict), scored_dict in zip(
            leads, enrich_results, score_results
        ):
            existing = s.get(Enrichment, lead.id)
            if existing:
                existing.title = enrich_dict["title"]
                existing.description = enrich_dict["description"]
                existing.tech_stack = enrich_dict["tech_stack"]
                existing.contacts = enrich_dict["contacts"]
                existing.signals = enrich_dict["signals"]
                existing.fetched_at = datetime.utcnow()
                existing.status = status
            else:
                s.add(
                    Enrichment(
                        lead_id=lead.id,
                        title=enrich_dict["title"],
                        description=enrich_dict["description"],
                        tech_stack=enrich_dict["tech_stack"],
                        contacts=enrich_dict["contacts"],
                        signals=enrich_dict["signals"],
                        status=status,
                    )
                )

            existing_score = s.get(Score, lead.id)
            next_version = (
                s.query(ScoreHistory)
                .filter(ScoreHistory.lead_id == lead.id)
                .count()
                + 1
            )
            if existing_score:
                changed = (
                    round(float(existing_score.score or 0), 1)
                    != round(float(scored_dict["score"] or 0), 1)
                    or (existing_score.tier or "") != (scored_dict["tier"] or "")
                    or (existing_score.why or "") != (scored_dict["why"] or "")
                )
                if changed:
                    s.add(
                        ScoreHistory(
                            lead_id=lead.id,
                            previous_score=existing_score.score,
                            previous_tier=existing_score.tier or "",
                            new_score=scored_dict["score"],
                            new_tier=scored_dict["tier"],
                            previous_why=existing_score.why or "",
                            new_why=scored_dict["why"],
                            version=next_version,
                        )
                    )
                existing_score.score = scored_dict["score"]
                existing_score.tier = scored_dict["tier"]
                existing_score.reasons = scored_dict["reasons"]
                existing_score.why = scored_dict["why"]
                existing_score.scored_at = datetime.utcnow()
            else:
                s.add(
                    ScoreHistory(
                        lead_id=lead.id,
                        previous_score=None,
                        previous_tier="",
                        new_score=scored_dict["score"],
                        new_tier=scored_dict["tier"],
                        previous_why="",
                        new_why=scored_dict["why"],
                        version=next_version,
                    )
                )
                s.add(
                    Score(
                        lead_id=lead.id,
                        score=scored_dict["score"],
                        tier=scored_dict["tier"],
                        reasons=scored_dict["reasons"],
                        why=scored_dict["why"],
                    )
                )

            if status == "ok":
                scored += 1
            elif status == "skipped":
                cached += 1  # leads scored without scraping (no website)
            else:
                failed += 1

        s.commit()
    return ScoreResult(scored=scored, cached=cached, failed=failed)
