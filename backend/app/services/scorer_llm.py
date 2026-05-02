"""OpenAI-powered scorer.

Returns the same shape as `scorer.score_lead` so the route, the SQL schema,
and the frontend drawer all keep working unchanged. On any failure (no key,
API error, malformed response) returns None so the caller falls back to
the deterministic rule-based scorer.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from . import gemini

# Same signal names as the rule-based scorer so the drawer's progress bars
# render identically. Weights are passed in the prompt as the rubric, not
# enforced post-hoc — let the model choose contributions within each cap.
SIGNAL_WEIGHTS = {
    "industry_match": 30,
    "size_band": 20,
    "tech_relevance": 20,
    "contact_completeness": 15,
    "activity_recency": 15,
}

VALID_SIGNALS = set(SIGNAL_WEIGHTS.keys())
VALID_TIERS = {"A", "B", "C"}


def _build_prompt(lead: dict, enrichment: dict, icp: dict) -> str:
    return f"""You are a B2B sales analyst scoring how well a company fits an Ideal Customer Profile.

ICP (the user's target customer):
- Industry keywords: {icp.get("industry_keywords") or "(none specified)"}
- Target company size: {icp.get("size_min") or 0}-{icp.get("size_max") or 10000} employees
- What we sell: {icp.get("value_prop") or "(not specified)"}

Lead under evaluation:
- Company: {lead.get("company_name", "")}
- Stated industry: {lead.get("industry") or "(unknown)"}
- Employee count: {lead.get("employee_count") or "unknown"}
- Location: {lead.get("location") or "(unknown)"}

Scraped homepage signals:
- Page title: {enrichment.get("title") or "(none)"}
- Description: {enrichment.get("description") or "(none)"}
- Tech stack detected: {", ".join(enrichment.get("tech_stack") or []) or "(none)"}
- Contacts found: {json.dumps(enrichment.get("contacts") or {}, default=str)}
- Activity signals: {json.dumps(enrichment.get("signals") or {}, default=str)}

Score this lead on a 0-100 scale across exactly these 5 signals (with these caps):
- industry_match (max 30): does the company's actual business semantically match the ICP keywords? Consider synonyms (e.g. "software-as-a-service" = "saas").
- size_band (max 20): how well does the employee count fit the target band?
- tech_relevance (max 20): do they use modern growth-tooling (HubSpot, Salesforce, Marketo, Intercom, Drift, Segment, Mixpanel, Amplitude, Pardot)?
- contact_completeness (max 15): emails, phones, LinkedIn presence?
- activity_recency (max 15): hiring page? recent founding year (younger = higher)?

Be conservative — reserve scores of 80+ for leads with strong matches across multiple signals.
Tier: A if total >= 75, B if 50-74, C otherwise.

Return JSON exactly in this shape:
{{
  "score": <number 0-100, sum of contributions>,
  "tier": "A" | "B" | "C",
  "reasons": [
    {{"signal": "industry_match", "weight": 30, "raw": <0.0-1.0>, "contribution": <0-30>, "details": ["specific facts"]}},
    {{"signal": "size_band", "weight": 20, "raw": <0.0-1.0>, "contribution": <0-20>, "details": []}},
    {{"signal": "tech_relevance", "weight": 20, "raw": <0.0-1.0>, "contribution": <0-20>, "details": ["HubSpot", "Segment"]}},
    {{"signal": "contact_completeness", "weight": 15, "raw": <0.0-1.0>, "contribution": <0-15>, "details": ["email", "LinkedIn"]}},
    {{"signal": "activity_recency", "weight": 15, "raw": <0.0-1.0>, "contribution": <0-15>, "details": ["public hiring page"]}}
  ],
  "why": "<one human sentence starting with the company name, naming the strongest 2-3 reasons>"
}}

Include ALL FIVE signals every time, even if contribution is 0. The "details" array should contain short, concrete strings — never sentences.
"""


def _validate_and_normalize(raw: Any) -> Optional[dict]:
    """Defensive parsing — Gemini may return slightly malformed shapes."""
    if not isinstance(raw, dict):
        return None
    try:
        score = float(raw.get("score", 0))
        tier = str(raw.get("tier", "C")).strip().upper()
        if tier not in VALID_TIERS:
            tier = "A" if score >= 75 else ("B" if score >= 50 else "C")

        reasons_in = raw.get("reasons") or []
        reasons: list[dict] = []
        seen_signals: set[str] = set()
        for r in reasons_in:
            if not isinstance(r, dict):
                continue
            signal = str(r.get("signal", "")).strip()
            if signal not in VALID_SIGNALS or signal in seen_signals:
                continue
            seen_signals.add(signal)
            details = r.get("details") or []
            if not isinstance(details, list):
                details = [str(details)]
            reasons.append(
                {
                    "signal": signal,
                    "weight": SIGNAL_WEIGHTS[signal],
                    "raw": round(float(r.get("raw", 0) or 0), 2),
                    "contribution": round(
                        float(r.get("contribution", 0) or 0), 1
                    ),
                    "details": [str(d) for d in details if d is not None],
                }
            )

        # Backfill any signals Gemini omitted, with zero contribution.
        for sig in VALID_SIGNALS - seen_signals:
            reasons.append(
                {
                    "signal": sig,
                    "weight": SIGNAL_WEIGHTS[sig],
                    "raw": 0.0,
                    "contribution": 0.0,
                    "details": [],
                }
            )

        # Stable order matches the rule-based scorer.
        order = ["industry_match", "size_band", "tech_relevance",
                 "contact_completeness", "activity_recency"]
        reasons.sort(key=lambda r: order.index(r["signal"]))

        why = str(raw.get("why") or "").strip()
        if not why:
            why = "Scored by Gemini — see signal breakdown for details."

        return {
            "score": round(score, 1),
            "tier": tier,
            "reasons": reasons,
            "why": why,
        }
    except (TypeError, ValueError):
        return None


def score_lead_llm(lead: dict, enrichment: dict, icp: dict) -> Optional[dict]:
    """Returns the same dict shape as `scorer.score_lead`, or None on failure."""
    if not gemini.is_enabled():
        return None
    prompt = _build_prompt(lead, enrichment, icp)
    raw = gemini.generate_json(prompt, temperature=0.2)
    return _validate_and_normalize(raw)
