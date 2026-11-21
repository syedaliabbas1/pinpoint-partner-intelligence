"""Local-only data operations. Run: python -m pinpoint.cli --help."""

import argparse
import json
import os
from pathlib import Path

from pinpoint.collect import AccessError, RefreshLock, refresh_firm
from pinpoint.config import FIRMS, ROOT, utcnow
from pinpoint.store import Store


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", default=os.getenv("PINPOINT_DB", str(ROOT / "data/pinpoint.sqlite"))
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create database and load the supplied evidence baseline")
    refresh = commands.add_parser(
        "refresh", help="Refresh allowed official profiles; never claim complete coverage"
    )
    refresh.add_argument("--firm", choices=list(FIRMS))
    refresh.add_argument("--max-profiles", type=int, default=15)
    refresh.add_argument(
        "--export", action="store_true", help="Update portable baseline/state after the run"
    )
    commands.add_parser("coverage", help="Print actual captured counts and last run per firm")
    commands.add_parser(
        "export", help="Export portable baseline and history for reproducible startup"
    )
    commands.add_parser("validate", help="Check portable baseline provenance offline")
    args = parser.parse_args()
    if args.command == "validate":
        from pinpoint.validation import validate_seed

        errors = validate_seed(ROOT / "data/seed.json")
        if errors:
            raise SystemExit("\n".join(errors))
        print(
            "Portable baseline provenance checks passed. This does not prove complete coverage or current source accuracy."
        )
        return
    store = Store(args.db)
    store.seed(ROOT / "data/seed.json")
    if args.command == "refresh":
        if not 1 <= args.max_profiles <= 500:
            parser.error("--max-profiles must be between 1 and 500")
        with RefreshLock(Path(args.db).with_suffix(".refresh.lock")):
            for firm_id in [args.firm] if args.firm else FIRMS:
                result = refresh_firm(store, firm_id, args.max_profiles)
                print(json.dumps(result, ensure_ascii=False), flush=True)
            if args.export:
                export(store)
    elif args.command == "export":
        export(store)
    elif args.command == "coverage":
        print(json.dumps(coverage(store), ensure_ascii=False, indent=2))
    else:
        print("Database ready:", args.db)


def coverage(store):
    runs = store.runs(limit=10000)
    result = []
    for firm_id, firm in FIRMS.items():
        people = store.search(firm=firm_id, page_size=100000)["items"]
        last = next((r for r in runs if r["firm_id"] == firm_id), None)
        result.append(
            dict(
                firm_id=firm_id,
                name=firm["name"],
                captured=len(people),
                completeness="unverified",
                last_run=last,
                latest_observation=max((p["last_seen"] for p in people), default=None),
            )
        )
    return result


def export(store):
    atomic_json(ROOT / "data/seed.json", store.search(page_size=100000)["items"])
    atomic_json(ROOT / "data/coverage.json", {"exported_at": utcnow(), "firms": coverage(store)})
    atomic_json(
        ROOT / "data/history.json",
        {"events": store.events(limit=100000), "runs": store.runs(limit=100000)},
    )
    print("Exported evidence baseline, coverage and history.")


if __name__ == "__main__":
    try:
        main()
    except AccessError as exc:
        raise SystemExit(str(exc)) from exc
