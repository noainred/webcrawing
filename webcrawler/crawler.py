"""The breadth-first crawl engine that ties the pieces together."""

from __future__ import annotations

import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional

from .fetcher import DEFAULT_USER_AGENT, Fetcher
from .models import FetchResult, Page
from .parser import parse as parse_html
from .robots import RobotsCache
from .urls import host_of, normalize_url, same_site

logger = logging.getLogger(__name__)


@dataclass
class CrawlConfig:
    """Knobs controlling how a crawl behaves."""

    max_depth: int = 2          # link distance from the seeds (seeds are depth 0)
    max_pages: int = 100        # hard cap on pages actually fetched
    same_domain: bool = True    # stay on the seed host(s)
    allow_subdomains: bool = True
    delay: float = 0.5          # minimum seconds between requests to one host
    obey_robots: bool = True
    user_agent: str = DEFAULT_USER_AGENT
    timeout: float = 10.0
    max_retries: int = 2
    text_max_len: int = 2000
    include: Optional[str] = None   # regex; if set, only matching URLs are crawled
    exclude: Optional[str] = None   # regex; matching URLs are skipped
    allowed_hosts: list[str] = field(default_factory=list)  # extra in-scope hosts


class Crawler:
    """Crawl one or more seed URLs breadth-first.

    Use it as an iterator (``for page in crawler.crawl(seed): ...``) to stream
    results, or call :meth:`run` to get the full list. Results are also kept
    in ``crawler.pages`` for convenience.
    """

    def __init__(self, config: CrawlConfig | None = None, fetcher: Fetcher | None = None) -> None:
        self.config = config or CrawlConfig()
        self.fetcher = fetcher or Fetcher(
            user_agent=self.config.user_agent,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
        )
        self.robots = RobotsCache(self.fetcher, self.config.user_agent, obey=self.config.obey_robots)

        self.visited: set[str] = set()
        self.pages: list[Page] = []
        self._last_request: dict[str, float] = {}
        self._allowed_hosts: set[str] = {h.lower() for h in self.config.allowed_hosts}
        self._include = re.compile(self.config.include) if self.config.include else None
        self._exclude = re.compile(self.config.exclude) if self.config.exclude else None

    # -- scope & politeness ------------------------------------------------

    def _in_scope(self, url: str) -> bool:
        if self._exclude and self._exclude.search(url):
            return False
        if self._include and not self._include.search(url):
            return False
        if not self.config.same_domain:
            return True
        return any(
            same_site(url, host, self.config.allow_subdomains) for host in self._allowed_hosts
        )

    def _respect_delay(self, url: str) -> None:
        if self.config.delay <= 0:
            return
        host = host_of(url)
        delay = self.config.delay
        crawl_delay = self.robots.crawl_delay(url)
        if crawl_delay:
            delay = max(delay, float(crawl_delay))
        last = self._last_request.get(host)
        if last is not None:
            wait = delay - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_request[host] = time.monotonic()

    # -- page construction -------------------------------------------------

    def _build_page(self, result: FetchResult, depth: int) -> Page:
        if not result.ok:
            return Page(
                url=result.url,
                status_code=result.status_code,
                depth=depth,
                content_type=result.content_type,
                content_length=len(result.content),
                error=result.error or f"HTTP {result.status_code}",
            )
        data = (
            parse_html(
                result.content,
                result.url,
                self.config.text_max_len,
                from_encoding=result.encoding or None,
            )
            if result.is_html
            else {"title": "", "description": "", "text": "", "links": []}
        )
        return Page(
            url=result.url,
            status_code=result.status_code,
            depth=depth,
            title=data["title"],
            description=data["description"],
            text=data["text"],
            links=data["links"],
            content_type=result.content_type,
            content_length=len(result.content),
        )

    # -- main loop ---------------------------------------------------------

    def crawl(self, start_urls: str | Iterable[str]) -> Iterator[Page]:
        if isinstance(start_urls, str):
            start_urls = [start_urls]

        queue: deque[tuple[str, int]] = deque()
        queued: set[str] = set()
        for raw in start_urls:
            seed = normalize_url(raw)
            if not seed:
                logger.warning("ignoring invalid seed URL: %r", raw)
                continue
            host = host_of(seed)
            if host:
                self._allowed_hosts.add(host)
            if seed not in queued:
                queued.add(seed)
                queue.append((seed, 0))

        while queue and len(self.pages) < self.config.max_pages:
            url, depth = queue.popleft()
            if url in self.visited:
                continue
            self.visited.add(url)

            if not self._in_scope(url):
                logger.debug("out of scope: %s", url)
                continue
            if not self.robots.can_fetch(url):
                logger.info("blocked by robots.txt: %s", url)
                continue

            self._respect_delay(url)
            logger.info("GET (depth %d) %s", depth, url)
            result = self.fetcher.fetch(url)
            page = self._build_page(result, depth)
            self.pages.append(page)
            yield page

            if page.ok and result.is_html and depth < self.config.max_depth:
                for link in page.links:
                    if link not in self.visited and link not in queued:
                        queued.add(link)
                        queue.append((link, depth + 1))

    def run(self, start_urls: str | Iterable[str]) -> list[Page]:
        """Run the crawl to completion and return all pages."""
        return list(self.crawl(start_urls))

    def close(self) -> None:
        self.fetcher.close()

    def __enter__(self) -> "Crawler":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
