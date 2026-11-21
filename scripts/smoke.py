"""Exercise the actual running server over HTTP, without a browser or network scraping."""

import argparse

import httpx
from bs4 import BeautifulSoup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base, timeout=20) as client:
        for route in [
            "/",
            "/coverage",
            "/changes",
            "/health",
            "/api/coverage",
            "/static/app.css",
            "/static/app.js",
        ]:
            response = client.get(route)
            assert response.status_code == 200, (route, response.status_code)
            print("200", route)
        profiles = client.get("/api/profiles?page_size=2000").json()
        assert len(client.get("/api/coverage").json()) == 15
        for person in profiles["items"]:
            response = client.get("/partners/" + person["id"])
            assert response.status_code == 200, person["name"]
            soup = BeautifulSoup(response.text, "html.parser")
            assert soup.h1.get_text(strip=True) == person["name"]
            assert soup.select_one('a[href="' + person["source_url"] + '"]')
        assert client.get("/?q=__no_such_partner__").status_code == 200
        assert "No partners match" in client.get("/?q=__no_such_partner__").text
        assert client.get("/missing-page").status_code == 404
        assert client.get("/api/profiles?page=0").status_code == 422
        assert client.get("/export.csv").headers["content-type"].startswith("text/csv")
        print("Verified profile detail routes:", len(profiles["items"]))
        print("Verified no-results, CSV, validation and 404 states.")


if __name__ == "__main__":
    main()
