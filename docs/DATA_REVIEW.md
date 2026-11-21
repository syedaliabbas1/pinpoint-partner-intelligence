# Final data review

Final baseline: 168 captured profiles, 160 core corporate/M&A, 8 adjacent M&A litigation; 13 firms represented; no firm certified complete. Added 88 records to the initial 54. Every addition has an official source, retrieval timestamp, excerpt and matching snapshot hash. Targeted scope checks are agent review of official evidence, not an independent human census.

| Firm | Captured |
|---|---:|
| Kirkland & Ellis | 21 |
| Wachtell, Lipton, Rosen & Katz | 0 |
| Quinn Emanuel Urquhart & Sullivan | 8 |
| Davis Polk & Wardwell | 7 |
| Simpson Thacher & Bartlett | 10 |
| Paul, Weiss, Rifkind, Wharton & Garrison | 15 |
| Gibson Dunn | 19 |
| Latham & Watkins | 25 |
| Cravath, Swaine & Moore | 4 |
| Milbank | 16 |
| Sullivan & Cromwell | 14 |
| Paul Hastings | 0 |
| Skadden, Arps, Slate, Meagher & Flom | 7 |
| King & Spalding | 11 |
| Weil, Gotshal & Manges | 11 |

## Exclusions and boundaries

Four same-name King & Spalding case-variant URL duplicates were excluded. Annie Herdman was excluded because her personal practice is litigation/antitrust/FDI rather than the core target. Tax-only, transport-only and associate examples were rejected by extraction/scope checks.

## Broader corporate scope

- Milbank Beahn: corporate/CFIUS
- Milbank Ahrens: corporate/environmental
- Milbank Britton: corporate finance/alternative investments
- Milbank Bartfeld: project finance with personal Latin America M&A practice
- Simpson Millard/Albrecht: corporate acquisition finance

Those records have official corporate/practice membership evidence; they should not be described as pure transactional M&A partners. Quinn profiles are included only where personal practice lists explicitly name M&A litigation and remain labelled adjacent.

## Access and completeness

- Wachtell 403, Davis Polk robots 403, Gibson Dunn robots 403, Paul Hastings robots 429: not retried
- Simpson returned 429 during expansion: stopped and not retried
- Cravath directory/profile paths disallowed by robots: independently allowed known profiles retained
- All 15 firms / global roster completeness remains unverified

Collector run counts record raw accepted observations at the time of a request. Final captured counts reflect the curated distinct-profile dataset after exclusions; these are different measures. Search rankings, linked partner cards and the bounded practice crawl do not prove exhaustive all-office coverage.

## Cloud artifact scope review

[Refresh run44914457810](https://github.com/syedaliabbas1/pinpoint-partner-intelligence/actions/runs/44914457810) succeeded and produced175 machine-accepted observations. Review of the 33 additions retained 26: 7 Davis Polk and 19 Gibson Dunn profiles. Seven were excluded as outside the selected core target: Annie Herdman (antitrust/FDI), Daniel R. Adler (appellate litigation), Evert J. Christensen and John A. Neuwirth (securities litigation), Joseph M. Pari (tax), Lisa A. Alfaro (white collar), and Megren Al-Shaalan (administrative/public law). Supporting M&A mentions alone were insufficient. Extractor version 3 now enforces stronger primary-practice exclusions.

Final curated release:168 profiles across 13 firms, 160 core corporate/M&A and 8 adjacent litigation. Two firms remain at zero: Wachtell and Paul Hastings. Cloud retrieval followed the same per-path policy checks; it did not bypass a robots denial. Raw HTML for 26 cloud additions was not retained in the downloaded JSON artifact, so local byte-for-byte snapshot validation is claimed only for the earlier 142 records. The additions retain the actual cloud retrieval timestamps, excerpts and content hashes.
