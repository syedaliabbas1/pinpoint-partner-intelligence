"""Bounded, robots-aware official-site collection. No browser challenge bypass."""

import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from pinpoint.config import FIRMS, ROOT, USER_AGENT, utcnow
from pinpoint.extract import CHALLENGE, extract_profile, official_url, profile_links


class AccessError(Exception):
    pass


class RefreshLock:
    def __init__(self, path):
        self.path = Path(path)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise AccessError(
                "A refresh is already running; inspect the lock before removing a stale one"
            ) from exc
        os.write(self.fd, json.dumps({"pid": os.getpid(), "started_at": utcnow()}).encode())
        return self

    def __exit__(self, *args):
        os.close(self.fd)
        self.path.unlink(missing_ok=True)


class PublicClient:
    def __init__(self, firm_id, cache_dir, transport=None, sleep=time.sleep):
        self.firm_id = firm_id
        self.firm = FIRMS[firm_id]
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=25,
            follow_redirects=False,
            transport=transport,
        )
        self.sleep = sleep
        self.last_request = 0
        self.delay = 1.5
        self.robots = None
        self.robots_note = ""
        self.policy_host = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def _request(self, url):
        if not official_url(self.firm_id, url):
            raise AccessError("Request outside configured official host denied")
        self.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        with self.client.stream("GET", url) as response:
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > 5_000_000:
                    raise AccessError("Response exceeds 5 MB safety limit")
            # httpx honours the server charset; replacement handles broken encodings.
            encoding = response.encoding or "utf-8"
            return (
                response.status_code,
                response.headers,
                bytes(content).decode(encoding, errors="replace"),
            )

    def _load_policy(self, origin):
        url = origin + "/robots.txt"
        for _ in range(4):
            status, headers, text = self._request(url)
            if status in {301, 302, 303, 307, 308}:
                url = urljoin(url, headers.get("location", ""))
                if not official_url(self.firm_id, url) or urlsplit(url).path != "/robots.txt":
                    raise AccessError("Unexpected robots redirect; policy uncertain")
                continue
            break
        if status in {404, 410}:
            text = "User-agent: *\nAllow: /"
            self.robots_note = f"robots.txt HTTP {status}: no policy published"
        elif status != 200:
            raise AccessError(f"robots.txt HTTP {status}; stopped without fetching profiles")
        elif "<html" in text.lower() or CHALLENGE.search(text):
            raise AccessError("robots.txt returned HTML/challenge; policy uncertain")
        else:
            self.robots_note = "robots.txt checked"
        policy = RobotFileParser()
        policy.parse(text.splitlines())
        self.robots = policy
        self.policy_host = urlsplit(origin).netloc
        self.delay = max(1.5, policy.crawl_delay(USER_AGENT) or policy.crawl_delay("*") or 0)
        rate = policy.request_rate(USER_AGENT) or policy.request_rate("*")
        if rate and rate.requests:
            self.delay = max(self.delay, rate.seconds / rate.requests)
        self._save(origin + "/robots.txt", text, "txt")

    def _save(self, url, text, suffix):
        key = hashlib.sha256(text.encode()).hexdigest()
        path = self.cache / (key + "." + suffix)
        payload = text.encode("utf-8")
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != key:
            path.write_bytes(payload)
        with (self.cache / "requests.jsonl").open("a", encoding="utf-8") as log:
            log.write(
                json.dumps({"url": url, "hash": key, "observed_at": utcnow(), "type": suffix})
                + "\n"
            )
        return key

    def get(self, url):
        for _ in range(5):
            if not official_url(self.firm_id, url):
                raise AccessError("Redirect outside configured official host denied")
            parsed = urlsplit(url)
            if self.robots is None or self.policy_host != parsed.netloc:
                self._load_policy(parsed.scheme + "://" + parsed.netloc)
            if not self.robots.can_fetch(USER_AGENT, url):
                raise AccessError("Path disallowed by robots.txt")
            status, headers, html = self._request(url)
            if status in {301, 302, 303, 307, 308}:
                url = urljoin(url, headers.get("location", ""))
                continue
            if status != 200:
                raise AccessError(f"HTTP {status} for {url}; no retry or access bypass")
            if CHALLENGE.search(html[:3000]):
                raise AccessError("Access challenge detected; collection stopped")
            self._save(url, html, "html")
            self.last_url = url
            return html
        raise AccessError("Too many redirects")


def refresh_firm(store, firm_id, max_profiles=15, cache_dir=None):
    firm = FIRMS[firm_id]
    run = store.start_run(firm_id)
    accepted = []
    errors = []
    fetched = 0
    discovered = set()
    practice_profiles = set()
    try:
        with PublicClient(firm_id, cache_dir or ROOT / "data/raw") as client:
            discovery = ROOT / "data/discovery.json"
            seeds = (
                json.loads(discovery.read_text(encoding="utf-8")).get(firm_id, [])
                if discovery.exists()
                else []
            )
            directory_error = ""
            try:
                html = client.get(firm["directory"])
                discovered.update(profile_links(firm_id, firm["directory"], html))
            except AccessError as exc:
                directory_error = str(exc)
                # Access restrictions end a firm run. Invalid routes/5xx can fall back
                # to already discovered official profiles, without changing identity.
                if not directory_error.startswith("Path disallowed by robots.txt") and any(
                    code in directory_error for code in ["403", "401", "429", "robots", "challenge"]
                ):
                    raise
                errors.append("Directory: " + directory_error)
            # Only explicitly configured first-party practice pages are followed;
            # arbitrary news/search candidates never become extra crawl roots.
            for practice_url in list(dict.fromkeys(firm.get("practice_pages", [])))[:3]:
                try:
                    html = client.get(practice_url)
                    practice_profiles.update(profile_links(firm_id, client.last_url, html))
                    discovered.update(practice_profiles)
                except AccessError as exc:
                    message = str(exc)
                    if not message.startswith("Path disallowed by robots.txt") and any(
                        code in message for code in ["403", "401", "429", "robots", "challenge"]
                    ):
                        raise
                    errors.append("Practice page: " + message)
            existing = store.search(firm=firm_id, page_size=100000)["items"]
            # Refresh current records first. Discovery candidates then expand the baseline.
            urls = list(
                dict.fromkeys(
                    [p["source_url"] for p in existing]
                    + seeds
                    + sorted(practice_profiles)
                    + sorted(discovered)
                )
            )
            from pinpoint.extract import is_profile_url

            urls = [u for u in urls if is_profile_url(firm_id, u)]
            for url in urls[:max_profiles]:
                try:
                    html = client.get(url)
                    fetched += 1
                    person = extract_profile(firm_id, client.last_url, html, utcnow())
                    if person:
                        if client.last_url.rstrip("/") != url.rstrip("/"):
                            person["redirected_from"] = url
                        accepted.append(person)
                    else:
                        errors.append(f"Not accepted (scope/title/template needs review): {url}")
                except (AccessError, httpx.HTTPError) as exc:
                    errors.append(str(exc))
                    old = next((p for p in existing if p["source_url"] == url), None)
                    if old and ("404" in str(exc) or "410" in str(exc)):
                        store.flag_missing(old["id"], str(exc))
                    if any(
                        code in str(exc) for code in ["403", "401", "429", "robots", "challenge"]
                    ):
                        break
            accepted = list({p["source_url"].rstrip("/"): p for p in accepted}.values())
            totals = store.observe(accepted)
            message = (
                f"{len(accepted)} accepted / {fetched} profiles fetched; {len(urls)} known candidates; "
                f"bounded to {max_profiles}. {client.robots_note}. Global coverage unverified. "
                + " | ".join(errors[:8])
            )
            status = "partial" if accepted else "needs_review"
            store.finish_run(run, status, message, len(accepted))
            return dict(
                firm_id=firm_id,
                status=status,
                message=message,
                accepted=len(accepted),
                fetched=fetched,
                candidates=len(urls),
                discovered=len(discovered),
                changes=totals,
            )
    except KeyboardInterrupt:
        store.finish_run(
            run,
            "interrupted",
            "Interrupted by operator; pending observations were not committed.",
            0,
        )
        raise
    except (AccessError, httpx.HTTPError, ValueError) as exc:
        store.finish_run(run, "blocked", str(exc), 0)
        return dict(
            firm_id=firm_id, status="blocked", message=str(exc), accepted=0, fetched=fetched
        )
