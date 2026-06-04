from webcrawler.fetcher import Fetcher
from webcrawler.robots import RobotsCache, _AllowAll, _DisallowAll


def test_robots_blocks_disallowed_path(server):
    with Fetcher() as fetcher:
        robots = RobotsCache(fetcher, "webcrawler")
        assert robots.can_fetch(server + "/secret") is False
        assert robots.can_fetch(server + "/about") is True


def test_robots_caches_per_origin(server):
    with Fetcher() as fetcher:
        robots = RobotsCache(fetcher, "webcrawler")
        robots.can_fetch(server + "/secret")
        # Second call must be served from cache (one entry for the origin).
        robots.can_fetch(server + "/about")
        assert len(robots._cache) == 1


def test_robots_disabled_allows_everything(server):
    with Fetcher() as fetcher:
        robots = RobotsCache(fetcher, "webcrawler", obey=False)
        assert robots.can_fetch(server + "/secret") is True


def test_allow_all_and_disallow_all():
    assert _AllowAll().can_fetch("ua", "http://x/") is True
    assert _DisallowAll().can_fetch("ua", "http://x/") is False
