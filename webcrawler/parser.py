"""HTML parsing and data extraction built on BeautifulSoup."""

from __future__ import annotations

from bs4 import BeautifulSoup

from .urls import normalize_url

# Prefer lxml when available (fast, lenient); fall back to the stdlib parser
# so the package keeps working even without lxml installed.
_PARSER_CHAIN = ("lxml", "html.parser")

_NON_CONTENT_TAGS = ("script", "style", "noscript", "template")


def make_soup(markup, from_encoding: str | None = None) -> BeautifulSoup:
    """Build a soup from ``markup`` (``str`` or ``bytes``).

    When ``markup`` is bytes, BeautifulSoup detects the encoding from a BOM,
    a ``<meta charset>`` tag or content sniffing. ``from_encoding`` (the
    charset declared in the HTTP headers, if any) takes precedence.
    """
    last_error: Exception | None = None
    for parser in _PARSER_CHAIN:
        try:
            if from_encoding and isinstance(markup, (bytes, bytearray)):
                return BeautifulSoup(markup, parser, from_encoding=from_encoding)
            return BeautifulSoup(markup, parser)
        except Exception as exc:  # parser not installed / unusable
            last_error = exc
    raise RuntimeError(f"no usable HTML parser available: {last_error}")


def extract_title(soup: BeautifulSoup) -> str:
    if soup.title:
        title = soup.title.get_text(strip=True)
        if title:
            return title
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def extract_description(soup: BeautifulSoup) -> str:
    for attrs in ({"name": "description"}, {"property": "og:description"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""


def extract_text(soup: BeautifulSoup, max_len: int = 2000) -> str:
    for tag in soup(list(_NON_CONTENT_TAGS)):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ", strip=True).split())
    if max_len and max_len > 0:
        return text[:max_len]
    return text


def extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Return the de-duplicated, absolute, crawlable links on the page."""
    seen: set[str] = set()
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        normalized = normalize_url(anchor["href"], base=base_url)
        if normalized and normalized not in seen:
            seen.add(normalized)
            links.append(normalized)
    return links


def parse(markup, base_url: str, text_max_len: int = 2000,
          from_encoding: str | None = None) -> dict:
    """Parse ``markup`` (str or bytes) and return title, description, text, links."""
    soup = make_soup(markup, from_encoding=from_encoding)
    return {
        "title": extract_title(soup),
        "description": extract_description(soup),
        "text": extract_text(soup, text_max_len),
        "links": extract_links(soup, base_url),
    }
