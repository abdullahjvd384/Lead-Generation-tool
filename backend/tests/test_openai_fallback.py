"""Verify that with no OPENAI_API_KEY set, every OpenAI-powered code path
falls back cleanly to the rule-based logic.
"""
from app.services import openai_client, outreach_llm, scorer_llm


def test_openai_disabled_when_no_key(monkeypatch):
    monkeypatch.setattr("app.services.openai_client._ENABLED", False)
    assert openai_client.is_enabled() is False


def test_scorer_llm_returns_none_without_key(monkeypatch):
    monkeypatch.setattr("app.services.scorer_llm.openai_client.is_enabled", lambda: False)
    out = scorer_llm.score_lead_llm({}, {}, {})
    assert out is None


def test_outreach_llm_returns_none_without_key(monkeypatch):
    monkeypatch.setattr("app.services.outreach_llm.openai_client.is_enabled", lambda: False)
    out = outreach_llm.generate_email_llm({}, {}, {}, {})
    assert out is None


def test_scorer_llm_validation_handles_garbage(monkeypatch):
    monkeypatch.setattr("app.services.scorer_llm.openai_client.is_enabled", lambda: True)
    monkeypatch.setattr(
        "app.services.scorer_llm.openai_client.generate_json", lambda *a, **k: "not a dict"
    )
    assert scorer_llm.score_lead_llm({}, {}, {}) is None


def test_scorer_llm_backfills_missing_signals(monkeypatch):
    monkeypatch.setattr("app.services.scorer_llm.openai_client.is_enabled", lambda: True)

    def partial_response(*a, **k):
        return {
            "score": 60,
            "tier": "B",
            "reasons": [
                {
                    "signal": "industry_match",
                    "weight": 30,
                    "raw": 1.0,
                    "contribution": 30,
                    "details": ["saas"],
                }
            ],
            "why": "Strong industry match.",
        }

    monkeypatch.setattr("app.services.scorer_llm.openai_client.generate_json", partial_response)
    out = scorer_llm.score_lead_llm({"company_name": "X"}, {}, {})
    assert out is not None
    # All 5 signals must be present even if the model omits some.
    signals = {r["signal"] for r in out["reasons"]}
    assert signals == {
        "industry_match",
        "size_band",
        "tech_relevance",
        "contact_completeness",
        "activity_recency",
    }
