"""Normalize CSV column headers to the canonical names the rest of the
backend expects.

Two passes:
1. Alias dictionary (free, instant) — handles ~90% of real CSVs from
   Salesforce, HubSpot, Apollo, ZoomInfo, etc.
2. OpenAI fallback — if `company_name` is still missing after pass 1 and
   OPENAI_API_KEY is set, ask OpenAI to map the unrecognized headers.

Returns the renamed DataFrame plus a `mapping_used` dict so the UI can show
the user which columns got remapped and how.
"""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from . import gemini

CANONICAL = ["company_name", "website", "industry", "employee_count", "location"]

ALIASES: dict[str, list[str]] = {
    "company_name": [
        "company", "name", "business_name", "business",
        "account_name", "account", "organization", "org",
        "firm", "firm_name", "company_title", "client", "client_name",
    ],
    "website": [
        "url", "domain", "web", "homepage", "site",
        "company_website", "web_url", "website_url",
    ],
    "industry": [
        "sector", "vertical", "category", "business_type", "segment",
    ],
    "employee_count": [
        "employees", "size", "headcount", "staff",
        "num_employees", "company_size", "team_size", "no_of_employees",
    ],
    "location": [
        "city", "country", "address", "hq", "headquarters",
        "region", "based_in", "company_location",
    ],
}

# Pre-build reverse lookup once at import time.
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in ALIASES.items():
    _ALIAS_TO_CANONICAL[canonical] = canonical  # the canonical name maps to itself
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias] = canonical


def _normalize_header(raw: str) -> str:
    return str(raw).strip().lower().replace(" ", "_").replace("-", "_")


def apply_alias_mapping(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Pass 1 — rename columns whose normalized name is in the alias dict.

    Returns (renamed_df, mapping_used) where mapping_used only includes
    columns that actually changed name (so the UI doesn't show no-ops).
    """
    rename: dict[str, str] = {}
    mapping_used: dict[str, str] = {}
    seen_targets: set[str] = set()

    for original in df.columns:
        normalized = _normalize_header(original)
        canonical = _ALIAS_TO_CANONICAL.get(normalized)
        if canonical is None:
            # Leave unrecognized columns alone — Gemini may handle them later.
            continue
        if canonical in seen_targets:
            # Two columns mapped to the same canonical name — keep the first.
            continue
        seen_targets.add(canonical)
        rename[original] = canonical
        if normalized != canonical:
            mapping_used[str(original)] = canonical

    if rename:
        df = df.rename(columns=rename)
    return df, mapping_used


def _openai_map(headers: list[str], sample_rows: list[dict]) -> dict[str, str]:
    """Pass 2 — ask OpenAI to map unrecognized headers to canonical names.

    Returns {original_header: canonical_name} for headers OpenAI could match.
    Empty dict on any failure.
    """
    prompt = f"""You are mapping CSV columns to a canonical schema for a sales lead tool.

Canonical fields (and what they mean):
- company_name: name of the company / business / account / organization
- website: company's website URL or domain
- industry: industry, sector, vertical, or business category
- employee_count: number of employees / headcount / company size
- location: city, country, region, headquarters, or address

Here are the CSV columns and 3 sample rows:

Columns: {json.dumps(headers)}

Sample rows:
{json.dumps(sample_rows, indent=2, default=str)}

For each column, decide which canonical field it maps to, or "skip" if it
doesn't match any. Return JSON exactly like:
{{
  "Account Name": "company_name",
  "Web URL": "website",
  "Notes": "skip"
}}

Include EVERY column from the input. Only use the canonical field names listed
above (or "skip"). Each canonical field should appear at most once.
"""
    result = gemini.generate_json(prompt, temperature=0.0)
    if not isinstance(result, dict):
        return {}

    valid_targets = set(CANONICAL) | {"skip"}
    seen_targets: set[str] = set()
    mapping: dict[str, str] = {}
    for original, target in result.items():
        if not isinstance(target, str) or target not in valid_targets:
            continue
        if target == "skip":
            continue
        if target in seen_targets:
            continue
        seen_targets.add(target)
        mapping[original] = target
    return mapping


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str], str]:
    """Run alias pass, then OpenAI fallback if company_name is still missing.

    Returns (df, mapping_used, source) where source is one of:
        "exact"  — no remapping was needed
        "alias"  — alias dictionary did the work
        "openai" — OpenAI fallback was used
        "none"   — nothing matched (caller should return a 400)
    """
    df, alias_mapping = apply_alias_mapping(df)

    if "company_name" in df.columns:
        source = "alias" if alias_mapping else "exact"
        return df, alias_mapping, source

    # Pass 2 — only runs if alias dict couldn't find company_name.
    if not gemini.is_enabled():
        return df, alias_mapping, "none"

    sample_rows: list[dict[str, Any]] = df.head(3).to_dict(orient="records")
    headers = [str(c) for c in df.columns]
    openai_mapping = _openai_map(headers, sample_rows)

    if not openai_mapping:
        return df, alias_mapping, "none"

    df = df.rename(columns=openai_mapping)
    combined = {**alias_mapping, **openai_mapping}

    if "company_name" not in df.columns:
        return df, combined, "none"

    return df, combined, "openai"
