from __future__ import annotations

import asyncio
import traceback
from datetime import datetime

import httpx
from fastapi import APIRouter, Query, HTTPException
import logging

from ..db import Enrichment, ICP, Lead, Score, ScoreHistory, ScoringConfig, ScoringJob, get_session
from ..models import ScoreResult
from ..services import enricher, openai_client, scorer, scorer_llm
from ..services.scraper import (
    USER_AGENT,
    fetch_homepage_nocache,
    read_cache,
    save_to_cache,
)

router = APIRouter(prefix="/score", tags=["score"])
logger = logging.getLogger(__name__)


def _safe_int(value, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    try:
        return int(value or default)
    except (ValueError, TypeError):
        return default


async def _enrich_one_nocache(
    domain: str, client: httpx.AsyncClient
) -> tuple[str, str, dict]:
    """Scrape one domain — HTTP only, NO database interaction.

    Returns (status, html, headers).
    """
    if not domain:
        return "skipped", "", {}

    try:
        html, headers, fetch_status = await fetch_homepage_nocache(
            domain, client=client
        )
        if fetch_status != "ok":
            return "error", "", {}
        return "ok", html, headers
    except Exception as exc:
        logger.warning("Scrape failed for %s: %s", domain, exc)
        return "error", "", {}


async def _score_one(lead_dict: dict, enrich_dict: dict, icp: dict, use_llm: bool) -> dict:
    """Score one lead, falling back to rule-based on any LLM failure."""
    if use_llm:
        # The OpenAI SDK is sync; run it in a thread so we can gather() many at once.
        result = await asyncio.to_thread(scorer_llm.score_lead_llm, lead_dict, enrich_dict, icp)
        if result is not None:
            return result
    return scorer.score_lead(lead_dict, enrich_dict, icp)


async def _do_score(only_unscored: bool) -> ScoreResult:
    """Internal scoring coroutine.

    Uses four sequential phases to avoid sharing a SQLAlchemy session
    across concurrent async operations:

    Phase 1 — DB Read:   Load leads, ICP, scrape cache (single session)
    Phase 2 — Scrape:    Concurrent HTTP requests (NO database access)
    Phase 3 — Score:     Compute scores (no database access)
    Phase 4 — DB Write:  Save enrichments, scores, cache (single session)
    """
    use_llm = openai_client.is_enabled()

    # ── Phase 1: Read everything from DB ──────────────────────────────
    with get_session() as s:
        job = ScoringJob(status="running")
        s.add(job)
        s.flush()
        job_id = job.id

        if only_unscored:
            scored_ids = {row[0] for row in s.query(Score.lead_id).all()}
            leads_raw = [l for l in s.query(Lead).all() if l.id not in scored_ids]
        else:
            leads_raw = s.query(Lead).all()

        if not leads_raw:
            job.status = "done"
            job.finished_at = datetime.utcnow()
            s.commit()
            return ScoreResult(scored=0, cached=0, failed=0)

        # Snapshot lead data into plain dicts so we don't need the session later
        lead_snapshots = []
        for lead in leads_raw:
            lead_snapshots.append({
                "id": lead.id,
                "company_name": lead.company_name or "",
                "domain": lead.domain or "",
                "website": lead.website or "",
                "industry": lead.industry or "",
                "employee_count": _safe_int(lead.employee_count),
                "location": lead.location or "",
            })

        icp_row = s.get(ICP, 1)
        config = s.get(ScoringConfig, 1)
        icp = {
            "industry_keywords": icp_row.industry_keywords if icp_row else "",
            "size_min": _safe_int(icp_row.size_min if icp_row else 0),
            "size_max": _safe_int(icp_row.size_max if icp_row else 10000, 10000),
            "value_prop": icp_row.value_prop if icp_row else "",
            "weights": (config.weights if config else {}) or {},
        }

        # Pre-read scrape cache so we skip HTTP for cached domains
        cached_scrapes: dict[str, tuple[str, dict]] = {}
        for snap in lead_snapshots:
            domain = snap["domain"]
            if domain:
                cached = read_cache(s, domain)
                if cached is not None:
                    cached_scrapes[domain] = cached

        s.commit()  # release session

    # ── Phase 2: Concurrent HTTP scraping (NO database access) ────────
    try:
        domains_to_scrape = []
        for snap in lead_snapshots:
            domain = snap["domain"]
            if domain and domain not in cached_scrapes:
                domains_to_scrape.append(domain)

        scrape_results: dict[str, tuple[str, str, dict]] = {}  # domain -> (status, html, headers)

        # Mark cached domains as "ok"
        for domain, (html, headers) in cached_scrapes.items():
            scrape_results[domain] = ("ok", html, headers)

        if domains_to_scrape:
            async with httpx.AsyncClient(
                timeout=5.0,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            ) as client:
                tasks = [
                    _enrich_one_nocache(domain, client)
                    for domain in domains_to_scrape
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for domain, result in zip(domains_to_scrape, results):
                    if isinstance(result, Exception):
                        logger.warning("Scrape exception for %s: %s", domain, result)
                        scrape_results[domain] = ("error", "", {})
                    else:
                        scrape_results[domain] = result

        # Run enrichment on scraped HTML (pure functions, no DB)
        lead_enrichments: list[tuple[str, dict, str, dict]] = []  # (status, enrich_dict, html, headers)
        for snap in lead_snapshots:
            domain = snap["domain"]
            if not domain:
                enrich_dict = enricher.enrich("", {})
                lead_enrichments.append(("skipped", enrich_dict, "", {}))
            elif domain in scrape_results:
                status, html, headers = scrape_results[domain]
                enrich_dict = enricher.enrich(html, headers) if status == "ok" else enricher.enrich("", {})
                lead_enrichments.append((status, enrich_dict, html, headers))
            else:
                enrich_dict = enricher.enrich("", {})
                lead_enrichments.append(("error", enrich_dict, "", {}))

    except Exception as exc:
        logger.exception("Phase 2 (scraping) failed")
        with get_session() as s:
            job = s.get(ScoringJob, job_id)
            if job:
                job.status = "failed"
                job.finished_at = datetime.utcnow()
                job.detail = f"Scraping phase failed: {exc}\n{traceback.format_exc()}"
                s.commit()
        raise

    # ── Phase 3: Compute scores (no DB access) ───────────────────────
    try:
        score_inputs = []
        for snap, (status, enrich_dict, _html, _headers) in zip(lead_snapshots, lead_enrichments):
            lead_dict = {
                "company_name": snap["company_name"],
                "industry": snap["industry"],
                "employee_count": snap["employee_count"],
                "location": snap["location"],
            }
            score_inputs.append((lead_dict, enrich_dict))

        # Score all leads concurrently (LLM calls run in thread pool)
        score_tasks = [
            _score_one(ld, ed, icp, use_llm) for ld, ed in score_inputs
        ]
        raw_score_results = await asyncio.gather(*score_tasks, return_exceptions=True)

        # Process results, replacing exceptions with a safe fallback
        score_results: list[dict] = []
        for i, result in enumerate(raw_score_results):
            if isinstance(result, Exception):
                logger.warning(
                    "Scoring failed for lead %s (%s): %s",
                    lead_snapshots[i]["id"],
                    lead_snapshots[i]["company_name"],
                    result,
                )
                # Fallback: zero score
                score_results.append({
                    "score": 0.0,
                    "tier": "C",
                    "reasons": [],
                    "why": "Scoring failed — review manually.",
                })
            else:
                score_results.append(result)

    except Exception as exc:
        logger.exception("Phase 3 (scoring) failed")
        with get_session() as s:
            job = s.get(ScoringJob, job_id)
            if job:
                job.status = "failed"
                job.finished_at = datetime.utcnow()
                job.detail = f"Scoring phase failed: {exc}\n{traceback.format_exc()}"
                s.commit()
        raise

    # ── Phase 4: Write everything to DB (single session) ─────────────
    try:
        with get_session() as s:
            scored = cached = failed = 0

            for snap, (status, enrich_dict, html, headers), scored_dict in zip(
                lead_snapshots, lead_enrichments, score_results
            ):
                lead_id = snap["id"]
                domain = snap["domain"]

                # Save scrape cache for newly scraped domains
                if status == "ok" and domain and domain not in cached_scrapes:
                    try:
                        save_to_cache(s, domain, html, headers)
                    except Exception as exc:
                        logger.warning("Failed to cache scrape for %s: %s", domain, exc)

                # Upsert enrichment
                existing = s.get(Enrichment, lead_id)
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
                            lead_id=lead_id,
                            title=enrich_dict["title"],
                            description=enrich_dict["description"],
                            tech_stack=enrich_dict["tech_stack"],
                            contacts=enrich_dict["contacts"],
                            signals=enrich_dict["signals"],
                            status=status,
                        )
                    )

                # Upsert score + history
                existing_score = s.get(Score, lead_id)
                next_version = (
                    s.query(ScoreHistory)
                    .filter(ScoreHistory.lead_id == lead_id)
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
                                lead_id=lead_id,
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
                            lead_id=lead_id,
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
                            lead_id=lead_id,
                            score=scored_dict["score"],
                            tier=scored_dict["tier"],
                            reasons=scored_dict["reasons"],
                            why=scored_dict["why"],
                        )
                    )

                if status == "ok":
                    scored += 1
                elif status == "skipped":
                    cached += 1
                else:
                    failed += 1

            # Mark job done
            job = s.get(ScoringJob, job_id)
            if job:
                job.status = "done"
                job.finished_at = datetime.utcnow()
            s.commit()

            return ScoreResult(scored=scored, cached=cached, failed=failed)

    except Exception as exc:
        logger.exception("Phase 4 (DB write) failed")
        with get_session() as s:
            job = s.get(ScoringJob, job_id)
            if job:
                job.status = "failed"
                job.finished_at = datetime.utcnow()
                job.detail = f"DB write phase failed: {exc}\n{traceback.format_exc()}"
                s.commit()
        raise



@router.post("", response_model=ScoreResult)
async def run_score(
    only_unscored: bool = Query(
        False,
        description="When true, score only leads that don't yet have a row in the scores table.",
    ),
) -> ScoreResult:
    try:
        return await _do_score(only_unscored)
    except Exception as exc:
        logging.exception("Error running scoring")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/start")
async def start_score_background(only_unscored: bool = Query(False)) -> dict:
    """Start scoring in the background and return immediately (202 accepted)."""
    try:
        # Schedule the scoring coroutine on the running event loop.
        asyncio.create_task(_do_score(only_unscored))
        return {"status": "accepted", "message": "Scoring started in background"}
    except Exception as exc:
        logging.exception("Failed to start background scoring")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/jobs")
def list_scoring_jobs(limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    """List recent scoring jobs for debugging."""
    with get_session() as s:
        rows = (
            s.query(ScoringJob).order_by(ScoringJob.id.desc()).limit(limit).all()
        )
        out = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "status": r.status,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                    "detail": r.detail,
                }
            )
        return out
