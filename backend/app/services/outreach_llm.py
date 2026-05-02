"""OpenAI-powered cold email writer.

Returns the same {subject, body} shape as `outreach.generate_email`. On any
failure returns None and the caller falls back to the deterministic template.
"""
from __future__ import annotations

from typing import Optional

from . import openai_client


def _build_prompt(lead: dict, enrichment: dict, score: dict, icp: dict) -> str:
    name = lead.get("company_name") or enrichment.get("title") or "the company"
    industry = lead.get("industry") or "(not stated)"
    tech = enrichment.get("tech_stack") or []
    signals = enrichment.get("signals") or {}
    why = score.get("why") or "(no scoring rationale available)"
    value_prop = icp.get("value_prop") or "(unspecified)"
    tone = icp.get("tone") or "direct"

    facts: list[str] = []
    if industry and industry != "(not stated)":
        facts.append(f"Industry: {industry}")
    if tech:
        facts.append(f"Tech stack detected: {', '.join(tech[:5])}")
    if signals.get("hiring"):
        facts.append("Has a public hiring page")
    if signals.get("founded_year"):
        facts.append(f"Founded {signals['founded_year']}")
    facts_block = "\n".join(f"- {f}" for f in facts) if facts else "- (no enrichment signals)"

    return f"""Write a personalized 3-line cold email to a sales prospect. Keep it
short, human, and specific — NOT templated. Mention 1-2 concrete facts about
the prospect (their tech stack, their hiring status, their industry, etc.).
Soft ask for a 15-minute call. Sign off with "—".

Prospect: {name}
What we know about them:
{facts_block}

Why they're a good fit for us: {why}

What we sell: {value_prop}
Tone: {tone}

Return JSON exactly in this shape:
{{
  "subject": "<6-10 word subject line that doesn't sound like spam>",
  "body": "<3 short paragraphs separated by a blank line. First paragraph references something specific you noticed about them. Second paragraph one sentence on what we do, in plain English. Third paragraph the soft ask. End with a blank line and \\"—\\" on its own line.>"
}}

Rules:
- Never use phrases like "hope you're well", "I came across your company", "as a leader in".
- Don't start with "I" — start with something about THEM.
- If tone is "executive", sound boardroom concise. If "warm", sound conversational. If "direct", be crisp and practical.
- Body must be under 80 words.
- Don't make up facts not given above.
"""


def generate_email_llm(
    lead: dict, enrichment: dict, score: dict, icp: dict
) -> Optional[dict]:
    if not openai_client.is_enabled():
        return None
    prompt = _build_prompt(lead, enrichment, score, icp)
    raw = openai_client.generate_json(prompt, temperature=0.7)
    if not isinstance(raw, dict):
        return None

    subject = str(raw.get("subject") or "").strip()
    body = str(raw.get("body") or "").strip()
    if not subject or not body:
        return None

    return {"subject": subject, "body": body}
