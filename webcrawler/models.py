"""Data structures shared across the crawler."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class FetchResult:
    """The raw outcome of a single HTTP request.

    ``url`` is the final URL after any redirects, while ``requested_url`` is
    the URL we originally asked for. ``error`` is set (and ``status_code`` is
    ``0``) when the request never produced a response.

    The body is kept as raw ``content`` bytes plus the ``encoding`` declared in
    the response headers (may be empty). This lets the HTML parser detect the
    real charset from the bytes — important for pages in EUC-KR, Shift_JIS,
    etc. that don't declare a charset in their headers.
    """

    url: str
    requested_url: str
    status_code: int
    content_type: str = ""
    content: bytes = b""
    encoding: str = ""
    elapsed: float = 0.0
    headers: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """True for a successful (2xx) response with no transport error."""
        return self.error is None and 200 <= self.status_code < 300

    @property
    def is_html(self) -> bool:
        ct = self.content_type.lower()
        return "html" in ct or "xhtml" in ct

    @property
    def text(self) -> str:
        """Best-effort decode of the body (declared encoding, else UTF-8)."""
        if not self.content:
            return ""
        try:
            return self.content.decode(self.encoding or "utf-8", errors="replace")
        except (LookupError, TypeError):
            return self.content.decode("utf-8", errors="replace")


@dataclass
class Page:
    """A crawled page together with the data extracted from it."""

    url: str
    status_code: int
    depth: int
    title: str = ""
    description: str = ""
    text: str = ""
    links: list[str] = field(default_factory=list)
    content_type: str = ""
    content_length: int = 0
    fetched_at: str = field(default_factory=_now_iso)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 300

    def to_dict(self) -> dict:
        return asdict(self)
