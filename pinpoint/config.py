import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))
FIRMS = {firm["id"]: firm for firm in SOURCES}
USER_AGENT = "PinpointResearch/0.1 (public professional directory research; local assessment)"


def utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
