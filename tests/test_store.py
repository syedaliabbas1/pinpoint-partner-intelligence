import sqlite3

import pytest

from pinpoint.store import Store


def test_same_name_case_variant_source_does_not_duplicate_a_person(tmp_path):
    db = Store(tmp_path / "case-alias.sqlite")
    first = dict(person(), firm_id="king", source_url="https://www.kslaw.com/People/Will-Jordan")
    db.observe([first])
    identity = db.search()["items"][0]["id"]
    db.observe([dict(first, source_url="https://www.kslaw.com/people/will-jordan")])
    assert db.search()["total"] == 1
    assert db.get(identity)["source_url"] == first["source_url"]
    assert db.events() == []


def test_case_sensitive_paths_with_different_names_are_not_merged(tmp_path):
    db = Store(tmp_path / "different-people.sqlite")
    first = dict(person(), source_url="https://www.wlrk.com/attorney/Example")
    db.observe(
        [
            first,
            dict(
                first, source_url="https://www.wlrk.com/attorney/example", name="Different Person"
            ),
        ]
    )
    assert db.search()["total"] == 2


def test_matching_name_is_found_among_multiple_case_distinct_paths(tmp_path):
    db = Store(tmp_path / "multiple-aliases.sqlite")
    first = dict(person(), name="Alice Example", source_url="https://www.wlrk.com/attorney/Example")
    bob = dict(first, name="Bob Example", source_url="https://www.wlrk.com/attorney/example")
    db.observe([first, bob])
    db.observe([dict(bob, source_url="https://www.wlrk.com/attorney/EXAMPLE")])
    assert db.search()["total"] == 2


def test_trailing_slash_only_difference_is_not_a_profile_change(tmp_path):
    db = Store(tmp_path / "slash.sqlite")
    row = person()
    db.observe([row])
    db.observe([dict(row, source_url=row["source_url"].rstrip("/"))])
    assert db.search()["total"] == 1
    assert db.events() == []


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.sqlite")


def person(**changes):
    return dict(
        firm_id="wachtell",
        source_url="https://www.wlrk.com/attorneys/jane-example/",
        name="Jane Example",
        title="Partner",
        practices=["Mergers & Acquisitions"],
        offices=["New York"],
        summary="Jane is a partner in the M&A practice.",
        evidence="Jane Example Partner Mergers & Acquisitions New York",
        content_hash="abc",
        observed_at="2026-11-21T12:00:00+00:00",
        **changes,
    )


def test_baseline_is_not_a_market_move(store):
    store.observe([person()])
    assert len(store.search()["items"]) == 1
    assert store.events() == []


def test_identical_refresh_is_idempotent(store):
    store.observe([person()])
    store.observe([person()])
    assert store.search()["total"] == 1
    assert not store.events()


def test_field_change_has_before_and_after_evidence(store):
    store.observe([person()])
    changed = person()
    changed.update(offices=["London"], observed_at="2026-11-22T12:00:00+00:00")
    store.observe([changed])
    event = store.events()[0]
    assert event["kind"] == "profile_changed"
    assert event["changes"]["offices"] == {"before": ["New York"], "after": ["London"]}
    assert event["source_url"] == changed["source_url"]


def test_empty_observation_retains_last_known_people(store):
    store.observe([person()])
    store.observe([])
    assert store.search()["total"] == 1
    assert not store.events()


def test_search_is_literal_parameterized_and_filters_are_combined(store):
    row = person()
    row["name"] = "Jo O'Brien_100%"
    store.observe([row])
    assert store.search(q="O'Brien", firm="wachtell", office="New York")["total"] == 1
    assert store.search(q="' OR 1=1 --")["total"] == 0
    assert store.search(q="%")["total"] == 1
    assert store.search(q="Missing", firm="wachtell")["total"] == 0


def test_firm_scoped_identity_does_not_merge_names(store):
    row = person()
    other = dict(
        row, firm_id="kirkland", source_url="https://www.kirkland.com/lawyers/j/jane-example"
    )
    store.observe([row, other])
    assert store.search()["total"] == 2


def test_run_failure_does_not_touch_profiles(store):
    store.observe([person()])
    run = store.start_run("wachtell")
    store.finish_run(run, "blocked", "HTTP 403; retained last-known data", 0)
    assert store.search()["total"] == 1
    assert store.runs()[0]["status"] == "blocked"


def test_transaction_rolls_back_partial_invalid_batch(store):
    bad = person()
    bad["name"] = None
    with pytest.raises((ValueError, sqlite3.IntegrityError)):
        store.observe([person(), bad])
    assert store.search()["total"] == 0


def test_seed_restores_history_once_on_a_clean_checkout(tmp_path):
    import json

    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps([person()]))
    history = {
        "events": [
            {
                "profile_id": "test",
                "firm_id": "wachtell",
                "kind": "source_unavailable",
                "observed_at": "2026-11-22",
                "name": "Jane",
                "changes": {},
            }
        ],
        "runs": [
            {
                "firm_id": "wachtell",
                "started_at": "2026-11-21",
                "finished_at": "2026-11-21",
                "status": "partial",
                "message": "Test fixture",
                "count": 1,
            }
        ],
    }
    (tmp_path / "history.json").write_text(json.dumps(history))
    db = Store(tmp_path / "fresh.sqlite")
    db.seed(seed)
    db.seed(seed)
    assert len(db.runs()) == 1
    assert len(db.events()) == 1


def test_extractor_version_change_does_not_create_market_change(store):
    p = dict(person(), extraction_version="1")
    store.observe([p])
    p.update(extraction_version="2", offices=[])
    store.observe([p])
    assert store.events() == []
    assert store.search()["items"][0]["offices"] == []


def test_missing_office_keeps_labelled_last_known_evidence(store):
    original = dict(person(), extraction_version="2", office_evidence="New York")
    store.observe([original])
    updated = dict(original, offices=[], office_evidence="", observed_at="2026-11-22T12:00:00Z")
    store.observe([updated])
    p = store.search()["items"][0]
    assert store.events() == []
    assert p["offices"] == ["New York"]
    assert p["office_status"] == "last_known"
    assert p["office_observed_at"] == original["observed_at"]
    assert p["office_evidence"] == "New York"


def test_seed_preserves_original_first_observation(tmp_path):
    import json

    row = person()
    row["first_seen"] = "2026-11-01T12:00:00+00:00"
    path = tmp_path / "seed.json"
    path.write_text(json.dumps([row]))
    store = Store(tmp_path / "seed.sqlite")
    store.seed(path)
    assert store.search()["items"][0]["first_seen"] == row["first_seen"]


def test_verified_same_name_redirect_preserves_identity_and_history(store):
    row = person()
    store.observe([row])
    before = store.search()["items"][0]
    changed = dict(
        row,
        source_url="https://www.wlrk.com/attorneys/jane-new/",
        redirected_from=row["source_url"],
        observed_at="2026-11-22T12:00:00Z",
    )
    store.observe([changed])
    store.observe([changed])
    after = store.search()["items"][0]
    assert store.search()["total"] == 1
    assert after["id"] == before["id"]
    assert after["first_seen"] == before["first_seen"]
    assert after["source_url"] == changed["source_url"]
    assert len(store.events()) == 1


def test_seed_preserves_last_known_office_metadata(tmp_path):
    import json

    row = dict(
        person(),
        office_status="last_known",
        office_observed_at="2026-11-01T12:00:00Z",
        office_content_hash="older",
    )
    path = tmp_path / "seed.json"
    path.write_text(json.dumps([row]))
    store = Store(tmp_path / "last-known.sqlite")
    store.seed(path)
    restored = store.search()["items"][0]
    assert restored["office_status"] == "last_known"
    assert restored["office_observed_at"] == row["office_observed_at"]


def test_redirect_identity_survives_portable_export_import(store, tmp_path):
    import json

    row = person()
    store.observe([row])
    store.observe(
        [
            dict(
                row,
                source_url="https://www.wlrk.com/attorneys/jane-new/",
                redirected_from=row["source_url"],
            )
        ]
    )
    original = store.search()["items"][0]
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps([original]))
    restored = Store(tmp_path / "restored.sqlite")
    restored.seed(seed)
    assert restored.get(original["id"]) is not None
