"""robots.txt fetching, caching and policy decisions.

Follows the common interpretation of RFC 9309:

* ``2xx`` with rules  -> apply the rules
* ``401`` / ``403``   -> treat the whole site as disallowed
* ``404`` / other 4xx -> allow everything (no restrictions published)
* network error       -> allow everything (fail open, but logged)
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


class _AllowAll:
    def can_fetch(self, useragent: str, url: str) -> bool:
        return True

    def crawl_delay(self, useragent: str):
        return None


class _DisallowAll:
    def can_fetch(self, useragent: str, url: str) -> bool:
        return False

    def crawl_delay(self, useragent: str):
        return None


class RobotsCache:
    """Per-origin ``robots.txt`` rules, fetched lazily and cached."""

    def __init__(self, fetcher, user_agent: str, obey: bool = True) -> None:
        self.fetcher = fetcher
        self.user_agent = user_agent
        self.obey = obey
        self._cache: dict[tuple[str, str], object] = {}

    def _rules_for(self, url: str):
        parsed = urlparse(url)
        key = (parsed.scheme, parsed.netloc)
        if key in self._cache:
            return self._cache[key]

        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
        result = self.fetcher.fetch(robots_url)

        if result.ok and result.text:
            parser = RobotFileParser()
            parser.parse(result.text.splitlines())
            rules: object = parser
        elif result.status_code in (401, 403):
            logger.info("robots.txt forbidden (%s) -> disallowing %s", result.status_code, parsed.netloc)
            rules = _DisallowAll()
        else:
            rules = _AllowAll()

        self._cache[key] = rules
        return rules

    def can_fetch(self, url: str) -> bool:
        if not self.obey:
            return True
        return self._rules_for(url).can_fetch(self.user_agent, url)

    def crawl_delay(self, url: str):
        if not self.obey:
            return None
        try:
            return self._rules_for(url).crawl_delay(self.user_agent)
        except Exception:  # pragma: no cover - defensive
            return None
