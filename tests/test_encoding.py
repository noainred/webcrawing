"""Charset handling: non-UTF-8 pages (e.g. EUC-KR) must decode correctly."""

from webcrawler.fetcher import Fetcher
from webcrawler.parser import parse

from .conftest import KOREAN_BODY_EUCKR, KOREAN_TITLE


def test_parse_bytes_with_declared_encoding():
    data = parse(KOREAN_BODY_EUCKR, "http://x.com", from_encoding="euc-kr")
    assert data["title"] == KOREAN_TITLE
    assert "안녕하세요" in data["text"]


def test_parse_bytes_sniffs_meta_charset():
    # No declared encoding: BeautifulSoup must detect EUC-KR from the meta tag.
    data = parse(KOREAN_BODY_EUCKR, "http://x.com", from_encoding=None)
    assert data["title"] == KOREAN_TITLE


def test_fetch_euckr_with_header_charset(server):
    with Fetcher() as fetcher:
        result = fetcher.fetch(server + "/korean")
    assert result.encoding.lower() in ("euc-kr", "euc_kr")
    data = parse(result.content, result.url, from_encoding=result.encoding or None)
    assert data["title"] == KOREAN_TITLE


def test_fetch_euckr_without_header_charset(server):
    with Fetcher() as fetcher:
        result = fetcher.fetch(server + "/korean-meta")
    # Header gave no charset, so we rely on the parser sniffing the meta tag.
    data = parse(result.content, result.url, from_encoding=result.encoding or None)
    assert data["title"] == KOREAN_TITLE
    assert "웹 크롤링" in data["text"]
