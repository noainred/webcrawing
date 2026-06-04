"""URL normalization and scope helpers."""

from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

# Only these schemes are worth crawling; mailto:, javascript:, tel:, data:
# and friends are dropped during normalization.
CRAWLABLE_SCHEMES = {"http", "https"}

_DEFAULT_PORTS = {"http": "80", "https": "443"}


def normalize_url(url: str, base: str | None = None) -> str | None:
    """Resolve ``url`` against ``base`` and return a canonical absolute URL.

    Returns ``None`` when the URL is empty or not crawlable (e.g. a
    ``mailto:`` link or a relative URL with no base to resolve against).

    Canonicalization removes the fragment, lower-cases the scheme and host,
    drops the default port and ensures a non-empty path. The query string is
    preserved as-is because it is often significant.
    """
    if not url or not url.strip():
        return None
    url = url.strip()

    if base:
        url = urljoin(base, url)

    url, _ = urldefrag(url)
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    if scheme not in CRAWLABLE_SCHEMES:
        return None
    if not parsed.hostname:
        return None

    host = parsed.hostname  # already lower-cased by urlparse
    netloc = host
    if parsed.port is not None and str(parsed.port) != _DEFAULT_PORTS.get(scheme):
        netloc = f"{host}:{parsed.port}"

    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))


def host_of(url: str) -> str:
    """Return the lower-cased hostname of ``url`` (or ``""``)."""
    return (urlparse(url).hostname or "").lower()


def same_site(url: str, host: str, allow_subdomains: bool = True) -> bool:
    """True when ``url``'s host equals ``host`` (or is a subdomain of it)."""
    h = host_of(url)
    if not h or not host:
        return False
    if h == host:
        return True
    return allow_subdomains and h.endswith("." + host)
