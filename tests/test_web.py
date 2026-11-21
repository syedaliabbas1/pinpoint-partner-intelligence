import csv
import io

import pytest
from fastapi.testclient import TestClient

from pinpoint.store import Store
from pinpoint.web import create_app, csv_cell
from tests.test_store import person


@pytest.fixture
def client(tmp_path):
    store = Store(tmp_path / "web.sqlite")
    store.observe([person()])
    with TestClient(create_app(store=store, load_seed=False)) as client:
        yield client


def test_directory_search_and_no_results(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Jane Example" in page.text
    assert "Global coverage unverified" in page.text
    assert "No partners match" in client.get("/?q=nonexistent").text
    assert client.get("/api/profiles?q=Jane&firm=wachtell").json()["total"] == 1
    assert client.get("/api/profiles?q=Jane&firm=milbank").json()["total"] == 0


def test_profile_has_source_evidence_and_owned_404(client):
    key = client.get("/api/profiles").json()["items"][0]["id"]
    page = client.get("/partners/" + key)
    assert page.status_code == 200
    assert "Source evidence" in page.text
    assert "https://www.wlrk.com/attorneys/jane-example/" in page.text
    assert client.get("/partners/missing").status_code == 404
    assert "Page not found" in client.get("/not-a-route").text


def test_coverage_has_exactly_fifteen_firms(client):
    firms = client.get("/api/coverage").json()
    assert len(firms) == 15
    assert sum(f["captured"] for f in firms) == 1
    assert all(f["completeness"] == "unverified" for f in firms)
    assert client.get("/coverage").status_code == 200
    assert "Baseline observations" in client.get("/changes").text


def test_csv_matches_current_filters_and_quotes_formula_cells(client):
    response = client.get("/export.csv?q=Jane")
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0]["name"] == "Jane Example"
    assert len(list(csv.DictReader(io.StringIO(client.get("/export.csv?q=missing").text)))) == 0
    for value in ["=1+1", "+cmd", "-2+3", "@SUM(1)", "\t=1", "  =1"]:
        assert csv_cell(value).startswith("'")


def test_query_bounds_and_security_headers(client):
    assert client.get("/api/profiles?page=0").status_code == 422
    assert client.get("/api/profiles?page_size=2001").status_code == 422
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_html_escapes_source_text(tmp_path):
    store = Store(tmp_path / "escape.sqlite")
    p = person()
    p["name"] = "<script>alert(1)</script>"
    store.observe([p])
    with TestClient(create_app(store=store, load_seed=False)) as c:
        assert "<script>alert(1)</script>" not in c.get("/").text


def test_empty_database_has_actionable_state(tmp_path):
    with TestClient(create_app(store=Store(tmp_path / "empty.sqlite"), load_seed=False)) as c:
        assert "No profiles captured yet" in c.get("/").text
        assert c.get("/health").json()["status"] == "ok"
