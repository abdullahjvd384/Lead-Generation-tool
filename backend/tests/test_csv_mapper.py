import pandas as pd
import pytest

from app.services import csv_mapper


def test_alias_dict_handles_salesforce_export(monkeypatch):
    monkeypatch.setattr("app.services.csv_mapper.openai_client.is_enabled", lambda: False)
    df = pd.DataFrame(
        {
            "Account Name": ["Acme", "Beta"],
            "Web URL": ["acme.com", "beta.com"],
            "Headcount": [50, 200],
            "Sector": ["SaaS", "Fintech"],
        }
    )
    out, mapping, source = csv_mapper.normalize_columns(df)
    assert source == "alias"
    assert "company_name" in out.columns
    assert "website" in out.columns
    assert "employee_count" in out.columns
    assert "industry" in out.columns
    assert mapping["Account Name"] == "company_name"
    assert mapping["Web URL"] == "website"


def test_canonical_columns_are_no_op(monkeypatch):
    monkeypatch.setattr("app.services.csv_mapper.openai_client.is_enabled", lambda: False)
    df = pd.DataFrame(
        {
            "company_name": ["Acme"],
            "website": ["acme.com"],
        }
    )
    out, mapping, source = csv_mapper.normalize_columns(df)
    assert source == "exact"
    assert mapping == {}
    assert "company_name" in out.columns


def test_uppercase_and_spaces_normalized(monkeypatch):
    monkeypatch.setattr("app.services.csv_mapper.openai_client.is_enabled", lambda: False)
    df = pd.DataFrame({"COMPANY NAME": ["Acme"], "URL": ["acme.com"]})
    out, mapping, source = csv_mapper.normalize_columns(df)
    assert "company_name" in out.columns
    assert "website" in out.columns
    assert source == "alias"


def test_missing_company_returns_none_source_when_no_OpenAI(monkeypatch):
    monkeypatch.setattr("app.services.csv_mapper.openai_client.is_enabled", lambda: False)
    df = pd.DataFrame({"Notes": ["x"], "Random": ["y"]})
    out, mapping, source = csv_mapper.normalize_columns(df)
    assert source == "none"
    assert "company_name" not in out.columns


def test_openai_fallback_used_when_aliases_fail(monkeypatch):
    monkeypatch.setattr("app.services.csv_mapper.openai_client.is_enabled", lambda: True)

    def fake_openai_json(prompt, **kwargs):
        return {
            "nom_entreprise": "company_name",
            "site_web": "website",
            "Notes": "skip",
        }

    monkeypatch.setattr("app.services.csv_mapper.openai_client.generate_json", fake_openai_json)

    df = pd.DataFrame(
        {
            "nom_entreprise": ["Acme"],
            "site_web": ["acme.com"],
            "Notes": ["whatever"],
        }
    )
    out, mapping, source = csv_mapper.normalize_columns(df)
    assert source == "openai"
    assert "company_name" in out.columns
    assert "website" in out.columns
    assert mapping["nom_entreprise"] == "company_name"


def test_openai_failure_returns_none_source(monkeypatch):
    monkeypatch.setattr("app.services.csv_mapper.openai_client.is_enabled", lambda: True)
    monkeypatch.setattr(
        "app.services.csv_mapper.openai_client.generate_json", lambda *a, **k: None
    )

    df = pd.DataFrame({"weird": ["x"]})
    _, _, source = csv_mapper.normalize_columns(df)
    assert source == "none"


def test_duplicate_targets_are_collapsed(monkeypatch):
    monkeypatch.setattr("app.services.csv_mapper.openai_client.is_enabled", lambda: False)
    # Two columns both alias to company_name — keep first, ignore second.
    df = pd.DataFrame({"Account Name": ["Acme"], "Business Name": ["Beta"]})
    out, _, _ = csv_mapper.normalize_columns(df)
    assert list(out.columns).count("company_name") == 1
