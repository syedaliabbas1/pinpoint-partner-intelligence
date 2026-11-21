"""SQLite persistence. Each observation batch is atomic; absence never deletes data."""

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from pinpoint.config import utcnow

FIELDS = ("name", "title", "practices", "offices", "summary", "source_url")


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY, firm_id TEXT NOT NULL, source_url TEXT NOT NULL,
                    name TEXT NOT NULL, search_text TEXT NOT NULL, payload TEXT NOT NULL,
                    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
                    UNIQUE(firm_id, source_url)
                );
                CREATE INDEX IF NOT EXISTS profile_firm ON profiles(firm_id);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, profile_id TEXT NOT NULL, firm_id TEXT NOT NULL,
                    kind TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY, firm_id TEXT NOT NULL, started_at TEXT NOT NULL,
                    finished_at TEXT, status TEXT NOT NULL, message TEXT NOT NULL DEFAULT '',
                    count INTEGER NOT NULL DEFAULT 0
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def observe(self, people, preserve_first_seen=False):
        totals = {"baseline": 0, "changed": 0, "unchanged": 0}
        with self.connect() as db:
            for original in people:
                p = dict(original)
                if not p.get("name") or not p.get("evidence") or not p.get("observed_at"):
                    raise ValueError("Observation needs name, source evidence and timestamp")
                identity = p["firm_id"] + "|" + p["source_url"].rstrip("/")
                key = hashlib.sha256(identity.encode()).hexdigest()[:20]
                if preserve_first_seen and re.fullmatch(r"[0-9a-f]{20}", str(p.get("id", ""))):
                    key = p["id"]
                previous = db.execute(
                    "SELECT * FROM profiles WHERE firm_id=? AND rtrim(source_url,'/')=rtrim(?, '/')",
                    (p["firm_id"], p["source_url"]),
                ).fetchone()
                if previous and previous["source_url"].rstrip("/") == p["source_url"].rstrip("/"):
                    p["source_url"] = previous["source_url"]
                if not previous:
                    case_aliases = db.execute(
                        "SELECT * FROM profiles WHERE firm_id=? AND lower(rtrim(source_url,'/'))=lower(rtrim(?, '/'))",
                        (p["firm_id"], p["source_url"]),
                    ).fetchall()
                    case_alias = next(
                        (
                            row
                            for row in case_aliases
                            if row["name"].casefold() == p["name"].casefold()
                        ),
                        None,
                    )
                    if case_alias:
                        previous = case_alias
                        p["source_url"] = case_alias["source_url"]
                if not previous and p.get("redirected_from"):
                    alias = db.execute(
                        "SELECT * FROM profiles WHERE firm_id=? AND rtrim(source_url,'/')=rtrim(?, '/')",
                        (p["firm_id"], p["redirected_from"]),
                    ).fetchone()
                    if alias and alias["name"].casefold() == p["name"].casefold():
                        previous = alias
                if previous:
                    key = previous["id"]
                first = (
                    previous["first_seen"]
                    if previous
                    else (
                        p.get("first_seen", p["observed_at"])
                        if preserve_first_seen
                        else p["observed_at"]
                    )
                )
                p.update(id=key, first_seen=first, last_seen=p["observed_at"])
                p.update(
                    office_status="current" if p.get("offices") else "unknown",
                    office_observed_at=p["observed_at"] if p.get("offices") else None,
                    office_content_hash=p["content_hash"] if p.get("offices") else None,
                )
                if preserve_first_seen:
                    for field in ("office_status", "office_observed_at", "office_content_hash"):
                        if field in original:
                            p[field] = original[field]
                if previous:
                    before = json.loads(previous["payload"])
                    if (
                        before.get("offices")
                        and not p.get("offices")
                        and before.get("extraction_version") == p.get("extraction_version")
                    ):
                        p.update(
                            offices=before["offices"],
                            office_status="last_known",
                            office_evidence=before.get("office_evidence", ""),
                            office_observed_at=before.get(
                                "office_observed_at", before["observed_at"]
                            ),
                            office_content_hash=before.get(
                                "office_content_hash", before["content_hash"]
                            ),
                        )
                    diff = {
                        f: {"before": before.get(f), "after": p.get(f)}
                        for f in FIELDS
                        if before.get(f) != p.get(f)
                    }
                    if diff and before.get("extraction_version") == p.get("extraction_version"):
                        event = dict(
                            profile_id=key,
                            name=p["name"],
                            firm_id=p["firm_id"],
                            kind="profile_changed",
                            changes=diff,
                            observed_at=p["observed_at"],
                            source_url=p["source_url"],
                            evidence_before=before["evidence"],
                            evidence_after=p["evidence"],
                        )
                        db.execute(
                            "INSERT INTO events(profile_id,firm_id,kind,observed_at,payload) VALUES(?,?,?,?,?)",
                            (
                                key,
                                p["firm_id"],
                                "profile_changed",
                                p["observed_at"],
                                json.dumps(event),
                            ),
                        )
                        totals["changed"] += 1
                    else:
                        totals["unchanged"] += 1
                else:
                    totals["baseline"] += 1
                search = " ".join(str(p.get(f, "")) for f in FIELDS).casefold()
                db.execute(
                    """INSERT INTO profiles VALUES(?,?,?,?,?,?,?,?)
                              ON CONFLICT(id) DO UPDATE SET name=excluded.name,source_url=excluded.source_url,
                              search_text=excluded.search_text,payload=excluded.payload,last_seen=excluded.last_seen""",
                    (
                        key,
                        p["firm_id"],
                        p["source_url"],
                        p["name"],
                        search,
                        json.dumps(p),
                        first,
                        p["observed_at"],
                    ),
                )
        return totals

    def search(self, q="", firm="", office="", practice="", page=1, page_size=25):
        # Filtering structured arrays in Python is intentional at MVP volume and keeps
        # exact office membership and literal Unicode search consistent across SQLite builds.
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM profiles ORDER BY name COLLATE NOCASE"
            ).fetchall()
        items = [json.loads(row[0]) for row in rows]
        items = [
            p
            for p in items
            if (not firm or p["firm_id"] == firm)
            and (not q or q.casefold() in " ".join(str(p.get(f, "")) for f in FIELDS).casefold())
            and (not office or office in p.get("offices", []))
            and (not practice or practice in p.get("practices", []))
        ]
        total = len(items)
        start = (max(1, page) - 1) * page_size
        return {"items": items[start : start + page_size], "total": total}

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM profiles WHERE id=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def events(self, firm="", limit=100):
        with self.connect() as db:
            rows = db.execute(
                'SELECT payload FROM events WHERE (?="" OR firm_id=?) ORDER BY id DESC LIMIT ?',
                (firm, firm, limit),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def flag_missing(self, key, message):
        """A failed source fetch is a review signal, never a departure assertion."""
        person = self.get(key)
        if not person:
            return
        with self.connect() as db:
            if db.execute(
                "SELECT 1 FROM events WHERE profile_id=? AND kind=?", (key, "source_unavailable")
            ).fetchone():
                return
            event = dict(
                profile_id=key,
                name=person["name"],
                firm_id=person["firm_id"],
                kind="source_unavailable",
                changes={},
                observed_at=utcnow(),
                source_url=person["source_url"],
                message=message,
            )
            db.execute(
                "INSERT INTO events(profile_id,firm_id,kind,observed_at,payload) VALUES(?,?,?,?,?)",
                (key, person["firm_id"], event["kind"], event["observed_at"], json.dumps(event)),
            )

    def start_run(self, firm):
        with self.connect() as db:
            return db.execute(
                "INSERT INTO runs(firm_id,started_at,status) VALUES(?,?,?)",
                (firm, utcnow(), "running"),
            ).lastrowid

    def finish_run(self, run, status, message, count):
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET finished_at=?,status=?,message=?,count=? WHERE id=?",
                (utcnow(), status, message, count, run),
            )

    def runs(self, limit=100):
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))
            ]

    def seed(self, path):
        with self.connect() as db:
            exists = db.execute("SELECT 1 FROM profiles LIMIT 1").fetchone()
        if not exists and Path(path).exists():
            self.observe(
                json.loads(Path(path).read_text(encoding="utf-8")), preserve_first_seen=True
            )
        history_path = Path(path).with_name("history.json")
        if history_path.exists():
            history = json.loads(history_path.read_text(encoding="utf-8"))
            with self.connect() as db:
                # Import history only into a clean database. Subsequent startup never
                # overwrites observations or appends duplicate historical rows.
                if (
                    not db.execute("SELECT 1 FROM runs LIMIT 1").fetchone()
                    and not db.execute("SELECT 1 FROM events LIMIT 1").fetchone()
                ):
                    for event in reversed(history.get("events", [])):
                        db.execute(
                            "INSERT INTO events(profile_id,firm_id,kind,observed_at,payload) VALUES(?,?,?,?,?)",
                            (
                                event["profile_id"],
                                event["firm_id"],
                                event["kind"],
                                event["observed_at"],
                                json.dumps(event),
                            ),
                        )
                    for run in reversed(history.get("runs", [])):
                        db.execute(
                            "INSERT INTO runs(firm_id,started_at,finished_at,status,message,count) VALUES(?,?,?,?,?,?)",
                            (
                                run["firm_id"],
                                run["started_at"],
                                run.get("finished_at"),
                                run["status"],
                                run["message"],
                                run["count"],
                            ),
                        )
