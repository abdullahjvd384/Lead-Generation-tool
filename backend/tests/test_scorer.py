from app.services.scorer import TIER_THRESHOLDS, score_lead

ICP = {
    "industry_keywords": "saas, marketing, b2b",
    "size_min": 50,
    "size_max": 500,
    "value_prop": "AI-powered lead enrichment for B2B sales teams",
}

STRONG_LEAD = {
    "company_name": "Acme",
    "industry": "B2B SaaS marketing",
    "employee_count": 200,
    "location": "Berlin",
}
STRONG_ENRICH = {
    "title": "Acme — B2B Marketing Automation",
    "description": "Acme helps SaaS companies grow.",
    "tech_stack": ["HubSpot", "Segment"],
    "contacts": {
        "emails": ["hello@acme.com"],
        "phones": ["+1 415 555 0142"],
        "social": {"linkedin": "https://linkedin.com/company/acme"},
    },
    "signals": {"hiring": True, "founded_year": 2015},
}


def test_strong_lead_is_a_tier():
    r = score_lead(STRONG_LEAD, STRONG_ENRICH, ICP)
    assert r["tier"] == "A"
    assert r["score"] >= 75
    assert r["why"] and "Acme" in r["why"]


def test_score_is_zero_to_hundred():
    r = score_lead(STRONG_LEAD, STRONG_ENRICH, ICP)
    assert 0 <= r["score"] <= 100


def test_weak_lead_is_c_tier():
    weak_lead = {"company_name": "Weak", "industry": "fishing supplies", "employee_count": 5}
    weak_enrich = {
        "title": "",
        "description": "",
        "tech_stack": [],
        "contacts": {},
        "signals": {"hiring": False, "founded_year": None},
    }
    r = score_lead(weak_lead, weak_enrich, ICP)
    assert r["tier"] == "C"
    assert r["score"] < 50


def test_unknown_size_does_not_zero_out():
    """An empty website still scores on industry match alone."""
    lead = {"company_name": "Acme", "industry": "B2B SaaS marketing", "employee_count": 0}
    enrich = {
        "title": "",
        "description": "",
        "tech_stack": [],
        "contacts": {},
        "signals": {},
    }
    r = score_lead(lead, enrich, ICP)
    # industry match (30 * 1.0) + size partial (20 * 0.4) = 38
    assert r["score"] >= 30


def test_reasons_contain_all_signals():
    r = score_lead(STRONG_LEAD, STRONG_ENRICH, ICP)
    signals = {row["signal"] for row in r["reasons"]}
    assert signals == {
        "industry_match",
        "size_band",
        "tech_relevance",
        "contact_completeness",
        "activity_recency",
    }


def test_tier_thresholds_monotonic():
    thresholds = [t for t, _ in TIER_THRESHOLDS]
    assert thresholds == sorted(thresholds, reverse=True)
