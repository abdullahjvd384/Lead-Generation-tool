from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from ..db import ScrapeCache

USER_AGENT = "LeadQualifier/0.1 (+contact: leadqualifier@example.com)"
TIMEOUT_S = 5.0
MAX_CONCURRENCY = 2
PER_DOMAIN_GAP_S = 1.0
CACHE_TTL = timedelta(days=7)

_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
_domain_locks: dict[str, asyncio.Lock] = {}


def _candidate_urls(domain: str) -> list[str]:
    host = (domain or "").strip().lower()
    if not host:
        return []
    if "://" in host:
        parsed = urlparse(host)
        host = (parsed.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if not host:
        return []

    variants = []
    for prefix in ("https://", "http://"):
        variants.append(f"{prefix}{host}/")
        variants.append(f"{prefix}www.{host}/")
    return list(dict.fromkeys(variants))


def _lock_for(domain: str) -> asyncio.Lock:
    lock = _domain_locks.get(domain)
    if lock is None:
        lock = asyncio.Lock()
        _domain_locks[domain] = lock
    return lock


def _cached(session: Session, domain: str) -> Optional[ScrapeCache]:
    row = session.get(ScrapeCache, domain)
    if row and row.fetched_at and (datetime.utcnow() - row.fetched_at) < CACHE_TTL:
        return row
    return None


async def fetch_homepage(
    session: Session, domain: str, *, client: Optional[httpx.AsyncClient] = None
) -> tuple[str, dict, str]:
    """Return (html, headers, status). Uses SQLite cache with 7-day TTL.

    Status: 'ok' on success/cache, 'error' on failure (html will be empty).
    Failures are not cached so a transient outage doesn't poison results.
    """
    if not domain:
        return "", {}, "error"

    cached = _cached(session, domain)
    if cached:
        return cached.html or "", cached.headers or {}, "ok"

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(
            timeout=TIMEOUT_S,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    async with _semaphore, _lock_for(domain):
        # Per-domain politeness gap.
        await asyncio.sleep(PER_DOMAIN_GAP_S)
        try:
            html, headers, status = "", {}, "error"
            for url in _candidate_urls(domain):
                try:
                    resp = await client.get(url)
                    if resp.status_code < 400 and (resp.text or "").strip():
                        html = resp.text or ""
                        headers = dict(resp.headers)
                        status = "ok"
                        break
                except Exception:
                    continue
        finally:
            if own_client:
                await client.aclose()

    if status == "ok":
        existing = session.get(ScrapeCache, domain)
        if existing:
            existing.html = html
            existing.headers = headers
            existing.fetched_at = datetime.utcnow()
        else:
            session.add(
                ScrapeCache(
                    domain=domain,
                    html=html,
                    headers=headers,
                    fetched_at=datetime.utcnow(),
                )
            )
        session.commit()

    return html, headers, status
