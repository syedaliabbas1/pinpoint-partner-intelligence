import json

from pinpoint.validation import validate_seed
from tests.test_store import person


def test_portable_seed_rejects_unknown_firm_host_and_missing_evidence(tmp_path):
    row = person()
    row.update(
        firm_id="unknown", source_url="https://evil.example/", content_hash="bad", evidence=""
    )
    path = tmp_path / "seed.json"
    path.write_text(json.dumps([row]))
    assert len(validate_seed(path)) >= 3


def test_supplied_baseline_passes_provenance_checks():
    from pinpoint.config import ROOT

    assert validate_seed(ROOT / "data/seed.json") == []
