# Verification record

Executed locally on Windows, Python 3.11.9, on 21 November 2026. This record distinguishes executed checks from supplied configuration and manual checks that remain.

## Executed checks

| Check | Actual result |
|---|---|
| `python -m pytest -q` | Initial build: 52 passed. Finalization results are recorded below. |
| `python -m ruff check pinpoint tests scripts` | All checks passed |
| `python -m ruff format --check pinpoint tests scripts` | All application/test/helper files formatted |
| `python -m compileall -q pinpoint scripts` | Exit 0 |
| `python -m pip check` | No broken requirements |
| `python -m pinpoint.cli validate` | Portable baseline provenance checks passed |
| New virtual environment + `pip install -r requirements.lock` | Installation succeeded from the locked dependency set |
| Fresh source/data copy without SQLite | Database initialised from portable seed/history; test suite passed |
| Uvicorn + `python scripts/smoke.py --base http://127.0.0.1:8001` | Directory, coverage, changes, health, API, local assets and all 54 detail routes returned 200; no-results, CSV, 422 and 404 states checked |
| Premium UI static audit, configured to application sources | 0 errors, 0 unresolved findings, 0 warnings; does not verify a browser |
| Official `designmd lint DESIGN.md` | 0 errors; 6 unused-component-token warnings (tokens are consumed by runtime CSS); no unsupported schema token remains |
| Actual second official-source observation pass | All 54 accepted profiles fetched again under per-path robots checks; 0 normalised field changes and 0 new baseline identities |
| Snapshot integrity | All 54 current profile hashes matched the stored UTF-8 snapshot bytes |

See the latest test output if subsequently changing source or data. No line-coverage percentage, accessibility certification, deployed-service health or GitHub CI success is claimed.

## What the tests exercise

- Atomic observations and rollback; baseline versus change semantics; idempotent updates.
- Literal Unicode/casefold filtering and safe handling of apostrophes and SQL metacharacters.
- Source evidence, role/practice acceptance, navigation/card exclusion, header variants, HTML comments, M&A litigation taxonomy and tax-only exclusions.
- Office extraction from contact elements, street-address false positives, last-known field evidence and freshness persistence.
- Fail-closed robots handling; missing-policy semantics; HTTPS host allowlists; external and disallowed redirects; separately allowed profile paths behind a disallowed listing path.
- Response streaming and byte-preserving snapshot hashes; source URL redirect identity.
- Refresh lifecycle: baseline, identical repeat, field change, unavailable source retention and review event deduplication.
- First-observed timestamps, stable redirected identities, field freshness and history surviving portable export/import.
- Concurrent lock rejection, lock release on exception, ordinary keyboard interruption status.
- TestClient routes, source links, HTML escaping, filtered/formula-safe CSV, bounded query parameters, empty/no-results states and owned 404/422 handling.

## Real data observations

Initial build baseline: **54 official-source profiles, 11 firms represented, 3 adjacent M&A litigation profiles, 0 firms certified globally complete**. The current curated baseline is 168, described below. The accepted sample was revisited in a second live pass. Its lack of changes over a short interval is an idempotence observation, not evidence that the market has not moved.

Wachtell's directory returned 403; Davis Polk and Gibson Dunn's collector robots requests returned 403; Paul Hastings's robots request returned 429. Those four were not retried through other transports or identities. Their zero counts remain visible. Initial reconnaissance and collector HTTP responses sometimes differed; collector decisions follow the actual response to its own request.

Two initial guessed directory routes were corrected using links in the firms' own profile-page navigation. Sullivan & Cromwell's `/LawyerListing` was retrieved successfully. Cravath's actual `/people/index.html` path is disallowed by robots, so it was not requested; its separately allowed known profiles were refreshed. All-profile discovery remains unfinished.

Current live-run details and timestamps are preserved in `data/history.json` and `data/coverage.json`. The release history contains no fabricated move events. Development false positives were investigated against cached real HTML, pinned in regression fixtures and corrected before the release seed. Synthetic Jane Example data is confined to tests.

## Independent review and fixes

One independent, read-only offline reviewer inspected code, tests, workflows and saved source evidence. No Critical findings. Important findings were fixed with reproducing tests:

1. Export/import lost first-observed timestamps: seed import now preserves them.
2. Missing office extraction created a false removal: prior office evidence remains explicitly last known, with its own timestamp/hash.
3. Corporate Tax was misclassified as Corporate: narrower scope checks exclude the concrete false positive.
4. Windows newline conversion invalidated replay hashes: snapshots are now written as UTF-8 bytes; the final live pass repaired/replaced current snapshots and all current hashes were checked.
5. Existing profile aliases could duplicate after redirects: verified same-name, same-firm redirects preserve identity and record source URL changes; stable identities survive seed import.

The minor ordinary Ctrl-C run-status issue was also fixed and tested. Hard process termination can still leave a stale lock/running status, which requires operator inspection. The review initially noted a missing helper directory; the HTTP helper now exists and lint/CI paths were checked. No second independent review of the fixes is claimed; the covering tests and complete suite were run instead.

Fresh-source verification found that the configured pytest temporary directory assumed an ignored parent existed. The configuration now uses a direct workspace temporary directory. The failed fresh-copy test attempt is not counted as passing; it was rerun after the fix.

## Verification not completed

- **Full browser QA:** initial browser access was unavailable. Finalization obtained limited native Chrome evidence, described below; keyboard/select interaction, print preview, mobile-device testing and accessibility certification remain unverified. Shared-window user activity was respected.
- **GitHub Actions:** the initial build did not execute cloud workflows. Finalization published the private source, and Linux CI succeeded on Python 3.11 and 3.12. The manual refresh run and its artifact are recorded below after completion.
- **Complete field or roster accuracy:** no exhaustive human-labelled evaluation set, total practice denominator, all-office crawl or independent manual confirmation of every record was performed. `validate` checks metadata and allowed source paths, not current remote truth.
- **Production operation:** no external hosting, authentication, live alert delivery, vendor permission programme or scheduled remote job has been activated.

This is a verified local MVP with documented coverage limits, not a claim of full assessment data completeness.

## Finalization verification

The first finalization review baseline contained **142 official-source profiles across 11 firms: 134 core corporate/M&A and 8 explicitly adjacent M&A litigation**. Added 88 records via public web/Firecrawl discovery and permitted official practice pages. All current snapshot hashes were checked before promotion. A new Simpson 429 caused collection to stop; the original four blocked firms were not retried. See DATA_REVIEW.md for scope and exclusions.

Native Chrome later exposed the local application. The coverage page was visually inspected in a narrow window and the directory accessibility tree exposed labelled filters and semantic tables. Input automation was interrupted by active user interaction; the shared Chrome window was left alone when it switched away from Pinpoint. This is limited browser evidence, not a completed keyboard/mobile/print matrix.

Release checks additionally cover allowlisted ZIP contents, manifest integrity, tampering, unsafe paths, case-insensitive archive collisions and deterministic output. One Windows symlink test may skip when the account lacks privilege; Linux CI executes that test. Same-name source URLs differing only in case or trailing slash now retain identity without cosmetic change events. Two cosmetic slash-only differences discovered during promotion were investigated and removed from the release change feed; no substantive market change is claimed.

Independent final review reported no Critical/Important issue. Its two minor alias-selection/Windows ZIP-collision findings were reproduced and fixed. Final commands and GitHub execution links follow after the actual runs.

### Executed final local checks

- Full suite: **74 passed, 1 skipped, 1 upstream warning** on Windows/Python 3.11. The skipped test requires privileged Windows symlink creation.
- Ruff checks and format checks passed for 18 Python files; portable seed validation passed.
- Actual HTTP smoke checked the directory, coverage, changes, health/API, local assets and **all 142 detail pages**, plus no-results, CSV, 422 and 404 states.
- Private repository created at https://github.com/syedaliabbas1/pinpoint-partner-intelligence; source publication and cloud run results are recorded after execution.

### Published source CI

[GitHub Tests run 44914416566](https://github.com/syedaliabbas1/pinpoint-partner-intelligence/actions/runs/44914416566) completed successfully on Linux for Python 3.11 and 3.12, including locked dependency installation, tests, Ruff, format, compile and seed validation. Both jobs tested source commit 5583ac07ff8d45bd863b61b4486818ba0e3eab23. The Windows archive extracted to a clean source-only directory also passed74 tests with1 privilege-basedskip, initialized its own database, and passed provenance validation.

## Committed release scope and final checks

The manual [cloud refresh](https://github.com/syedaliabbas1/pinpoint-partner-intelligence/actions/runs/44914457810) completed successfully and its 175-record JSON artifact was downloaded and provenance-validated. Review of its 33 additions accepted 26 and excluded 7 tax/litigation/public-law specialists. The committed curated baseline is **168 profiles across 13 firms: 160 corporate/M&A and 8 adjacent litigation**. Full worldwide coverage remains unverified.

Extractor version 3 adds six reproducing scope regressions. Source excerpts/actual retrieval metadata support the 26 cloud additions; their raw HTML snapshots were not retained in the downloaded artifact, so no local byte-for-byte snapshot claim is made for those 26. Existing 142 snapshots matched their hashes.

The final Windows suite passed **80 tests**, with 1 privileged-symlink test skipped and 1 upstream deprecation warning. Ruff check/format, compile and seed validation passed. The actual server smoke checked all 168 profile pages and directory/coverage/changes/API/static/CSV/error states. Cloud CI for the final code is checked separately after push; the previous 75-test Linux result above is historical. Full browser keyboard/print/mobile checks remain unverified.
