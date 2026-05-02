from __future__ import annotations

from datetime import datetime
from typing import Any

# Weights sum to 100. Tunable in one place.
WEIGHTS = {
    "industry_match": 30,
    "size_band": 20,
    "tech_relevance": 20,
    "contact_completeness": 15,
    "activity_recency": 15,
}

TIER_THRESHOLDS = [(75, "A"), (50, "B"), (0, "C")]

# Tech stacks that suggest the company actively invests in growth/sales tooling
# and is therefore more likely to engage with outbound.
GROWTH_STACK = {
    "HubSpot",
    "Salesforce",
    "Marketo",
    "Pardot",
    "Intercom",
    "Drift",
    "Segment",
    "Mixpanel",
    "Amplitude",
}


def _split_keywords(s: str) -> list[str]:
    return [k.strip().lower() for k in (s or "").replace("\n", ",").split(",") if k.strip()]


def _industry_match_score(lead_text: str, keywords: list[str]) -> tuple[float, list[str]]:
    if not keywords:
        return 0.5, []  # neutral if user gave us no ICP keywords
    hay = lead_text.lower()
    hits = [k for k in keywords if k in hay]
    if not hits:
        return 0.0, []
    # Saturating: 1 hit = 0.6, 2 = 0.85, 3+ = 1.0.
    raw = min(1.0, 0.6 + 0.25 * (len(hits) - 1))
    return raw, hits


def _size_band_score(employees: int, size_min: int, size_max: int) -> float:
    if employees <= 0:
        return 0.4  # unknown — partial credit, not zero, so leads with no size data still rank
    if size_min <= employees <= size_max:
        return 1.0
    # Soft fall-off: 50% credit within 2x of the band edges.
    if employees < size_min:
        ratio = employees / max(size_min, 1)
        return max(0.0, 0.5 * ratio)
    # employees > size_max
    ratio = size_max / max(employees, 1)
    return max(0.0, 0.5 * ratio)


def _tech_relevance_score(tech_stack: list[str]) -> tuple[float, list[str]]:
    if not tech_stack:
        return 0.0, []
    relevant = [t for t in tech_stack if t in GROWTH_STACK]
    if not relevant:
        # Some tech detected but not growth-relevant — small credit for being a real, modern site.
        return 0.25, []
    raw = min(1.0, 0.5 + 0.25 * len(relevant))
    return raw, relevant


def _contact_completeness_score(contacts: dict) -> tuple[float, list[str]]:
    found: list[str] = []
    score = 0.0
    if contacts.get("emails"):
        score += 0.5
        found.append("email")
    if contacts.get("phones"):
        score += 0.25
        found.append("phone")
    socials = contacts.get("social", {}) or {}
    if "linkedin" in socials:
        score += 0.25
        found.append("LinkedIn")
    return min(score, 1.0), found


def _activity_recency_score(signals: dict) -> tuple[float, list[str]]:
    notes: list[str] = []
    score = 0.0
    if signals.get("hiring"):
        score += 0.6
        notes.append("public hiring page")
    fy = signals.get("founded_year")
    if isinstance(fy, int):
        age = datetime.utcnow().year - fy
        if 1 <= age <= 15:
            score += 0.4
            notes.append(f"founded {fy}")
        elif age <= 30:
            score += 0.2
    return min(score, 1.0), notes


def score_lead(lead: dict, enrichment: dict, icp: dict) -> dict[str, Any]:
    """Return {score (0-100), tier, reasons, why}.

    Pure function — easy to unit test.
    `lead` keys: company_name, industry, employee_count, location.
    `enrichment` keys: title, description, tech_stack, contacts, signals.
    `icp` keys: industry_keywords, size_min, size_max, value_prop.
    """
    keywords = _split_keywords(icp.get("industry_keywords", ""))
    lead_text = " ".join(
        str(x)
        for x in [
            lead.get("company_name", ""),
            lead.get("industry", ""),
            enrichment.get("title", ""),
            enrichment.get("description", ""),
        ]
    )

    ind_raw, ind_hits = _industry_match_score(lead_text, keywords)
    size_raw = _size_band_score(
        int(lead.get("employee_count") or 0),
        int(icp.get("size_min") or 0),
        int(icp.get("size_max") or 10000),
    )
    tech_raw, tech_hits = _tech_relevance_score(enrichment.get("tech_stack") or [])
    contact_raw, contact_found = _contact_completeness_score(enrichment.get("contacts") or {})
    activity_raw, activity_notes = _activity_recency_score(enrichment.get("signals") or {})

    weights = _normalized_weights(icp.get("weights") or WEIGHTS)

    contributions = [
        ("industry_match", ind_raw, weights["industry_match"], ind_hits),
        ("size_band", size_raw, weights["size_band"], []),
        ("tech_relevance", tech_raw, weights["tech_relevance"], tech_hits),
        ("contact_completeness", contact_raw, weights["contact_completeness"], contact_found),
        ("activity_recency", activity_raw, weights["activity_recency"], activity_notes),
    ]

    reasons = [
        {
            "signal": name,
            "weight": weight,
            "raw": round(raw, 2),
            "contribution": round(raw * weight, 1),
            "details": details,
        }
        for name, raw, weight, details in contributions
    ]

    score = round(sum(r["contribution"] for r in reasons), 1)
    tier = next(t for thresh, t in TIER_THRESHOLDS if score >= thresh)
    why = build_why(reasons, lead, enrichment)
    return {"score": score, "tier": tier, "reasons": reasons, "why": why}


def _normalized_weights(raw_weights: dict[str, Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for signal, default in WEIGHTS.items():
        try:
            weights[signal] = max(0.0, float(raw_weights.get(signal, default)))
        except (TypeError, ValueError, AttributeError):
            weights[signal] = float(default)
    total = sum(weights.values())
    if total <= 0:
        return {signal: float(weight) for signal, weight in WEIGHTS.items()}
    return {signal: round((weight / total) * 100, 4) for signal, weight in weights.items()}


def build_why(reasons: list[dict], lead: dict, enrichment: dict) -> str:
    """Humanize the top contributors into a one-sentence rationale."""
    top = sorted(reasons, key=lambda r: r["contribution"], reverse=True)
    parts: list[str] = []

    for r in top:
        if r["contribution"] < 5:
            continue
        details = r["details"]
        if r["signal"] == "industry_match" and details:
            parts.append(f"matches your ICP keywords ({', '.join(details[:3])})")
        elif r["signal"] == "size_band" and r["raw"] >= 0.9:
            parts.append("sits inside your target size band")
        elif r["signal"] == "tech_relevance" and details:
            parts.append(f"runs growth tooling ({', '.join(details[:2])})")
        elif r["signal"] == "contact_completeness" and details:
            parts.append(f"has reachable contacts ({', '.join(details)})")
        elif r["signal"] == "activity_recency" and details:
            parts.append(", ".join(details))
        if len(parts) >= 3:
            break

    if not parts:
        return "Limited ICP signal — review manually before outreach."

    name = lead.get("company_name") or enrichment.get("title") or "This lead"
    return f"{name}: " + "; ".join(parts) + "."
