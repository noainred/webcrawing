import csv
import json

import pytest

from webcrawler import storage
from webcrawler.models import Page

PAGES = [
    Page(url="http://x.com/", status_code=200, depth=0, title="Home",
         description="d", text="body text", links=["http://x.com/a", "http://x.com/b"]),
    Page(url="http://x.com/a", status_code=404, depth=1, error="HTTP 404"),
]


def test_save_json_roundtrip(tmp_path):
    path = tmp_path / "out.json"
    storage.save(PAGES, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["title"] == "Home"
    assert data[1]["error"] == "HTTP 404"


def test_save_jsonl(tmp_path):
    path = tmp_path / "out.jsonl"
    fmt = storage.save(PAGES, path)
    assert fmt == "jsonl"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["url"] == "http://x.com/"


def test_save_csv_flattens_links_and_omits_text(tmp_path):
    path = tmp_path / "out.csv"
    storage.save(PAGES, path)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert rows[0]["links"] == "http://x.com/a http://x.com/b"
    assert "text" not in rows[0]  # text is not exported to CSV


def test_format_inferred_from_suffix(tmp_path):
    assert storage.save(PAGES, tmp_path / "a.csv") == "csv"
    assert storage.save(PAGES, tmp_path / "a.jsonl") == "jsonl"


def test_explicit_format_overrides_suffix(tmp_path):
    path = tmp_path / "data.txt"
    assert storage.save(PAGES, path, fmt="json") == "json"
    assert json.loads(path.read_text(encoding="utf-8"))[0]["title"] == "Home"


def test_unknown_format_raises(tmp_path):
    with pytest.raises(ValueError):
        storage.save(PAGES, tmp_path / "a.xml")
