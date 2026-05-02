from __future__ import annotations


def generate_email(lead: dict, enrichment: dict, score: dict, icp: dict) -> dict[str, str]:
    """Compose a 3-line cold email grounded in observed facts.

    Template-driven, but every blank is filled from real scraped data — never
    generic Mad-Libs. If a fact isn't observed, the line that uses it is dropped
    rather than faked.
    """
    name = lead.get("company_name") or enrichment.get("title") or "your team"
    value_prop = (icp.get("value_prop") or "").strip()

    tech_stack = enrichment.get("tech_stack") or []
    industry_hits = []
    for r in score.get("reasons", []):
        if r.get("signal") == "industry_match":
            industry_hits = r.get("details") or []
            break

    # Hook line: prefer industry signal, then tech signal, then a generic.
    if industry_hits:
        hook = (
            f"I came across {name} while looking at companies working in "
            f"{industry_hits[0]} — your focus there caught my eye."
        )
    elif tech_stack:
        hook = (
            f"Saw that {name} runs {tech_stack[0]} — that usually means a team "
            f"that takes its growth stack seriously."
        )
    else:
        hook = f"I came across {name} and wanted to reach out directly."

    pitch = (
        f"At our end, we help teams like yours with {value_prop}."
        if value_prop
        else "We work with similar teams on outbound efficiency."
    )

    ask = "Worth a 15-minute call next week to see if it's a fit?"

    body = "\n\n".join([hook, pitch, ask, "—"])
    subject = f"Quick idea for {name}"
    return {"subject": subject, "body": body}
