from app.services.quality import assess_lead_quality


ICP = {"size_min": 50, "size_max": 500}


def test_a_tier_contactable_lead_is_prioritized():
    quality = assess_lead_quality(
        {
            "company_name": "Acme",
            "website": "https://acme.com",
            "domain": "acme.com",
            "industry": "B2B SaaS",
            "employee_count": 120,
        },
        {
            "status": "ok",
            "contacts": {
                "emails": ["hello@acme.com"],
                "social": {"linkedin": "https://linkedin.com/company/acme"},
            },
        },
        {
            "score": 82,
            "tier": "A",
            "reasons": [
                {"signal": "industry_match", "raw": 1.0},
                {"signal": "size_band", "raw": 1.0},
            ],
        },
        ICP,
    )

    assert quality["recommended_action"] == "Prioritize"
    assert quality["confidence"] >= 80
    assert "email" in quality["contact_channels"]


def test_good_fit_without_contact_channel_needs_research():
    quality = assess_lead_quality(
        {
            "company_name": "Beta",
            "website": "https://beta.com",
            "domain": "beta.com",
            "industry": "B2B SaaS",
            "employee_count": 80,
        },
        {"status": "ok", "contacts": {}},
        {
            "score": 76,
            "tier": "A",
            "reasons": [{"signal": "industry_match", "raw": 1.0}],
        },
        ICP,
    )

    assert quality["recommended_action"] == "Research"
    assert "no contact channel" in quality["risk_flags"]


def test_unscored_lead_gets_score_first_action():
    quality = assess_lead_quality(
        {"company_name": "Gamma", "website": "", "domain": "", "industry": "", "employee_count": 0},
        {"status": None, "contacts": {}},
        None,
        ICP,
    )

    assert quality["recommended_action"] == "Score first"
    assert "website" in quality["missing_data"]
