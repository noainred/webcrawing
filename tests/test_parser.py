from webcrawler.parser import (
    extract_description,
    extract_links,
    extract_title,
    make_soup,
    parse,
)

SAMPLE = """
<html><head>
  <title>  My Page  </title>
  <meta name="description" content="hello world">
</head><body>
  <script>var x = 1;</script>
  <style>.a{color:red}</style>
  <h1>Heading</h1>
  <p>Some  visible   text.</p>
  <a href="/rel">rel</a>
  <a href="http://other.com/abs">abs</a>
  <a href="/rel">dup</a>
  <a href="mailto:x@y.com">mail</a>
  <a>no href</a>
</body></html>
"""


def test_extract_title_prefers_title_tag():
    assert extract_title(make_soup(SAMPLE)) == "My Page"


def test_extract_title_falls_back_to_h1():
    soup = make_soup("<html><body><h1>Only H1</h1></body></html>")
    assert extract_title(soup) == "Only H1"


def test_extract_description():
    assert extract_description(make_soup(SAMPLE)) == "hello world"


def test_extract_description_og_fallback():
    soup = make_soup('<meta property="og:description" content="og text">')
    assert extract_description(soup) == "og text"


def test_extract_text_drops_scripts_and_collapses_whitespace():
    text = parse(SAMPLE, "http://base.com")["text"]
    assert "var x" not in text
    assert "color:red" not in text
    assert "Some visible text." in text


def test_extract_links_absolutizes_dedupes_and_filters():
    links = extract_links(make_soup(SAMPLE), "http://base.com/dir/")
    assert "http://base.com/rel" in links
    assert "http://other.com/abs" in links
    assert links.count("http://base.com/rel") == 1  # de-duplicated
    assert all("mailto" not in link for link in links)


def test_parse_returns_all_fields():
    data = parse(SAMPLE, "http://base.com")
    assert set(data) == {"title", "description", "text", "links"}
    assert data["title"] == "My Page"


def test_text_max_len_truncates():
    data = parse("<p>" + "x" * 5000 + "</p>", "http://b.com", text_max_len=100)
    assert len(data["text"]) == 100
