# Pinpoint partner intelligence v0.1.0

A runnable local research application for legal recruiters, with partner search, official-source briefs, CSV export, coverage and refresh history, and reviewable field changes.

- Reviewed baseline: 168 profiles across 13 of 15 specified firms. 160 have corporate/M&A evidence; 8 are explicitly labelled adjacent M&A litigation. All firm rosters remain partial; two remaining source blocks are documented.
- Windows tests: 80 passed, 1 privilege-based symlink test skipped. Linux GitHub CI: 81 passed on each of Python 3.11 and 3.12. See the verification report for the exact source commit and run link.
- All 168 HTTP detail routes checked; provenance validation, lint, formatting, dependency and snapshot checks passed.
- Source ZIP excludes credentials, PDFs, raw HTML, caches, virtual environments and SQLite databases. It includes an independently verifiable SHA-256 file manifest.
- Follow README.md to run; see docs/SHARING.md for extraction and sharing instructions, and docs/VERIFICATION.md for executed checks and limitations.

The repository is private. Give the assessment reviewer access before sharing its link, or transfer the verified source ZIP through the agreed channel. This release publishes source rather than hosting a public application. Full roster coverage, full browser/accessibility certification and assessment submission are not claimed.
