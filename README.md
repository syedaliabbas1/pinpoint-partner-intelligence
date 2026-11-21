# Pinpoint partner intelligence

A research desk for legal recruiters preparing corporate and M&A partner conversations. Search by name, firm, captured office or practice evidence; open a source-backed brief; export a shortlist; and review what changed between observations.

**This is a working local MVP with partial data, not a complete market database.** The release baseline covers **142 profiles at 11 of the 15 specified firms**, including **8 M&A litigation profiles explicitly labelled adjacent** (134 core corporate/M&A profiles). Four firms returned access blocks. No firm's worldwide practice roster has been verified as complete. Counts and access details are in [data/coverage.json](data/coverage.json) and the application's coverage screen; those files are the authority if a later refresh changes the numbers.

The supplied assessment PDF is the specification. The job specification and supplied 12-month roadmap were also read. `Codex_Prompt_Pinpoint_CTO_Assessment.md` was not present: after a path request, the user pointed back to the assessment PDF, so implementation proceeded from that primary brief. The PDF says submission was due **19 November 2026, 17:00 UK time**; this work session is dated 21 November. Confirm submission arrangements before sending it.

## Run it

Requires Python **3.11 or 3.12**, pip and an internet connection for the initial dependency installation. Running the included dataset and tests needs no law-firm access, AI subscription or API key. Start commands from the repository root.

Windows PowerShell, without changing execution policy or activating a shell script:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pinpoint.cli init
.venv\Scripts\python.exe -m uvicorn pinpoint.web:app --host 127.0.0.1 --port 8000
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pinpoint.cli init
.venv/bin/python -m uvicorn pinpoint.web:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Stop the server with Ctrl-C. The default SQLite database is `data/pinpoint.sqlite`; set `PINPOINT_DB` to use another file. Startup imports the portable baseline/history only when needed and never replaces an existing database with the bundled data.

The server binds to loopback deliberately. This MVP has no login or role system; add authentication, deployment controls and data governance before making it available outside a trusted local environment. No hosted service has been deployed as part of this submission.

## What a recruiter can do

1. Search the directory and combine firm, office and practice filters. Filter state survives in the URL. Results are alphabetical, 25 per page.
2. Open a partner brief with their captured role, offices, biography excerpt, first/last observation times, official source link, extraction evidence and content hash. Print the brief using the browser.
3. Export the current filtered results to CSV. Cells that could be interpreted as spreadsheet formulas are escaped; exports include office-evidence freshness. Exports are capped at 2,000 rows.
4. Check all fifteen firms on the coverage page, including zero-record firms and actual refresh failures.
5. Review field changes with before/after values and excerpts. A changed page is a signal to investigate, not proof of a partner move. Initial records never become fake joiner alerts.

No emails are sent, people ranked by willingness to move, or private contact details enriched. Short source excerpts may contain the public business contact information published by the firm; contact extraction is not a separate product feature.

## Actual coverage

Snapshot from the build session on **21 November 2026**. “Captured” means an official profile was successfully retrieved and passed the extraction rules. It does not mean independent human confirmation of every fact, inclusion in an exhaustive practice directory, or current availability for recruitment. The scope includes offices worldwide; discovery is uneven and mostly English-language.

| Assessment firm | Captured | Boundary |
|---|---:|---|
| Kirkland & Ellis | 21 | Partial official-profile sample |
| Wachtell, Lipton, Rosen & Katz | 0 | Directory returned HTTP 403; stopped |
| Quinn Emanuel Urquhart & Sullivan | 8 | Explicit M&A litigation only; labelled adjacent, not transactional M&A |
| Davis Polk & Wardwell | 0 | Collector's robots request returned HTTP 403; stopped |
| Simpson Thacher & Bartlett | 10 | Partial sample; expansion stopped on HTTP 429 |
| Paul, Weiss, Rifkind, Wharton & Garrison | 15 | Partial official-profile sample |
| Gibson Dunn | 0 | Collector's robots request returned HTTP 403; stopped |
| Latham & Watkins | 25 | Partial official-profile sample |
| Cravath, Swaine & Moore | 4 | Known profiles allowed; actual directory path disallowed by robots |
| Milbank | 16 | Corporate/M&A structured-practice evidence; tax-only/transport profiles excluded |
| Sullivan & Cromwell | 14 | Partial sample; official navigation directory verified |
| Paul Hastings | 0 | Robots request returned HTTP 429; stopped |
| Skadden, Arps, Slate, Meagher & Flom | 7 | Partial official-profile sample |
| King & Spalding | 11 | Partial official-profile sample |
| Weil, Gotshal & Manges | 11 | Partial official-profile sample |
| **Total** | **142** | **11 firms with captured records; 0 firms certified complete** |

Web search and the configured Firecrawl research CLI were used to discover candidate URLs. Finalization also enumerated a bounded set of official practice pages, adding 88 accepted profiles after scope review. See [docs/DATA_REVIEW.md](docs/DATA_REVIEW.md). **Search snippets were not imported as verified profiles.** The product's refresh runs directly against allowed official pages and needs no search-service credentials. Public search rankings and static directory pages are not exhaustive; the remaining URLs have to be discovered and verified through firm-specific practice filters, pagination, or authorised exports. A zero is an access/collection limitation, not a claim that the firm has no relevant partners.

Access can differ between requests and HTTP clients. For example, initial reconnaissance retrieved robots files that the subsequent collector was denied. The collector stops on the response it actually receives; it does not switch identity, proxy, transport or route to get around a denial. [docs/DATA.md](docs/DATA.md) explains scope and evidence handling.

## Architecture and why

```text
Official public pages -> robots/pacing/allowlist -> HTML extraction -> SQLite
                                  |                    |               |
                           private snapshots     source evidence    FastAPI/Jinja
                                                                     + CSV/API
Weekly/manual CLI -> persisted observations/history -> next comparison
```

One Python process and SQLite are enough for a single recruiter's research dataset. FastAPI supplies typed query boundaries, ordinary HTTP routes and testable endpoints. Jinja keeps tables and forms usable without a frontend build. The small JavaScript file enhances clear-search and printing; both controls remain disabled until their handlers are attached. Native selects intentionally use operating-system behaviour. CSS, fonts and scripts are served locally.

`Store.observe()` writes each firm's accepted batch in a transaction. Identity is scoped by firm and source URL, not a person's name alone. A verified same-firm redirect with the same source name preserves the existing identity and first-seen history. Cross-firm names and ambiguous renames are not automatically merged. SQLite WAL mode permits readers during refresh; a file lock serialises CLI refreshes. A failed firm does not prevent independent firms from being processed.

Profiles store normalised facts and short excerpts in JSON alongside indexed identities, with separate event and run tables. This avoids a premature complex practice/office ontology while still retaining field-level change evidence. For this dataset, literal Unicode casefold search and exact office/practice filtering happen in Python after reading SQLite rows. That is deliberately simple, **not a design for millions of profiles**. It preserves apostrophes, accents and literal SQL metacharacters without constructing SQL from queries.

**Alternatives rejected:**

- A React/Next frontend and separate API would add a build pipeline, duplicated state and more deployment work without improving this shortlist workflow within six hours.
- PostgreSQL, Redis, a task queue, container orchestration and multiple services are unnecessary for this local workload. SQLite has straightforward backups and a portable seed; infrastructure is not the current bottleneck.
- An LLM extraction/classification service would add cost, credentials, prompt injection exposure and difficult-to-audit mistakes. Here, source selectors, structured practice metadata and conservative rules are easier to defend. AI helped write and review code; the application does not invent summaries or infer personal intent. If added later, AI should draft evidence-linked briefs for recruiter review and be evaluated against a human-labelled sample.
- A script with a CSV as its only output would collect data but miss the recruiter's repeated search, evidence and change-review workflow.
- Scraping behind challenges, private databases or paywalls was rejected. Robots permission alone is not a substitute for reviewing a site's terms or obtaining appropriate operational permission.

The hard part is source coverage and extraction reliability, not rendering another dashboard. Building a complete firm-specific practice-directory adapter would be the next investment.

## Refresh and change detection

Using the virtual environment's Python (replace `python` below with `.venv\Scripts\python.exe` on Windows, or activate your environment):

```bash
python -m pinpoint.cli refresh --firm milbank --max-profiles 15 --export
python -m pinpoint.cli refresh --max-profiles 100 --export
python -m pinpoint.cli coverage
python -m pinpoint.cli validate
```

`--max-profiles` is a **per-firm request budget**, between 1 and 500, default 15. Existing records are refreshed first; known discovery URLs, links from up to three configured official practice pages, and static directory links follow. Each practice page uses the same robots/access checks as a profile. A budget smaller than the existing dataset leaves some records unrefreshed; compare each record's observation time. `--export` updates `seed.json`, `history.json` and `coverage.json` for portable startup; it does not commit or upload anything. `export` can also be run separately when no other writer is active.

The collector:

- Checks robots before page requests and respects disallowed paths, crawl delay and request rate. A missing robots file (404/410) is treated as no published policy; denied, malformed or unavailable policy fails closed. A disallowed directory is never fetched; independently allowed, already-known profile URLs can still be checked against their own path policy.
- Uses a descriptive user agent, at least 1.5 seconds between requests to a firm, a 25-second network timeout, a 5 MB decompressed response limit and bounded redirects. Every redirect must remain on that firm's HTTPS hosts and pass robots policy.
- Stops on 401/403/429 and detected challenges. It does not retry those responses or rotate proxies/identities. Future weekly runs can recheck whether access has changed.
- Stores UTF-8 response snapshots by SHA-256 in ignored `data/raw/`, with a local request ledger. The hash identifies the decoded HTML encoded as UTF-8, **not the compressed HTTP wire bytes**. Byte-preserving writes avoid Windows newline corruption.
- Requires a profile heading, partner role and corporate/M&A practice evidence. It removes global navigation and related-colleague cards. Office names require contact/location evidence; unknown offices remain unknown. Corporate Tax does not qualify as Corporate. Quinn's explicitly named M&A litigation is separated as adjacent practice.
- Ignores volatile page markup when detecting changes: only normalised name, role, practices, offices, source URL and biography excerpt are compared. Changes across extraction versions are reprocessing, not market events. Bump the version when changing interpretation rules.
- Retains an earlier office when a same-version refresh cannot extract a new one, labels it **last known**, and carries its own evidence timestamp/hash. It does not turn template drift into an office-removal alert.
- Flags observed 404/410 profile failures for review without deleting anyone. No absence in an incomplete directory is treated as departure. A profile that no longer passes title/practice extraction is retained with its earlier observation timestamp and a run-level review message.

Repeated identical observations update last-seen times without adding duplicates or change events. `first_seen` survives export/import. The UI never labels a new observation as a confirmed joiner or leaver. The initial 54-record sample had a second live pass; finalization added 88 independently fetched and scope-reviewed records. The final 142-record roster was not exhaustively revisited; see [docs/VERIFICATION.md](docs/VERIFICATION.md) for the actual result.

**Scheduling:** `.github/workflows/refresh.yml` runs Mondays at **06:23 UTC** and supports manual dispatch. It restores JSON state from the previous successful run's artifact, runs offline tests, refreshes with a budget of 100 per firm, validates and uploads the next state with 90-day retention. The workflow has read-only repository permissions; it does not commit, open PRs or publish data automatically. Download and inspect the artifact to update your local dataset. If no previous artifact exists or retention makes it unavailable, the workflow visibly falls back to the committed baseline, so comparisons may cover a longer interval. GitHub's scheduler is best-effort, not an exact-time guarantee. This workflow is supplied but has **not been executed on GitHub** in this session.

For an unattended local installation, run the same CLI command weekly using Task Scheduler or cron, pointing it at the same database. An example cron entry after setting the actual absolute checkout path:

```cron
23 6 * * 1 cd /absolute/path/to/pinpoint && .venv/bin/python -m pinpoint.cli refresh --max-profiles 100 --export >> refresh.log 2>&1
```

Ordinary Ctrl-C records an interrupted run and releases the lock. A hard kill may leave a lock and a running status: inspect the lock's PID and confirm no refresh is active before removing that exact file. Do not start a second writer as a workaround.

## Test and verify

```bash
python -m pytest -q
python -m ruff check pinpoint tests scripts
python -m ruff format --check pinpoint tests scripts
python -m compileall -q pinpoint scripts
python -m pip check
python -m pinpoint.cli validate
# With the app already running:
python scripts/smoke.py
```

The automated tests are offline and use temporary databases/HTTP transports. They cover baseline/idempotent refresh, real field changes, Unicode/literal filters, rollback, failed-source retention, redirects, robot policies, snapshot checksums, field freshness, CSV safety, HTML escaping, clean seed/history restoration and HTTP routes. `validate` checks shape and provenance metadata; it does not claim to reverify the remote facts. No coverage percentage is asserted.

The latest commands/results, fresh-start checks and review fixes are recorded in [docs/VERIFICATION.md](docs/VERIFICATION.md). There is one upstream Starlette/AnyIO deprecation warning under the locked environment; it is reported, not suppressed. The supplied GitHub CI runs Python 3.11 and 3.12, but only the local Python environment has been executed here.

**Browser verification:** local HTTP and TestClient checks are automated. Native Chrome later became available: the coverage page rendered correctly at a narrow window width, and the directory exposed labelled search/filter controls and semantic tables. Further automated clicks were interrupted by active user input; the shared window was left alone when it switched to unrelated content. Full keyboard, mobile-device and print-preview checks remain manual. The static UI audit is separate evidence, not a browser certification.

## What remains incomplete and what changes first

- **Complete all-firm/global coverage is unfinished.** Most directories need practice filters, pagination or JavaScript-specific adapters. Four access-blocked sources need permission, a supported feed or a later authorised access check. No workaround can honestly produce their missing profiles now.
- Tax/practice scope and office detection remain rules, not a human-reviewed census. Adjacent litigation and broader corporate finance require recruiter judgement. Names, current status and the official page must be checked before outreach.
- No confirmed movement reconciliation, cross-firm identity resolution, news monitoring, contact enrichment, alert email delivery, saved shortlists, CRM integration or natural-language AI search. None is needed to prove source-backed research and repeatable observations.
- No multi-user authentication, production deployment, backup service, formal privacy/legal assessment, data-retention automation or monitoring service. SQLite/JSON copies are available; a production rollout needs those controls and a tested restore procedure.
- Browser verification is limited to the observations described above. GitHub workflow execution is recorded separately in the verification report. No assessment submission or reviewer invitation has been sent. Automated tests cannot certify accessibility or directory completeness.

At 50 firms, keep the same process and add tested per-firm adapters, authoritative practice roster enumeration, source-health metrics and review queues. Rotate refresh budgets or raise them when all existing records must be visited; the present ordering can starve discovery behind a full refresh budget. Track changed source versions and extraction acceptance ratios. Move filtering/pagination into SQL/FTS as volume justifies it. Add a small work queue for measured scheduling needs, then PostgreSQL for concurrent editors and shared deployment. A queue or vector database would not fix today's source-access and taxonomy problems.

## Repository guide

```text
pinpoint/config.py       Fifteen-firm registry and timestamps
pinpoint/collect.py      Access policy, pacing, snapshots and refresh orchestration
pinpoint/extract.py      Official URL patterns and evidence extraction
pinpoint/store.py        SQLite profiles, field changes, run history and seed import
pinpoint/web.py          Read-only web/API routes and CSV export
pinpoint/cli.py          Init, refresh, export, coverage and provenance validation
pinpoint/templates/     Shared navigation, directory, briefs, changes and coverage
pinpoint/static/        Local CSS and small progressive enhancements
data/                   Portable seed, history, coverage and discovery candidates
tests/                  Offline regression and integration tests
scripts/smoke.py        Actual-server HTTP smoke check
.github/workflows/      Offline CI and weekly/manual refresh
```

`requirements.txt` declares direct dependencies; `requirements.lock` records the complete installed set. Source PDFs, development scratch work, snapshots, virtual environments and SQLite files are excluded from Git. The seed contains real public professional information; review that choice before making the repository public.

## Publish to GitHub

The final source repository is **private**: [syedaliabbas1/pinpoint-partner-intelligence](https://github.com/syedaliabbas1/pinpoint-partner-intelligence). Give the assessment reviewer access before sharing its link, or share the verified source ZIP described in [docs/SHARING.md](docs/SHARING.md). No application hosting is implied by publishing source.

To publish a separate copy, review the source and data first, then create an **empty** GitHub repository with no auto-generated README. From a checkout with no origin configured:

```bash
git status
git add README.md DESIGN.md UX-CONTRACT.md premium-ui.json pyproject.toml requirements.txt requirements.lock .gitignore pinpoint data tests scripts docs .github
git diff --cached --stat
git commit -m "Build source-backed partner intelligence MVP"
git remote add origin https://github.com/YOUR_USERNAME/pinpoint-partner-intelligence.git
git push -u origin main
```

If starting from a downloaded folder without Git metadata, first run `git init -b main`. If Git needs an author, set **your own** name/email locally before committing. Replace the remote URL with your repository; don't enter tokens into source files. For a private repository, grant the assessment reviewer access using the instructions/contact in the PDF (`sp@pinpoint-careers.com`; confirm the associated GitHub account). Do not include `.venv`, `.firecrawl`, `tmp`, source PDFs, raw snapshots or the SQLite database.

After pushing, check the Tests workflow and manually run the refresh workflow once. Inspect its coverage and artifact before relying on the schedule. For the finalized repository above, use its existing `origin` remote; do not add it again. Check the actual workflow links in the verification report. The source ZIP provides an additional portable delivery without Git metadata.

## Personal review before submission

- Run the README from a clean checkout; manually inspect desktop/mobile layout, keyboard navigation, filters, detail return links, printing and CSV output.
- Open at least one source profile per represented firm, review every practice boundary, and check the final counts/status against the coverage screen. Decide whether the limited sample is sufficient for the assessment and explain the gap candidly.
- Read the code and be ready to explain it line by line. In particular: why no LLM, why source failures never imply departures, and why global completeness is not claimed.
- Review the real public-profile excerpts, permissions/terms and repository visibility; confirm that no credentials or unrelated personal files are staged.
- Confirm the submission deadline/extension, reviewer access and the repository URL from another account.
- Review [docs/TIME.md](docs/TIME.md), add any work you personally did before/after this session, and submit an honest total. The measured agent-session elapsed time is not a claim about your own effort.

The README is the explanation of the product and its boundaries, not a promise that the unfinished parts have been delivered.
