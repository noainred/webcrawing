from urllib.parse import urlparse

from webcrawler import Crawler, CrawlConfig


def _paths(pages):
    return {urlparse(p.url).path for p in pages}


def _config(**kw):
    # No politeness delay in tests so they run fast.
    kw.setdefault("delay", 0)
    return CrawlConfig(**kw)


def test_crawl_stays_on_domain_and_obeys_robots(server):
    with Crawler(_config(max_depth=2, max_pages=50)) as crawler:
        pages = crawler.run(server + "/")
    paths = _paths(pages)
    # Reachable, in-scope, allowed pages are fetched...
    assert {"/", "/about", "/products", "/products/1"} <= paths
    # ...the image (non-HTML) is fetched too...
    assert "/image.png" in paths
    # ...but robots-disallowed and external pages are not.
    assert "/secret" not in paths
    assert all("external.example.com" not in p.url for p in pages)


def test_depth_limit_is_respected(server):
    with Crawler(_config(max_depth=1, max_pages=50)) as crawler:
        pages = crawler.run(server + "/")
    by_path = {urlparse(p.url).path: p for p in pages}
    assert by_path["/"].depth == 0
    assert by_path["/about"].depth == 1
    # /products/1 is two hops away, so depth=1 must not reach it.
    assert "/products/1" not in by_path


def test_max_pages_caps_fetches(server):
    with Crawler(_config(max_depth=5, max_pages=2)) as crawler:
        pages = crawler.run(server + "/")
    assert len(pages) == 2


def test_non_html_page_has_no_links_or_title(server):
    with Crawler(_config(max_depth=2)) as crawler:
        pages = crawler.run(server + "/")
    image = next(p for p in pages if p.url.endswith("/image.png"))
    assert image.status_code == 200
    assert image.title == ""
    assert image.links == []


def test_visited_pages_are_unique(server):
    with Crawler(_config(max_depth=3)) as crawler:
        pages = crawler.run(server + "/")
    urls = [p.url for p in pages]
    assert len(urls) == len(set(urls))


def test_allow_external_can_leave_domain(server):
    # External host is unreachable in tests, but it should at least be
    # attempted (producing an error page) rather than skipped as out of scope.
    cfg = _config(max_depth=1, max_pages=50, obey_robots=False)
    cfg.same_domain = False
    cfg.timeout = 1
    cfg.max_retries = 0
    with Crawler(cfg) as crawler:
        pages = crawler.run(server + "/")
    assert any("external.example.com" in p.url for p in pages)


def test_exclude_regex_skips_matches(server):
    with Crawler(_config(max_depth=2, exclude=r"/products")) as crawler:
        pages = crawler.run(server + "/")
    assert all("/products" not in urlparse(p.url).path for p in pages)


def test_include_regex_limits_crawl(server):
    # Only the seed and /about match; /products* is excluded by omission.
    with Crawler(_config(max_depth=2, include=r"/($|about)")) as crawler:
        pages = crawler.run(server + "/")
    paths = _paths(pages)
    assert "/about" in paths
    assert "/products" not in paths


def test_robots_can_be_disabled(server):
    with Crawler(_config(max_depth=2, obey_robots=False)) as crawler:
        pages = crawler.run(server + "/")
    assert "/secret" in _paths(pages)


def test_seed_is_normalized(server):
    # A seed with a fragment should still be crawled (fragment stripped).
    with Crawler(_config(max_depth=0)) as crawler:
        pages = crawler.run(server + "/#top")
    assert len(pages) == 1
    assert pages[0].url == server + "/"
