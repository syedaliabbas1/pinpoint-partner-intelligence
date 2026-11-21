"""Offline provenance checks for the portable evidence baseline."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pinpoint.config import FIRMS
from pinpoint.extract import is_profile_url


def validate_seed(path):
    errors = []
    try:
        people = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"Unable to read baseline: {exc}"]
    if not isinstance(people, list):
        return ["Baseline must be a JSON array"]
    seen = set()
    for index, p in enumerate(people):
        label = f"Profile {index + 1}"
        if not isinstance(p, dict):
            errors.append(label + ": not an object")
            continue
        firm = p.get("firm_id")
        url = p.get("source_url", "")
        if firm not in FIRMS:
            errors.append(label + ": unknown firm")
        elif not isinstance(url, str) or not is_profile_url(firm, url):
            errors.append(label + ": source must be an allowlisted official profile")
        identity = (firm, str(url).rstrip("/"))
        if identity in seen:
            errors.append(label + ": duplicate identity")
        seen.add(identity)
        for key in ["name", "evidence", "observed_at"]:
            if not isinstance(p.get(key), str) or not p[key].strip():
                errors.append(label + ": missing " + key)
        if p.get("title") != "Partner":
            errors.append(label + ": partner title is required")
        if not p.get("practices") or not isinstance(p["practices"], list):
            errors.append(label + ": practice evidence is required")
        if not isinstance(p.get("offices"), list):
            errors.append(label + ": offices must be an array, empty when unknown")
        if not re.fullmatch(r"[0-9a-f]{64}", str(p.get("content_hash", ""))):
            errors.append(label + ": missing SHA-256 content hash")
        try:
            stamp = datetime.fromisoformat(p.get("observed_at", "").replace("Z", "+00:00"))
            if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
                errors.append(label + ": observation must be a past timezone-aware timestamp")
        except (ValueError, TypeError):
            errors.append(label + ": invalid observation timestamp")
    return errors
