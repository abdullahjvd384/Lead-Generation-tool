from __future__ import annotations

from typing import Any


ACTION_PRIORITIZE = "Prioritize"
ACTION_RESEARCH = "Research"
ACTION_NURTURE = "Nurture"
ACTION_DISQUALIFY = "Disqualify"
ACTION_SCORE_FIRST = "Score first"


def _reason_by_signal(reasons: list[dict[str, Any]], signal: str) -> dict[str, Any]:
    for reason in reasons or []:
        if reason.get("signal") == signal:
            return reason
    return {}


def _contact_channels(contacts: dict[str, Any]) -> list[str]:
    channels: list[str] = []
    if contacts.get("emails"):
        channels.append("email")
    if contacts.get("phones"):
        channels.append("phone")
    social = contacts.get("social") or {}
    if social.get("linkedin"):
        channels.append("linkedin")
    return channels


def assess_lead_quality(
    lead: dict[str, Any],
    enrichment: dict[str, Any],
    score: dict[str, Any] | None,
    icp: dict[str, Any],
) -> dict[str, Any]:
    """Translate scoring data into a sales-ready action and risk profile.

    The score ranks fit; this assessment answers the next operational question:
    whether sales should act now, research gaps, nurture, or remove the lead.
    """
    score = score or {}
    contacts = enrichment.get("contacts") or {}
    reasons = score.get("reasons") or []
    status = enrichment.get("status")
    channels = _contact_channels(contacts)

    missing_data: list[str] = []
    if not lead.get("website"):
        missing_data.append("website")
    if not lead.get("industry"):
        missing_data.append("industry")
    if not int(lead.get("employee_count") or 0):
        missing_data.append("employee count")
    if not channels:
        missing_data.append("contact channel")

    confidence = 0
    if lead.get("company_name"):
        confidence += 15
    if lead.get("website") or lead.get("domain"):
        confidence += 15
    if lead.get("industry"):
        confidence += 15
    if int(lead.get("employee_count") or 0) > 0:
        confidence += 15
    if score.get("score") is not None:
        confidence += 20
    if status == "ok":
        confidence += 10
    elif status == "error":
        confidence -= 10
    if channels:
        confidence += min(10, len(channels) * 5)
    confidence = max(0, min(100, confidence))

    risk_flags: list[str] = []
    if status == "error":
        risk_flags.append("site unreachable")
    if "website" in missing_data:
        risk_flags.append("no website")
    if "contact channel" in missing_data:
        risk_flags.append("no contact channel")

    industry_reason = _reason_by_signal(reasons, "industry_match")
    if industry_reason and float(industry_reason.get("raw") or 0) < 0.4:
        risk_flags.append("weak ICP keyword match")

    size_reason = _reason_by_signal(reasons, "size_band")
    employees = int(lead.get("employee_count") or 0)
    if employees and size_reason and float(size_reason.get("raw") or 0) < 0.5:
        low = int(icp.get("size_min") or 0)
        high = int(icp.get("size_max") or 10000)
        risk_flags.append(f"outside size band ({low}-{high})")

    if confidence < 55:
        risk_flags.append("low data confidence")

    tier = score.get("tier")
    numeric_score = score.get("score")
    if numeric_score is None:
        action = ACTION_SCORE_FIRST
    elif tier == "A" and confidence >= 65 and channels:
        action = ACTION_PRIORITIZE
    elif tier in {"A", "B"} and (confidence < 65 or not channels):
        action = ACTION_RESEARCH
    elif tier == "B":
        action = ACTION_NURTURE
    elif confidence < 50 and float(numeric_score) >= 40:
        action = ACTION_RESEARCH
    else:
        action = ACTION_DISQUALIFY

    if action == ACTION_PRIORITIZE:
        summary = "Ready for sales outreach."
    elif action == ACTION_RESEARCH:
        summary = "Promising, but fix data gaps before spending outreach time."
    elif action == ACTION_NURTURE:
        summary = "Good enough to keep warm, not the next call."
    elif action == ACTION_SCORE_FIRST:
        summary = "Score this lead to decide fit."
    else:
        summary = "Low-fit lead; exclude from near-term outreach."

    return {
        "recommended_action": action,
        "confidence": confidence,
        "risk_flags": risk_flags,
        "missing_data": missing_data,
        "contact_channels": channels,
        "summary": summary,
    }
