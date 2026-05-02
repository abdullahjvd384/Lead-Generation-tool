from app.services.enricher import enrich

SAMPLE = """
<html>
<head>
  <title>Acme — Marketing Automation for SaaS</title>
  <meta name="description" content="Acme helps B2B SaaS teams run outbound at scale." />
</head>
<body>
  <p>We're hiring engineers in Berlin. Founded in 2014.</p>
  <a href="https://www.linkedin.com/company/acme">LinkedIn</a>
  <a href="mailto:hello@acme.com">Email us</a>
  <p>Call us at +1 (415) 555-0142.</p>
  <script src="https://js.hubspot.com/hs-scripts/123.js"></script>
  <script src="https://cdn.segment.com/analytics.js"></script>
</body>
</html>
"""


def test_enrich_extracts_title_and_description():
    r = enrich(SAMPLE, {})
    assert "Acme" in r["title"]
    assert "B2B" in r["description"]


def test_enrich_detects_tech_stack():
    r = enrich(SAMPLE, {})
    assert "HubSpot" in r["tech_stack"]
    assert "Segment" in r["tech_stack"]


def test_enrich_extracts_contacts():
    r = enrich(SAMPLE, {})
    assert "hello@acme.com" in r["contacts"]["emails"]
    assert "linkedin" in r["contacts"]["social"]
    assert any("415" in p for p in r["contacts"]["phones"])


def test_enrich_signals_hiring_and_founded():
    r = enrich(SAMPLE, {})
    assert r["signals"]["hiring"] is True
    assert r["signals"]["founded_year"] == 2014


def test_enrich_empty_html():
    r = enrich("", {})
    assert r["title"] == ""
    assert r["tech_stack"] == []
    assert r["signals"]["hiring"] is False
