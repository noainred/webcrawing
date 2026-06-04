"""HTTP fetching with timeouts, retries and a size cap."""

from __future__ import annotations

import logging
import re
import time

import requests

from .models import FetchResult

logger = logging.getLogger(__name__)

_CHARSET_RE = re.compile(r"charset=([^\s;]+)", re.IGNORECASE)


def _charset_from_content_type(content_type: str) -> str:
    """Return the charset explicitly declared in a Content-Type header, or "".

    Unlike ``requests.Response.encoding``, this does NOT fall back to
    ISO-8859-1 for ``text/*`` without a charset — that legacy default mangles
    UTF-8/EUC-KR pages. When no charset is declared we return "" so the parser
    can sniff the real encoding from the bytes.
    """
    match = _CHARSET_RE.search(content_type or "")
    return match.group(1).strip().strip("'\"").lower() if match else ""

DEFAULT_USER_AGENT = (
    "webcrawler/0.1 (+https://github.com/; polite educational crawler)"
)

# Status codes that are worth retrying (transient server / rate-limit errors).
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Content types whose body we bother to download. Anything else (images,
# PDFs, archives, ...) is recorded by its headers only.
_TEXT_HINTS = ("html", "xml", "text", "json", "javascript")


def _is_text_like(content_type: str) -> bool:
    if not content_type:
        return True  # servers that omit it are usually serving HTML
    ct = content_type.lower()
    return any(hint in ct for hint in _TEXT_HINTS)


class Fetcher:
    """A thin, retrying wrapper around a :class:`requests.Session`."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 10.0,
        max_retries: int = 2,
        backoff: float = 1.0,
        max_bytes: int = 5_000_000,
        session: requests.Session | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.max_bytes = max_bytes
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "*",
            }
        )

    def _sleep_backoff(self, attempt: int) -> None:
        time.sleep(self.backoff * (2 ** attempt))

    def _read_body(self, response: requests.Response) -> bytes:
        """Stream the body up to ``max_bytes`` for text-like responses only.

        Returns raw bytes; charset detection is deferred to the parser so that
        non-UTF-8 pages (e.g. EUC-KR) are handled correctly. We deliberately
        avoid ``response.apparent_encoding`` here — it re-reads the body, which
        is impossible once the stream has been consumed.
        """
        if not _is_text_like(response.headers.get("Content-Type", "")):
            return b""
        raw = bytearray()
        for chunk in response.iter_content(8192):
            raw += chunk
            if len(raw) >= self.max_bytes:
                logger.debug("truncating body at %d bytes for %s", self.max_bytes, response.url)
                break
        return bytes(raw)

    def fetch(self, url: str) -> FetchResult:
        """Fetch ``url`` and return a :class:`FetchResult` (never raises)."""
        last_error: str | None = None
        last_result: FetchResult | None = None

        for attempt in range(self.max_retries + 1):
            try:
                start = time.monotonic()
                response = self.session.get(
                    url, timeout=self.timeout, stream=True, allow_redirects=True
                )
                body = self._read_body(response)
                elapsed = time.monotonic() - start
                result = FetchResult(
                    url=response.url,
                    requested_url=url,
                    status_code=response.status_code,
                    content_type=response.headers.get("Content-Type", ""),
                    content=body,
                    encoding=_charset_from_content_type(response.headers.get("Content-Type", "")),
                    elapsed=elapsed,
                    headers=dict(response.headers),
                )
                response.close()
                last_result = result

                if result.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                    last_error = f"HTTP {result.status_code}"
                    logger.warning("retryable %s on %s (attempt %d)", last_error, url, attempt + 1)
                    self._sleep_backoff(attempt)
                    continue
                return result

            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("request failed for %s: %s", url, last_error)
                if attempt < self.max_retries:
                    self._sleep_backoff(attempt)
                    continue

        if last_result is not None:
            return last_result
        return FetchResult(url=url, requested_url=url, status_code=0, error=last_error)

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
