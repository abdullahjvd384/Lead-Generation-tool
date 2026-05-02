from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "leadgen_test.db")
    monkeypatch.setenv("LEADGEN_DB", db_path)
    monkeypatch.setenv("GEMINI_API_KEY", "")

    import importlib

    from app import db as db_module
    from app.services import gemini as gemini_module

    importlib.reload(db_module)
    importlib.reload(gemini_module)

    from app import main as main_module

    importlib.reload(main_module)
    db_module.init_db()
    return TestClient(main_module.app), db_module


def _seed_lead(db_module, *, company_name, website, industry, employee_count, location):
    with db_module.get_session() as s:
        lead = db_module.Lead(
            company_name=company_name,
            website=website,
            domain=website.replace("https://", "").replace("http://", "").split("/")[0],
            industry=industry,
            employee_count=employee_count,
            location=location,
        )
        s.add(lead)
        s.commit()
        s.refresh(lead)
        return lead.id


def _add_enrichment_and_score(db_module, lead_id, *, score, tier, contacts=None, tech_stack=None, signals=None, status="ok"):
    with db_module.get_session() as s:
        s.add(
            db_module.Enrichment(
                lead_id=lead_id,
                title="",
                description="",
                tech_stack=tech_stack or [],
                contacts=contacts or {},
                signals=signals or {},
                status=status,
            )
        )
        s.add(
            db_module.Score(
                lead_id=lead_id,
                score=score,
                tier=tier,
                reasons=[],
                why=f"{lead_id} why",
            )
        )
        s.commit()


def test_ranked_leads_orders_by_score_and_confidence(client):
    test_client, db_module = client
    lead_a = _seed_lead(db_module, company_name="Alpha", website="https://alpha.test", industry="SaaS", employee_count=100, location="Austin TX")
    lead_b = _seed_lead(db_module, company_name="Beta", website="https://beta.test", industry="SaaS", employee_count=120, location="Austin TX")
    lead_c = _seed_lead(db_module, company_name="Gamma", website="https://gamma.test", industry="SaaS", employee_count=140, location="Austin TX")

    _add_enrichment_and_score(
        db_module,
        lead_a,
        score=90,
        tier="A",
        contacts={"emails": ["alpha@test.com"], "social": {"linkedin": "https://linkedin.com/company/alpha"}},
        tech_stack=["HubSpot"],
        signals={"hiring": True},
    )
    _add_enrichment_and_score(
        db_module,
        lead_b,
        score=85,
        tier="A",
        contacts={"emails": ["beta@test.com"]},
        tech_stack=["Segment"],
        signals={"hiring": False},
    )
    _add_enrichment_and_score(
        db_module,
        lead_c,
        score=85,
        tier="A",
        contacts={},
        tech_stack=[],
        signals={},
    )

    test_client.put(f"/leads/{lead_b}/stage", json={"stage": "contacted", "reason": "left voicemail", "updated_by": "tester"})

    r = test_client.get("/leads/ranked?limit=3")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 3
    assert [item["company_name"] for item in body["items"]] == ["Alpha", "Beta", "Gamma"]
    assert body["items"][0]["next_step"] == "Call today"
    assert body["items"][1]["stage"] == "contacted"


def test_stage_update_persists_history_and_summary(client):
    test_client, db_module = client
    lead_id = _seed_lead(db_module, company_name="StageCo", website="https://stage.test", industry="SaaS", employee_count=50, location="Remote")

    r = test_client.put(
        f"/leads/{lead_id}/stage",
        json={"stage": "qualified", "reason": "responded positively", "updated_by": "tester"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "qualified"

    history = test_client.get(f"/leads/{lead_id}/stage/history")
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) == 1
    assert rows[0]["from_stage"] == "new"
    assert rows[0]["to_stage"] == "qualified"

    summary = test_client.get("/leads/pipeline")
    assert summary.status_code == 200
    body = summary.json()
    counts = {item["stage"]: item["count"] for item in body["items"]}
    assert counts["qualified"] == 1
    assert body["total"] == 1


def test_lookalikes_rank_most_similar_first(client):
    test_client, db_module = client
    target_id = _seed_lead(db_module, company_name="Target", website="https://target.test", industry="B2B SaaS marketing", employee_count=120, location="Austin TX")
    similar_id = _seed_lead(db_module, company_name="Similar", website="https://similar.test", industry="B2B SaaS marketing", employee_count=110, location="Austin TX")
    different_id = _seed_lead(db_module, company_name="Different", website="https://different.test", industry="manufacturing", employee_count=2000, location="Seattle WA")

    _add_enrichment_and_score(
        db_module,
        target_id,
        score=88,
        tier="A",
        contacts={"emails": ["target@test.com"]},
        tech_stack=["HubSpot", "Segment"],
        signals={"hiring": True},
    )
    _add_enrichment_and_score(
        db_module,
        similar_id,
        score=82,
        tier="A",
        contacts={"emails": ["similar@test.com"]},
        tech_stack=["HubSpot"],
        signals={"hiring": True},
    )
    _add_enrichment_and_score(
        db_module,
        different_id,
        score=20,
        tier="C",
        contacts={},
        tech_stack=[],
        signals={},
    )

    r = test_client.get(f"/leads/{target_id}/lookalikes?limit=2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["seed_lead"]["company_name"] == "Target"
    assert len(body["items"]) == 2
    assert body["items"][0]["lead"]["company_name"] == "Similar"
    assert body["items"][0]["similarity"] >= body["items"][1]["similarity"]
    signals = {reason["signal"] for reason in body["items"][0]["reasons"]}
    assert "industry_similarity" in signals
