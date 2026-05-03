from __future__ import annotations

from typing import Any


ACTION_ORDER = {
    "Prioritize": 0,
    "Research": 1,
    "Nurture": 2,
    "Disqualify": 3,
    "Score first": 4,
}

STAGE_ORDER = {
    "new": 0,
    "contacted": 1,
    "qualified": 2,
    "dead": 3,
}


def _stage_name(stage: str | None) -> str:
    value = (stage or "new").strip().lower()
    return value if value in STAGE_ORDER else "new"


def rank_leads(leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> tuple:
        quality = item.get("quality") or {}
        stage = _stage_name(item.get("stage"))
        score = float(item.get("score") or -1)
        confidence = float(quality.get("confidence") or 0)
        action = quality.get("recommended_action") or "Score first"
        return (
            -score,
            -confidence,
            ACTION_ORDER.get(action, 99),
            STAGE_ORDER[stage],
            item.get("id") or 0,
        )

    ordered = sorted(leads, key=sort_key)
    ranked: list[dict[str, Any]] = []
    for index, lead in enumerate(ordered, start=1):
        quality = lead.get("quality") or {}
        stage = _stage_name(lead.get("stage"))
        ranked.append(
            {
                **lead,
                "stage": stage,
                "rank": index,
                "rank_reason": quality.get("summary")
                or lead.get("why")
                or "Ranked by score and workflow readiness.",
                "next_step": _next_step(quality.get("recommended_action"), stage),
            }
        )
    return ranked


def _next_step(action: str | None, stage: str) -> str:
    action = action or "Score first"
    if stage == "dead":
        return "Do not pursue"
    if action == "Prioritize":
        return "Call today"
    if action == "Research":
        return "Verify missing details"
    if action == "Nurture":
        return "Add to follow-up cadence"
    if action == "Disqualify":
        return "Archive or suppress"
    return "Score before outreach"


def _tokenize(text: str) -> set[str]:
    import re

    return {part for part in re.split(r"[^a-z0-9]+", (text or "").lower()) if part}


def _industry_similarity(target: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, list[str]]:
    target_text = " ".join(
        str(x)
        for x in [
            target.get("industry", ""),
            target.get("company_name", ""),
            target.get("description", ""),
        ]
    )
    candidate_text = " ".join(
        str(x)
        for x in [
            candidate.get("industry", ""),
            candidate.get("company_name", ""),
            candidate.get("description", ""),
        ]
    )
    target_tokens = _tokenize(target_text)
    candidate_tokens = _tokenize(candidate_text)
    common = sorted(target_tokens & candidate_tokens)
    if not common:
        return 0.0, []
    return min(1.0, 0.55 + 0.15 * (len(common) - 1)), common[:4]


def _size_similarity(target: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, list[str]]:
    try:
        target_size = int(target.get("employee_count") or 0)
    except (ValueError, TypeError):
        target_size = 0
    try:
        candidate_size = int(candidate.get("employee_count") or 0)
    except (ValueError, TypeError):
        candidate_size = 0
    if target_size <= 0 or candidate_size <= 0:
        return 0.25, ["size missing"]
    ratio = min(target_size, candidate_size) / max(target_size, candidate_size)
    if ratio >= 0.9:
        return 1.0, ["similar size"]
    if ratio >= 0.7:
        return 0.75, [f"{candidate_size} employees"]
    if ratio >= 0.5:
        return 0.5, [f"{candidate_size} employees"]
    return 0.2, [f"{candidate_size} employees"]


def _location_similarity(target: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, list[str]]:
    target_loc = (target.get("location") or "").strip().lower()
    candidate_loc = (candidate.get("location") or "").strip().lower()
    if not target_loc or not candidate_loc:
        return 0.0, []
    if target_loc == candidate_loc:
        return 1.0, [candidate.get("location") or ""]
    target_tail = target_loc.split()[-1]
    candidate_tail = candidate_loc.split()[-1]
    if target_tail and target_tail == candidate_tail:
        return 0.6, [candidate.get("location") or ""]
    return 0.0, []


def _tech_similarity(target: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, list[str]]:
    target_tech = {str(x).lower() for x in (target.get("tech_stack") or [])}
    candidate_tech = {str(x).lower() for x in (candidate.get("tech_stack") or [])}
    overlap = sorted(target_tech & candidate_tech)
    if not overlap:
        return 0.0, []
    return min(1.0, 0.4 + 0.2 * len(overlap)), overlap[:4]


def _score_similarity(target: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, list[str]]:
    target_score = float(target.get("score") or 0)
    candidate_score = float(candidate.get("score") or 0)
    if target_score <= 0 or candidate_score <= 0:
        return 0.0, []
    diff = abs(target_score - candidate_score)
    if diff <= 5:
        return 1.0, ["score near target"]
    if diff <= 15:
        return 0.7, [f"score within {diff:.0f} points"]
    if diff <= 30:
        return 0.4, [f"score within {diff:.0f} points"]
    return 0.1, [f"score differs by {diff:.0f} points"]


def lookalike_matches(seed: dict[str, Any], candidates: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    weighted = [
        ("industry_similarity", 35, _industry_similarity),
        ("size_similarity", 20, _size_similarity),
        ("location_similarity", 10, _location_similarity),
        ("tech_overlap", 20, _tech_similarity),
        ("score_alignment", 15, _score_similarity),
    ]

    results: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("id") == seed.get("id"):
            continue
        reasons: list[dict[str, Any]] = []
        total = 0.0
        for signal, weight, fn in weighted:
            raw, details = fn(seed, candidate)
            contribution = round(weight * raw, 1)
            total += contribution
            reasons.append(
                {
                    "signal": signal,
                    "weight": weight,
                    "raw": round(raw, 2),
                    "contribution": contribution,
                    "details": details,
                }
            )
        results.append({"lead": candidate, "similarity": round(total, 1), "reasons": reasons})

    results.sort(key=lambda item: (-item["similarity"], item["lead"].get("id") or 0))
    return results[: max(0, limit)]
