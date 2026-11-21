import httpx
import pytest

from pinpoint.collect import AccessError, PublicClient, RefreshLock


def client(handler, tmp_path):
    return PublicClient(
        "milbank", tmp_path, transport=httpx.MockTransport(handler), sleep=lambda _: None
    )


def test_robots_disallow_prevents_profile_request(tmp_path):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text="User-agent: *\nDisallow: /en/professionals/")

    with client(handler, tmp_path) as c:
        with pytest.raises(AccessError, match="robots"):
            c.get("https://www.milbank.com/en/professionals/jane.html")
    assert len(calls) == 1


def test_missing_robots_is_allowed_but_server_error_fails_closed(tmp_path):
    for status, allowed in [(404, True), (500, False), (403, False), (429, False)]:

        def handler(request):
            return httpx.Response(
                status if request.url.path == "/robots.txt" else 200,
                text="<main>Public page</main>",
            )

        with client(handler, tmp_path) as c:
            if allowed:
                assert "Public page" in c.get("https://www.milbank.com/en/professionals/")
            else:
                with pytest.raises(AccessError):
                    c.get("https://www.milbank.com/en/professionals/")


def test_does_not_follow_redirect_outside_official_host(tmp_path):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(302, headers={"location": "https://evil.example/steal"})

    with client(handler, tmp_path) as c:
        with pytest.raises(AccessError, match="host"):
            c.get("https://www.milbank.com/en/professionals/")
    assert len(calls) == 2


def test_redirect_cannot_enter_disallowed_path(tmp_path):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        return httpx.Response(302, headers={"location": "/private"})

    with client(handler, tmp_path) as c:
        with pytest.raises(AccessError, match="robots"):
            c.get("https://www.milbank.com/en/professionals/")


def test_lock_blocks_concurrent_refresh_and_releases_after_error(tmp_path):
    path = tmp_path / "refresh.lock"
    with pytest.raises(RuntimeError, match="test interruption"):
        with RefreshLock(path):
            with pytest.raises(AccessError, match="already"):
                with RefreshLock(path):
                    pass
            raise RuntimeError("test interruption")
    with RefreshLock(path):
        assert path.exists()
    assert not path.exists()


def test_real_stream_response_is_consumed_only_once(tmp_path):
    class Stream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"<main>Public page</main>"

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(
            200, stream=Stream(), headers={"content-type": "text/html; charset=utf-8"}
        )

    with client(handler, tmp_path) as c:
        assert "Public page" in c.get("https://www.milbank.com/en/professionals/")


def test_successful_redirect_records_final_source_url(tmp_path):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path.endswith("old.html"):
            return httpx.Response(301, headers={"location": "/en/professionals/new.html"})
        return httpx.Response(200, text="<main>Public profile</main>")

    with client(handler, tmp_path) as c:
        c.get("https://www.milbank.com/en/professionals/old.html")
        assert c.last_url == "https://www.milbank.com/en/professionals/new.html"


def test_snapshot_hash_matches_stored_utf8_bytes(tmp_path):
    import hashlib

    html = "<main>One\r\nTwo\nThree</main>"

    def handler(request):
        return httpx.Response(
            200, text="User-agent: *\nAllow: /" if request.url.path == "/robots.txt" else html
        )

    with client(handler, tmp_path) as c:
        result = c.get("https://www.milbank.com/en/professionals/jane.html")
    key = hashlib.sha256(result.encode()).hexdigest()
    assert (tmp_path / (key + ".html")).read_bytes() == result.encode()
