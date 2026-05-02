from __future__ import annotations

import re
from urllib.parse import urlparse

_TRAILING_TLD_PORT = re.compile(r":\d+$")


def normalize_domain(url_or_domain: str) -> str:
    """Reduce a URL or domain string to its canonical lowercased registrable host.

    Examples:
        https://www.Acme.com/about?x=1  -> acme.com
        ACME.COM                         -> acme.com
        sub.acme.co.uk                   -> sub.acme.co.uk (subdomain preserved)
        www.acme.com                     -> acme.com
    """
    if not url_or_domain:
        return ""

    raw = url_or_domain.strip()
    if not raw:
        return ""

    # Ensure urlparse sees a scheme so it puts the host in netloc.
    if "://" not in raw:
        raw = "http://" + raw

    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    host = _TRAILING_TLD_PORT.sub("", host)
    if host.startswith("www."):
        host = host[4:]
    return host
