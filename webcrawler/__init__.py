"""webcrawler — a small, polite, HTML-focused web crawler.

Quick start::

    from webcrawler import Crawler, CrawlConfig

    crawler = Crawler(CrawlConfig(max_depth=2, max_pages=50))
    for page in crawler.crawl("https://example.com"):
        print(page.status_code, page.url, page.title)

The crawler performs a breadth-first traversal starting from one or more
seed URLs, parses each HTML page with BeautifulSoup, extracts the title,
meta description, visible text and outbound links, and (by default) stays
on the seed domain while obeying ``robots.txt`` and a per-host politeness
delay.
"""

from .models import FetchResult, Page
from .crawler import Crawler, CrawlConfig
from .fetcher import Fetcher

__all__ = ["Crawler", "CrawlConfig", "Fetcher", "Page", "FetchResult"]
__version__ = "0.1.0"
