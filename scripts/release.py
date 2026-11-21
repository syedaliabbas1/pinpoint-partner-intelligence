"""Build or verify a deterministic, allowlisted source ZIP using only the stdlib."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import zipfile


PREFIX = "pinpoint-partner-intelligence/"
MANIFEST = "RELEASE-MANIFEST.json"
REQUIRED = {
    "README.md",
    "DESIGN.md",
    "UX-CONTRACT.md",
    "premium-ui.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements.lock",
    ".gitignore",
}
EXCLUDED_PARTS = {
    "__pycache__",
    ".git",
    ".venv",
    ".env",
    ".firecrawl",
    "tmp",
    "cache",
    "raw",
    "snapshots",
    "secrets",
    ".pytest_cache",
    ".ruff_cache",
}


def allowed(name: str) -> bool:
    """Reject ambiguous/external paths before evaluating the explicit source allowlist."""
    if "\\" in name or ":" in name or "\x00" in name:
        return False
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    if any(part.casefold() in EXCLUDED_PARTS for part in parts):
        return False
    if name in REQUIRED:
        return True
    path = PurePosixPath(name)
    if parts[0] == "pinpoint" and len(parts) >= 2:
        return path.suffix in {".py", ".html", ".css", ".js"}
    if parts[0] == "data" and len(parts) == 2:
        return path.suffix == ".json"
    if parts[0] in {"tests", "scripts"} and len(parts) == 2:
        return path.suffix == ".py"
    if parts[0] == "docs" and len(parts) >= 2:
        return path.suffix == ".md"
    return len(parts) == 3 and parts[:2] == [".github", "workflows"] and path.suffix == ".yml"


def verify(output: Path) -> int:
    """Check paths, exact manifest membership and every file's SHA-256, without extracting."""
    with zipfile.ZipFile(output) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive member")
        if len(names) != len({name.casefold() for name in names}):
            raise ValueError("Case-insensitive archive path collision")
        for entry in entries:
            name = entry.filename
            if not name.startswith(PREFIX):
                raise ValueError(f"Unexpected archive root: {name}")
            relative = name[len(PREFIX) :]
            if relative != MANIFEST and not allowed(relative):
                raise ValueError(f"Unsafe or excluded archive path: {name}")
            if entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError(f"Unexpected directory or symlink: {name}")
        manifest = json.loads(archive.read(PREFIX + MANIFEST))
        hashes = manifest["files"]
        expected = {name[len(PREFIX) :] for name in names if name != PREFIX + MANIFEST}
        if manifest.get("format") != 1 or not isinstance(hashes, dict) or set(hashes) != expected:
            raise ValueError("Manifest membership mismatch")
        if not REQUIRED.issubset(expected):
            raise ValueError("Release is missing required root files")
        for name, digest in hashes.items():
            if hashlib.sha256(archive.read(PREFIX + name)).hexdigest() != digest:
                raise ValueError(f"Checksum mismatch: {name}")
        return len(hashes)


def build(root: Path, output: Path) -> int:
    if not root.is_dir():
        raise ValueError(f"Source root is not a directory: {root}")
    if output.suffix.casefold() != ".zip":
        raise ValueError("Output must have a .zip suffix")
    files = {}

    def reject_link(path: Path) -> None:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        if path.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError(f"Source symlink/junction is not permitted: {path.relative_to(root)}")

    # Prune before descending: excluded environments/raw captures may be large or private.
    for directory, subdirs, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        relative_dir = current.relative_to(root).as_posix()
        if relative_dir == ".":
            subdirs[:] = [
                name
                for name in subdirs
                if name in {"pinpoint", "data", "docs", "tests", "scripts", ".github"}
            ]
        elif relative_dir in {"data", "tests", "scripts", ".github/workflows"}:
            subdirs[:] = []
        elif relative_dir == ".github":
            subdirs[:] = [name for name in subdirs if name == "workflows"]
        subdirs[:] = [name for name in subdirs if name.casefold() not in EXCLUDED_PARTS]
        for name in subdirs:
            reject_link(current / name)
        for name in sorted(filenames):
            path = current / name
            relative = path.relative_to(root).as_posix()
            if not allowed(relative):
                continue
            reject_link(path)
            if not path.resolve().is_relative_to(root):
                raise ValueError(f"Source escapes root: {relative}")
            if path.resolve() == output:
                raise ValueError("Output would overwrite an included source")
            files[relative] = path.read_bytes()
    if not REQUIRED.issubset(files):
        raise ValueError(
            "Missing required source files: " + ", ".join(sorted(REQUIRED - files.keys()))
        )
    manifest = {
        "format": 1,
        "files": {
            name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())
        },
    }
    files[MANIFEST] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Write and verify a sibling first; failed builds leave an existing release intact.
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, content in sorted(files.items()):
                entry = zipfile.ZipInfo(PREFIX + name, date_time=(2020, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = (stat.S_IFREG | 0o644) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, content, compresslevel=9)
        count = verify(temporary)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Source tree (default: repository containing this script)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/pinpoint-partner-intelligence.zip"),
        help="ZIP path, relative to the current working directory",
    )
    parser.add_argument(
        "--check", action="store_true", help="Verify existing ZIP without rebuilding"
    )
    args = parser.parse_args()
    try:
        output = args.output.resolve()
        count = verify(output) if args.check else build(args.root.resolve(), output)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError) as error:
        print(f"Release failed: {error}", file=sys.stderr)
        return 1
    print(f"{'Verified' if args.check else 'Built'} {output} ({count} source files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
