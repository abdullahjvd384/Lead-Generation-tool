"""Verifies the `only_unscored` filter on POST /score: when set, the route
should only process leads that don't yet have a row in the scores table.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Fresh app + temp SQLite per test, so we can seed leads + scores cleanly."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "leadgen_test.db")
    monkeypatch.setenv("LEADGEN_DB", db_path)
    # Force rule-based path so tests don't depend on a Gemini key.
    monkeypatch.setenv("GEMINI_API_KEY", "")

    # Re-import everything fresh under the patched env.
    import importlib

    from app import db as db_module
    from app.services import gemini as gemini_module

    importlib.reload(db_module)
    importlib.reload(gemini_module)

    from app import main as main_module
    importlib.reload(main_module)

    db_module.init_db()
    return TestClient(main_module.app)


def _seed_three_leads(client):
    """Insert three leads via the upload endpoint."""
    csv = b"company_name,website\nAlpha,alpha.test\nBravo,bravo.test\nCharlie,charlie.test\n"
    r = client.post(
        "/leads/upload",
        files={"file": ("leads.csv", csv, "text/csv")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["inserted"] == 3


def test_only_unscored_skips_already_scored_leads(client, monkeypatch):
    # Stub out the network: scraper returns empty html for every domain so the
    # test is fast and offline.
    async def fake_fetch(session, domain, *, client=None):
        return "", {}, "ok"

    monkeypatch.setattr("app.routes.score.fetch_homepage", fake_fetch)

    _seed_three_leads(client)

    # First run scores all three.
    r = client.post("/score")
    assert r.status_code == 200
    assert r.json()["scored"] + r.json()["cached"] + r.json()["failed"] == 3

    # Add a fourth lead; only_unscored=true should process exactly one.
    csv = b"company_name,website\nDelta,delta.test\n"
    client.post("/leads/upload", files={"file": ("more.csv", csv, "text/csv")})

    r = client.post("/score?only_unscored=true")
    assert r.status_code == 200
    body = r.json()
    total_processed = body["scored"] + body["cached"] + body["failed"]
    assert total_processed == 1, f"expected 1 processed, got {total_processed}: {body}"


def test_only_unscored_with_nothing_new_is_a_noop(client, monkeypatch):
    async def fake_fetch(session, domain, *, client=None):
        return "", {}, "ok"

    monkeypatch.setattr("app.routes.score.fetch_homepage", fake_fetch)

    _seed_three_leads(client)
    client.post("/score")  # all scored

    r = client.post("/score?only_unscored=true")
    assert r.status_code == 200
    assert r.json() == {"scored": 0, "cached": 0, "failed": 0}


def test_default_still_rescores_all(client, monkeypatch):
    async def fake_fetch(session, domain, *, client=None):
        return "", {}, "ok"

    monkeypatch.setattr("app.routes.score.fetch_homepage", fake_fetch)

    _seed_three_leads(client)
    client.post("/score")  # all scored

    r = client.post("/score")  # no flag → rescore everything
    assert r.status_code == 200
    body = r.json()
    assert body["scored"] + body["cached"] + body["failed"] == 3
