"""Exercise the release CLI against disposable source trees, never the live dataset."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release.py"
PREFIX = "pinpoint-partner-intelligence/"


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    files = {
        "README.md": "Run locally\n",
        "DESIGN.md": "Design",
        "UX-CONTRACT.md": "UX",
        "premium-ui.json": "{}",
        "pyproject.toml": "",
        "requirements.txt": "",
        "requirements.lock": "",
        ".gitignore": ".env\n",
        "pinpoint/web.py": "print('app')\n",
        "pinpoint/templates/home.html": "<h1>Hi</h1>",
        "pinpoint/static/style.css": "body {}",
        "pinpoint/static/app.js": "void 0;",
        "data/seed.json": "[]",
        "tests/test_app.py": "def test_ok(): pass",
        "scripts/smoke.py": "print('ok')",
        "docs/nested/NOTES.md": "Notes",
        ".github/workflows/test.yml": "name: Test",
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
    return root


def cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)], cwd=cwd, capture_output=True, text=True
    )


def test_packages_only_allowlisted_sources_and_independent_checksums(source):
    excluded = [
        ".env",
        ".git/config",
        ".venv/lib/module.py",
        ".firecrawl/page.html",
        "tmp/scratch.py",
        "data/raw/secret.json",
        "data/pinpoint.sqlite",
        "data/private.pdf",
        "pinpoint/__pycache__/cached.py",
        "pinpoint/.env",
        "pinpoint/tmp/private.py",
        "docs/cache/private.md",
        "tests/raw/page.html",
    ]
    for name in excluded:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("PRIVATE", encoding="utf-8")
    output = source / "output" / "release.zip"
    result = cli("--root", source, "--output", output)
    assert result.returncode == 0, result.stderr
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert PREFIX + "pinpoint/templates/home.html" in names
        assert PREFIX + "data/seed.json" in names
        assert PREFIX + "docs/nested/NOTES.md" in names
        assert all(PREFIX + name not in names for name in excluded)
        assert all(name.startswith(PREFIX) for name in names)
        manifest = json.loads(archive.read(PREFIX + "RELEASE-MANIFEST.json"))
        assert set(manifest["files"]) == {
            name[len(PREFIX) :] for name in names if name != PREFIX + "RELEASE-MANIFEST.json"
        }
        assert manifest["files"]["README.md"] == hashlib.sha256(b"Run locally\n").hexdigest()
    assert cli("--check", "--output", output).returncode == 0


def test_build_is_reproducible_and_relative_output_uses_working_directory(source, tmp_path):
    first = cli("--root", source, "--output", "first.zip", cwd=tmp_path)
    assert first.returncode == 0, first.stderr
    os.utime(source / "README.md", (1700000000, 1700000000))
    second = cli("--root", source, "--output", "second.zip", cwd=tmp_path)
    assert second.returncode == 0, second.stderr
    assert (tmp_path / "first.zip").read_bytes() == (tmp_path / "second.zip").read_bytes()


@pytest.mark.parametrize(
    "member",
    [
        "../escape.py",
        "/absolute.py",
        PREFIX + "../escape.py",
        PREFIX + "docs\\escape.md",
        PREFIX + "data/raw/secret.json",
        PREFIX + "C:/secret.py",
    ],
)
def test_check_rejects_unsafe_or_unallowlisted_archive_members(tmp_path, member):
    output = tmp_path / "bad.zip"
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(member, "secret")
    assert cli("--check", "--output", output).returncode != 0


def test_check_detects_tampered_content_and_does_not_rebuild(source, tmp_path):
    output = tmp_path / "release.zip"
    result = cli("--root", source, "--output", output)
    assert result.returncode == 0, result.stderr
    with zipfile.ZipFile(output) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    files[PREFIX + "README.md"] = b"tampered"
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    before = output.read_bytes()
    assert cli("--check", "--root", tmp_path / "missing", "--output", output).returncode != 0
    assert output.read_bytes() == before


def test_check_rejects_paths_that_collide_on_windows(source, tmp_path):
    output = tmp_path / "collision.zip"
    assert cli("--root", source, "--output", output).returncode == 0
    with zipfile.ZipFile(output) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    extra = "pinpoint/WEB.py"
    files[PREFIX + extra] = b'print("different")'
    manifest = json.loads(files[PREFIX + "RELEASE-MANIFEST.json"])
    manifest["files"][extra] = hashlib.sha256(files[PREFIX + extra]).hexdigest()
    files[PREFIX + "RELEASE-MANIFEST.json"] = json.dumps(manifest).encode()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    assert cli("--check", "--output", output).returncode != 0


def test_missing_source_fails_without_replacing_existing_output(tmp_path):
    output = tmp_path / "release.zip"
    output.write_bytes(b"keep me")
    assert cli("--root", tmp_path / "missing", "--output", output).returncode != 0
    assert output.read_bytes() == b"keep me"


def test_incomplete_source_cannot_replace_existing_release(source, tmp_path):
    (source / "requirements.lock").unlink()
    output = tmp_path / "release.zip"
    output.write_bytes(b"previous release")
    result = cli("--root", source, "--output", output)
    assert result.returncode != 0
    assert "requirements.lock" in result.stderr
    assert output.read_bytes() == b"previous release"


def test_check_rejects_duplicate_members(source, tmp_path):
    output = tmp_path / "release.zip"
    assert cli("--root", source, "--output", output).returncode == 0
    with zipfile.ZipFile(output, "a") as archive:
        with pytest.warns(UserWarning, match="Duplicate"):
            archive.writestr(PREFIX + "README.md", "second copy")
    result = cli("--check", "--output", output)
    assert result.returncode != 0
    assert "Duplicate" in result.stderr


def test_selected_symlink_is_rejected_instead_of_leaking_external_file(source, tmp_path):
    external = tmp_path / "private.py"
    external.write_text("secret")
    link = source / "pinpoint" / "linked.py"
    try:
        link.symlink_to(external)
    except OSError:
        pytest.skip("Creating symlinks requires Windows developer mode or privilege")
    assert cli("--root", source, "--output", tmp_path / "release.zip").returncode != 0
