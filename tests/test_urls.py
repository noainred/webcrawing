from webcrawler.urls import host_of, normalize_url, same_site


def test_normalize_resolves_relative():
    assert normalize_url("/a/b", base="http://x.com/c/d") == "http://x.com/a/b"
    assert normalize_url("page", base="http://x.com/dir/") == "http://x.com/dir/page"


def test_normalize_strips_fragment_and_lowercases_host():
    assert normalize_url("HTTP://Example.COM/Path#frag") == "http://example.com/Path"


def test_normalize_drops_default_ports():
    assert normalize_url("http://x.com:80/") == "http://x.com/"
    assert normalize_url("https://x.com:443/") == "https://x.com/"
    assert normalize_url("http://x.com:8080/") == "http://x.com:8080/"


def test_normalize_adds_root_path():
    assert normalize_url("http://x.com") == "http://x.com/"


def test_normalize_preserves_query():
    assert normalize_url("http://x.com/s?q=1&p=2") == "http://x.com/s?q=1&p=2"


def test_normalize_rejects_non_http_schemes():
    assert normalize_url("mailto:a@b.com") is None
    assert normalize_url("javascript:void(0)") is None
    assert normalize_url("tel:123") is None
    assert normalize_url("") is None
    assert normalize_url("   ") is None


def test_normalize_relative_without_base_is_none():
    assert normalize_url("just/a/path") is None


def test_same_site_and_subdomains():
    assert same_site("http://a.com/x", "a.com") is True
    assert same_site("http://www.a.com/x", "a.com", allow_subdomains=True) is True
    assert same_site("http://www.a.com/x", "a.com", allow_subdomains=False) is False
    assert same_site("http://b.com/x", "a.com") is False


def test_host_of():
    assert host_of("http://Example.com:8080/path") == "example.com"
    assert host_of("not a url") == ""
