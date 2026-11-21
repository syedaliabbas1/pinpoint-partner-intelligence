# Partner intelligence implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task.

**Goal:** Give legal recruiters searchable, evidenced corporate/M&A partner profiles, truthful coverage and repeatable refreshes across the assessment's 15 firms.

**Architecture:** One FastAPI application renders Jinja templates. SQLite holds profiles, field-level change events and run history; a bounded CLI collector checks robots policies, extracts official pages, and preserves evidence. Read-only UI plus local CLI writes avoids exposing a crawler to arbitrary web requests.

**Tech stack:** Python 3.11+, FastAPI, Jinja2, SQLite, httpx, BeautifulSoup, pytest, Ruff. No required API credentials.

**Spec:** `Pinpoint_Partners_CTO_Technical_Assessment.pdf`, supported by the job specification. The requested Markdown file was absent; the user pointed back to the assessment PDF after being asked for its path.

## Global constraints
- No more than about six hours; record measured elapsed time, not a fabricated human effort estimate.
- Exactly the specified 15 firms in the coverage registry. Global scope; never infer practice coverage from a small sample.
- Respect robots policies, stop on access denials/challenges, no proxy evasion or private contact enrichment.
- Every profile has an official URL, retrieval timestamp, excerpt and hash. Unknown fields stay unknown.
- Initial observations are a baseline; missing pages are review signals, never automatically confirmed moves.
- Runs are idempotent; failures retain last-known records and do not manufacture deletion events.
- Local application and GitHub publishing instructions; do not publish or submit on the user's behalf.

## Review focus
- Empty/blocked directory must not delete existing people or claim completeness.
- Names containing quotes, accents and SQL metacharacters must remain safe/searchable.
- Page template drift or challenge HTML must fail conservatively.
- CSV cells beginning with formula characters must be escaped.
- Refresh interruption/concurrent execution must leave a usable database and release its lock.

## Tasks
### Task 1: Registry, evidence model and storage
Files: `pinpoint/config.py`, `pinpoint/store.py`, `tests/test_store.py`, `data/sources.json`.
- [x] Test baseline/idempotence, actual field changes, failure retention, firm-scoped identities and literal searches against temporary SQLite.
- [x] Implement transactional observations, run summaries, schema initialization and seed loading.
- [x] Run `python -m pytest tests/test_store.py -q`.

### Task 2: Responsible collection and real data
Files: `pinpoint/collect.py`, `pinpoint/extract.py`, `pinpoint/cli.py`, `tests/test_collect.py`, `tests/test_extract.py`, `data/seed.json`, `data/coverage.json`.
- [x] Test robots disallow/fail-closed, host allowlisting, redirects, profile classification, normalisation, changed/missing evidence and lock handling.
- [x] Implement bounded per-host pacing, timeout, response limits, snapshots, profile extraction, review-only missing alerts and `refresh` / `coverage` CLI.
- [x] Inspect each firm's robots and directories. Collect only evidenced, allowed official profiles; report blocked/partial/not collected states with reasons.
- [x] Run fixture tests offline and two real observation passes; inspect actual source fields before accepting seed records.

### Task 3: Recruiter workflow
Files: `pinpoint/web.py`, `pinpoint/templates/`, `pinpoint/static/`, `tests/test_web.py`, `DESIGN.md`, `UX-CONTRACT.md`.
- [x] Test search/filter/pagination, profile source evidence, coverage/history pages, 404s, CSV safety and empty states through TestClient.
- [x] Implement directory, profile call brief, change feed and coverage/run history with one shared navigation/layout.
- [x] Run the suite and start uvicorn; verify actual HTTP and browser behaviour at desktop/mobile widths.

### Task 4: Scheduling, delivery and verification
Files: `.github/workflows/`, `README.md`, `docs/VERIFICATION.md`, `docs/DATA.md`.
- [x] Add weekly/manual refresh workflow with persisted reviewed seed and offline test CI; document local scheduler alternative.
- [x] Document choices, rejected alternatives, exact setup/test commands, actual coverage, privacy/access policy, scaling, omissions, measured time and submission checklist.
- [x] Run complete pytest suite, Ruff, compile, seed validation, live HTTP smoke and UI audit. Review correctness and fix material findings.
- [x] Keep local source ready for user review and GitHub publication; report actual checks and remaining limits.

## Execution record
- Tasks 1-3 implemented and verified with offline tests and actual HTTP requests. The source dataset contains 54 real profiles across 11 firms; 3 are explicitly adjacent M&A litigation profiles. All 15 firm states are reported.
- Second live pass: all 54 current profiles accepted; no normalised field changes or duplicate baselines. Current snapshot hashes checked against their saved bytes.
- Independent offline code review identified first-seen/identity import, missing-office, Corporate Tax, alias and newline issues; covered by failing regression tests and fixed. Ctrl-C run bookkeeping also fixed.
- Fresh-source tests exposed a missing pytest temporary-parent directory assumption. Using a direct workspace temporary directory resolved it.
- Ruling: browser runtime QA could not be completed because the browser host was unavailable; an unrelated private browser window was not inspected after automatic approval rejected that action. Actual HTTP and static checks are recorded separately. Manual visual/keyboard/print review remains.
- Ruling: weekly GitHub refresh is supplied as configuration; no workflow execution, repository publication, messages or submission were performed.
- Ruling: the missing Markdown instruction file could not be recovered; after clarification the user pointed to the primary assessment PDF, which governed scope.
- Task 4 documentation and final verification results are in docs/VERIFICATION.md and docs/TIME.md.
