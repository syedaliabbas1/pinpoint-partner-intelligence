# Build and share the assessment

Run these commands from the repository root using Python 3.11 or 3.12. Packaging uses the Python standard library and needs no installed application dependencies or network access. Finish data exports and documentation edits before building; the ZIP is a snapshot of file bytes at build time.

## Build and verify

```powershell
python scripts/release.py --output output/pinpoint-partner-intelligence.zip
python scripts/release.py --check --output output/pinpoint-partner-intelligence.zip
Get-FileHash output/pinpoint-partner-intelligence.zip -Algorithm SHA256
```

On macOS/Linux use `python3` and `sha256sum output/pinpoint-partner-intelligence.zip` (or `shasum -a 256` on macOS). `--root PATH` selects another source tree; otherwise the script uses its own repository root. Relative output paths resolve from the shell's current directory. `--check` reads the existing archive without rebuilding or consulting the source tree.

The ZIP contains one top folder, `pinpoint-partner-intelligence/`, and a generated `RELEASE-MANIFEST.json` mapping every included source path to its SHA-256 checksum. The manifest lives inside the ZIP only. Verification rejects unexpected paths, duplicate entries, symlinks, missing required root files, missing/extra manifest entries and checksum mismatches. This detects corruption; it is not a cryptographic signature or a claim of authorship. Send the whole-ZIP hash separately if the recipient needs to compare the downloaded bytes.

File order, archive timestamps and permissions are fixed. Identical source bytes produce identical ZIP bytes in the same Python/zlib environment; compression-library changes can change ZIP bytes between environments. Existing releases are replaced only after the new archive passes verification.

The explicit inclusion rules are:

- Root files: `README.md`, `DESIGN.md`, `UX-CONTRACT.md`, `premium-ui.json`, `pyproject.toml`, `requirements.txt`, `requirements.lock`, `.gitignore`.
- Python, HTML, CSS and JavaScript under `pinpoint/`.
- Direct `data/*.json`, `tests/*.py`, `scripts/*.py` and `.github/workflows/*.yml` files.
- Markdown under `docs/`.

Raw captures, snapshots, caches, scratch folders, secrets folders, `.env`, `.git`, `.venv`, `.firecrawl`, PDFs and SQLite databases are excluded. Directory symlinks/junctions and selected file symlinks are rejected. The output ZIP cannot include itself. The allowlist is structural: review the permitted source and JSON content before sharing, because a credential pasted into an otherwise allowed file would still be included. The JSON baseline contains real public professional information and short source excerpts.

## Extract and run a clean copy

Extract into a new empty destination so old files cannot be confused with this release.

Windows PowerShell:

```powershell
Expand-Archive -LiteralPath output/pinpoint-partner-intelligence.zip -DestinationPath output/reviewer-copy
Set-Location output/reviewer-copy/pinpoint-partner-intelligence
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pinpoint.cli init
.venv\Scripts\python.exe -m pinpoint.cli validate
.venv\Scripts\python.exe -m uvicorn pinpoint.web:app --host 127.0.0.1 --port 8000
```

macOS/Linux:

```bash
unzip output/pinpoint-partner-intelligence.zip -d output/reviewer-copy
cd output/reviewer-copy/pinpoint-partner-intelligence
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pytest
.venv/bin/python -m pinpoint.cli init
.venv/bin/python -m pinpoint.cli validate
.venv/bin/python -m uvicorn pinpoint.web:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and stop with Ctrl-C. Initial dependency installation needs internet access; the bundled data and offline tests need no API credentials or law-firm access. The database is recreated locally from portable JSON. Read `README.md` for coverage boundaries, refresh behaviour and application limitations. Package verification does not replace running the tests or inspecting the app.

## Deliver the files or publish a repository

Share `output/pinpoint-partner-intelligence.zip` through the assessment's agreed transfer channel, with its SHA-256 and the README's run instructions. Confirm reviewer access and submission arrangements. Building the archive does not upload, email, deploy or submit anything.

If a GitHub repository is required, publish the extracted clean copy to an empty repository you control. The extracted tree deliberately contains no Git metadata. Prefer private visibility while reviewing the public-profile data, then grant the reviewer access. In that clean copy, after testing:

```bash
git init -b main
git status --short
git add README.md DESIGN.md UX-CONTRACT.md premium-ui.json pyproject.toml requirements.txt requirements.lock .gitignore pinpoint data tests scripts docs .github
git diff --cached --stat
git diff --cached --name-only
git commit -m "Build source-backed partner intelligence MVP"
git remote add origin https://github.com/YOUR_USERNAME/pinpoint-partner-intelligence.git
git push -u origin main
```

Use your own repository URL and Git author identity. Review staged files before committing, and authenticate through your normal GitHub mechanism; never put credentials in source files. The generated release manifest need not be committed. Check the remote repository and Tests workflow, grant reviewer access, then manually exercise the refresh workflow and inspect its artifact before relying on the schedule.

GitHub authentication was verified with network access during finalization. The private source repository is https://github.com/syedaliabbas1/pinpoint-partner-intelligence. Reviewers need repository access before they can use that link. The verified ZIP is an additional portable option. Publication and actual workflow results are recorded in docs/VERIFICATION.md; no assessment email or reviewer invitation is sent automatically.
