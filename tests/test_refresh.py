import httpx
import pytest
import json

from pinpoint import collect
from pinpoint.store import Store


def test_refresh_discovers_profiles_from_bounded_configured_practice_pages(tmp_path, monkeypatch):
    store = Store(tmp_path / "practice.sqlite")
    pages = [f"https://www.milbank.com/en/practices/area-{i}.html" for i in range(4)]
    profile = "https://www.milbank.com/en/professionals/jane-example.html"
    calls = []
    monkeypatch.setitem(
        collect.FIRMS, "milbank", dict(collect.FIRMS["milbank"], practice_pages=pages)
    )
    monkeypatch.setattr(collect, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data/discovery.json").write_text(
        json.dumps({"milbank": ["https://www.milbank.com/news/unrelated"]})
    )

    def handler(request):
        url = str(request.url)
        calls.append(url)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /en/practices/area-0.html")
        if url == profile:
            return httpx.Response(
                200,
                text="<main><h1>Jane Example</h1><h2>Partner</h2><p>Jane advises on mergers and acquisitions.</p></main>",
            )
        if url in pages:
            return httpx.Response(200, text=f'<a href="{profile}">Jane Example</a>')
        return httpx.Response(
            200,
            text='<a href="https://www.milbank.com/en/professionals/aaa-directory.html">Other directory candidate</a>',
        )

    original = collect.PublicClient
    monkeypatch.setattr(
        collect,
        "PublicClient",
        lambda firm, cache: original(
            firm, cache, transport=httpx.MockTransport(handler), sleep=lambda _: None
        ),
    )
    result = collect.refresh_firm(store, "milbank", max_profiles=1)
    assert result["accepted"] == 1
    assert pages[0] not in calls
    assert pages[1] in calls and pages[2] in calls
    assert pages[3] not in calls
    assert not any("unrelated" in url for url in calls)


def test_practice_access_denial_stops_without_requesting_profiles(tmp_path, monkeypatch):
    store = Store(tmp_path / "denied.sqlite")
    practice = "https://www.milbank.com/en/practices/mergers.html"
    profile = "https://www.milbank.com/en/professionals/jane-example.html"
    calls = []
    monkeypatch.setitem(
        collect.FIRMS, "milbank", dict(collect.FIRMS["milbank"], practice_pages=[practice])
    )
    monkeypatch.setattr(collect, "ROOT", tmp_path)

    def handler(request):
        url = str(request.url)
        calls.append(url)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if url == practice:
            return httpx.Response(403)
        return httpx.Response(200, text=f'<a href="{profile}">Jane Example</a>')

    original = collect.PublicClient
    monkeypatch.setattr(
        collect,
        "PublicClient",
        lambda firm, cache: original(
            firm, cache, transport=httpx.MockTransport(handler), sleep=lambda _: None
        ),
    )
    result = collect.refresh_firm(store, "milbank")
    assert result["status"] == "blocked"
    assert profile not in calls
    assert calls.count(practice) == 1


def test_complete_refresh_lifecycle_retains_failed_sources(tmp_path, monkeypatch):
    store = Store(tmp_path / "refresh.sqlite")
    profile_url = "https://www.milbank.com/en/professionals/jane-example.html"
    state = {"office": "New York", "status": 200}

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if str(request.url) == profile_url:
            return httpx.Response(
                state["status"],
                text=f'<main><h1>Jane Example</h1><h2>Partner</h2><p>Jane Example advises on mergers and acquisitions.</p><div class="office">{state["office"]}</div></main>',
            )
        return httpx.Response(200, text=f'<a href="{profile_url}">Jane Example</a>')

    original = collect.PublicClient
    monkeypatch.setattr(collect, "ROOT", tmp_path)
    monkeypatch.setattr(
        collect,
        "PublicClient",
        lambda firm, cache: original(
            firm, cache, transport=httpx.MockTransport(handler), sleep=lambda _: None
        ),
    )
    assert collect.refresh_firm(store, "milbank")["accepted"] == 1
    assert store.events() == []
    assert collect.refresh_firm(store, "milbank")["changes"]["unchanged"] == 1
    assert store.events() == []
    state["office"] = "London"
    assert collect.refresh_firm(store, "milbank")["changes"]["changed"] == 1
    assert store.events()[0]["changes"]["offices"]["after"] == ["London"]
    state["status"] = 404
    collect.refresh_firm(store, "milbank")
    collect.refresh_firm(store, "milbank")
    assert store.search()["total"] == 1
    assert len([e for e in store.events() if e["kind"] == "source_unavailable"]) == 1
    assert store.search()["items"][0]["offices"] == ["London"]


def test_keyboard_interrupt_finishes_run_without_committing_partial_data(tmp_path, monkeypatch):
    store = Store(tmp_path / "interrupted.sqlite")
    original = collect.PublicClient

    def handler(request):
        raise KeyboardInterrupt()

    monkeypatch.setattr(
        collect,
        "PublicClient",
        lambda firm, cache: original(
            firm, cache, transport=httpx.MockTransport(handler), sleep=lambda _: None
        ),
    )
    with pytest.raises(KeyboardInterrupt):
        collect.refresh_firm(store, "milbank", cache_dir=tmp_path / "raw")
    assert store.runs()[0]["status"] == "interrupted"
    assert store.search()["total"] == 0


def test_disallowed_directory_does_not_block_independently_allowed_known_profiles(
    tmp_path, monkeypatch
):
    from tests.test_store import person

    store = Store(tmp_path / "paths.sqlite")
    profile_url = "https://www.cravath.com/people/jane-example.html"
    row = dict(person(), firm_id="cravath", source_url=profile_url)
    store.observe([row])
    requests = []

    def handler(request):
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /people/index.html")
        return httpx.Response(
            200,
            text='<main><h1>Jane Example</h1><h2>Partner</h2><p>Jane advises on mergers and acquisitions.</p><div class="office">New York</div></main>',
        )

    original = collect.PublicClient
    monkeypatch.setattr(collect, "ROOT", tmp_path)
    monkeypatch.setattr(
        collect,
        "PublicClient",
        lambda firm, cache: original(
            firm, cache, transport=httpx.MockTransport(handler), sleep=lambda _: None
        ),
    )
    result = collect.refresh_firm(store, "cravath", max_profiles=1)
    assert result["accepted"] == 1
    assert not any(url.endswith("/people/index.html") for url in requests)
    assert profile_url in requests
