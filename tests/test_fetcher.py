from webcrawler.fetcher import Fetcher, _is_text_like


def test_fetch_ok_html(server):
    with Fetcher() as fetcher:
        result = fetcher.fetch(server + "/about")
    assert result.ok
    assert result.status_code == 200
    assert result.is_html
    assert "About Us" in result.text


def test_fetch_404(server):
    with Fetcher() as fetcher:
        result = fetcher.fetch(server + "/missing")
    assert result.status_code == 404
    assert not result.ok


def test_fetch_skips_body_for_non_text(server):
    with Fetcher() as fetcher:
        result = fetcher.fetch(server + "/image.png")
    assert result.status_code == 200
    assert result.is_html is False
    assert result.text == ""  # binary body not downloaded


def test_fetch_retries_then_succeeds(server):
    # /flaky returns 503 twice before a 200; two retries should reach it.
    with Fetcher(max_retries=2, backoff=0.01) as fetcher:
        result = fetcher.fetch(server + "/flaky")
    assert result.status_code == 200
    assert result.ok


def test_fetch_gives_up_on_persistent_503(server):
    # With no retries we see the first 503 and stop.
    with Fetcher(max_retries=0) as fetcher:
        result = fetcher.fetch(server + "/flaky")
    assert result.status_code == 503
    assert not result.ok


def test_fetch_connection_error_returns_error_result():
    # Port 9 (discard) is essentially never accepting connections.
    with Fetcher(timeout=1, max_retries=0) as fetcher:
        result = fetcher.fetch("http://127.0.0.1:9/")
    assert result.status_code == 0
    assert result.error is not None


def test_is_text_like():
    assert _is_text_like("text/html; charset=utf-8")
    assert _is_text_like("application/xhtml+xml")
    assert _is_text_like("")  # missing header -> assume text
    assert not _is_text_like("image/png")
    assert not _is_text_like("application/octet-stream")
