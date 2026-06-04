"""A tiny in-process HTTP server serving a fake site for end-to-end tests."""

from __future__ import annotations

import http.server
import socketserver
import threading

import pytest

# A small site:
#   /            -> links to /about, /products, an external site, a mailto:,
#                   an image and /secret (which robots.txt disallows)
#   /about       -> links back home and to /secret
#   /products    -> links to /products/1
#   /products/1  -> leaf page (depth 2 from home)
#   /secret      -> reachable but disallowed by robots.txt
#   /image.png   -> non-HTML resource
#   /flaky       -> 503 twice, then 200 (exercises retry logic)
PAGES = {
    "/": b"""<!doctype html><html><head><title>Home</title>
        <meta name="description" content="the home page"></head>
        <body><h1>Welcome</h1>
        <a href="/about">About</a>
        <a href="/products">Products</a>
        <a href="/about#team">About (fragment)</a>
        <a href="/image.png">An image</a>
        <a href="/secret">Secret</a>
        <a href="https://external.example.com/page">External</a>
        <a href="mailto:hi@example.com">Mail us</a>
        </body></html>""",
    "/about": b"""<!doctype html><html><head><title>About Us</title></head>
        <body><a href="/">Home</a> <a href="/secret">secret</a></body></html>""",
    "/products": b"""<!doctype html><html><head><title>Products</title></head>
        <body><a href="/products/1">Product 1</a></body></html>""",
    "/products/1": b"""<!doctype html><html><head><title>Product 1</title></head>
        <body>Just a leaf.</body></html>""",
    "/secret": b"""<!doctype html><html><head><title>Secret</title></head>
        <body>robots.txt should keep crawlers out of here</body></html>""",
    "/robots.txt": b"User-agent: *\nDisallow: /secret\nCrawl-delay: 0\n",
    "/image.png": b"\x89PNG\r\n\x1a\n not really an image",
}

# A Korean page encoded as EUC-KR (not UTF-8) to exercise charset detection.
_KOREAN_HTML = (
    "<!doctype html><html><head>"
    "<meta http-equiv='Content-Type' content='text/html; charset=euc-kr'>"
    "<title>한국어 페이지</title></head>"
    "<body><h1>안녕하세요</h1><p>웹 크롤링 테스트입니다.</p></body></html>"
)
KOREAN_TITLE = "한국어 페이지"
KOREAN_BODY_EUCKR = _KOREAN_HTML.encode("euc-kr")


class _Handler(http.server.BaseHTTPRequestHandler):
    flaky_hits = 0

    def do_GET(self):  # noqa: N802 (http.server naming)
        if self.path == "/flaky":
            type(self).flaky_hits += 1
            if type(self).flaky_hits <= 2:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"try again")
                return
            self._respond(200, b"<html><title>Recovered</title></html>", "text/html")
            return

        # EUC-KR page WITH the charset declared in the HTTP header.
        if self.path == "/korean":
            self._respond(200, KOREAN_BODY_EUCKR, "text/html; charset=euc-kr")
            return
        # EUC-KR page with NO charset in the header (must be sniffed from <meta>).
        if self.path == "/korean-meta":
            self._respond(200, KOREAN_BODY_EUCKR, "text/html")
            return

        body = PAGES.get(self.path)
        if body is None:
            self._respond(404, b"not found", "text/plain")
            return
        if self.path.endswith(".png"):
            ctype = "image/png"
        elif self.path.endswith(".txt"):
            ctype = "text/plain"
        else:
            ctype = "text/html; charset=utf-8"
        self._respond(200, body, ctype)

    def _respond(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence the test server
        pass


@pytest.fixture(scope="session")
def server():
    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture(autouse=True)
def _reset_flaky():
    _Handler.flaky_hits = 0
    yield
