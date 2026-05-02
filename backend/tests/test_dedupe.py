from app.services.dedupe import normalize_domain


def test_strips_scheme_and_www():
    assert normalize_domain("https://www.Acme.com/about?x=1") == "acme.com"


def test_naked_domain():
    assert normalize_domain("ACME.COM") == "acme.com"


def test_preserves_subdomain():
    assert normalize_domain("blog.acme.co.uk") == "blog.acme.co.uk"


def test_drops_port():
    assert normalize_domain("https://acme.com:8080/x") == "acme.com"


def test_empty():
    assert normalize_domain("") == ""
    assert normalize_domain("   ") == ""
