from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

# (Display name, regex tested against page HTML and headers, lowercased)
TECH_SIGNATURES: list[tuple[str, re.Pattern]] = [
    ("HubSpot", re.compile(r"hubspot|hs-scripts|hs-analytics", re.I)),
    ("Salesforce", re.compile(r"salesforce|force\.com|pardot", re.I)),
    ("Marketo", re.compile(r"marketo|munchkin\.js", re.I)),
    ("Intercom", re.compile(r"intercom", re.I)),
    ("Drift", re.compile(r"drift\.com|driftt\.com", re.I)),
    ("Segment", re.compile(r"segment\.io|analytics\.js", re.I)),
    ("Mixpanel", re.compile(r"mixpanel", re.I)),
    ("Amplitude", re.compile(r"amplitude", re.I)),
    ("Stripe", re.compile(r"js\.stripe\.com|stripe", re.I)),
    ("Shopify", re.compile(r"cdn\.shopify\.com|shopify", re.I)),
    ("WordPress", re.compile(r"wp-content|wp-includes|wordpress", re.I)),
    ("Webflow", re.compile(r"webflow", re.I)),
    ("React", re.compile(r"__NEXT_DATA__|react-dom|_next/static", re.I)),
    ("Google Analytics", re.compile(r"google-analytics|gtag/js|ga\.js", re.I)),
    ("Cloudflare", re.compile(r"cloudflare", re.I)),
]

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
SOCIAL_HOSTS = {
    "linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "youtube.com": "youtube",
}
HIRING_RE = re.compile(r"\b(careers|hiring|we'?re hiring|join us|jobs|open roles)\b", re.I)
FOUNDED_RE = re.compile(r"\b(founded|since|established)\s+(in\s+)?(\d{4})\b", re.I)


def detect_tech_stack(html: str, headers: dict) -> list[str]:
    blob_parts = [html or ""]
    for k, v in (headers or {}).items():
        blob_parts.append(f"{k}: {v}")
    blob = "\n".join(blob_parts)
    found = []
    for name, pattern in TECH_SIGNATURES:
        if pattern.search(blob):
            found.append(name)
    return found


def extract_contacts(html: str, soup: BeautifulSoup) -> dict[str, Any]:
    text = soup.get_text(" ", strip=True) if soup else ""

    emails = sorted({e for e in EMAIL_RE.findall(html or "") if not e.lower().endswith((".png", ".jpg", ".gif"))})
    # Strip obvious junk emails (sentry, wixpress, etc.)
    emails = [e for e in emails if not any(noise in e.lower() for noise in ("sentry.io", "wixpress", "example.com"))]

    phones = []
    if text:
        for m in PHONE_RE.findall(text):
            cleaned = re.sub(r"[^\d+]", "", m)
            if 8 <= len(cleaned) <= 15:
                phones.append(m.strip())
        phones = sorted(set(phones))[:3]

    socials: dict[str, str] = {}
    if soup:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            for host, key in SOCIAL_HOSTS.items():
                if host in href and key not in socials:
                    socials[key] = href
                    break

    return {
        "emails": emails[:5],
        "phones": phones,
        "social": socials,
    }


def extract_signals(html: str, soup: BeautifulSoup) -> dict[str, Any]:
    text = soup.get_text(" ", strip=True).lower() if soup else ""

    hiring = bool(HIRING_RE.search(text)) if text else False
    founded_match = FOUNDED_RE.search(text) if text else None
    founded_year = int(founded_match.group(3)) if founded_match else None

    return {
        "hiring": hiring,
        "founded_year": founded_year,
        "page_words": len(text.split()) if text else 0,
    }


def enrich(html: str, headers: dict) -> dict[str, Any]:
    """Pure function: turn raw HTML+headers into the enrichment dict."""
    if not html:
        return {
            "title": "",
            "description": "",
            "tech_stack": [],
            "contacts": {"emails": [], "phones": [], "social": {}},
            "signals": {"hiring": False, "founded_year": None, "page_words": 0},
        }

    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")[:200]

    description = ""
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if meta and meta.get("content"):
        description = meta["content"].strip()[:500]

    return {
        "title": title,
        "description": description,
        "tech_stack": detect_tech_stack(html, headers),
        "contacts": extract_contacts(html, soup),
        "signals": extract_signals(html, soup),
    }
