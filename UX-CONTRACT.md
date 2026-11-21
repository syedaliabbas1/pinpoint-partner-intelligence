# Pinpoint research workflow

Business source: supplied technical assessment PDF and current user instructions. Visual contract: [DESIGN.md](DESIGN.md).

## Canonical UI Map
| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Select/Listbox | templates/filters.html | This contract | Native OS popup | Browser keyboard/open popup |
| Form | templates/filters.html | GET query contract | Search/filter | test_web.py |
| Scrollbar | static/app.css | DESIGN.md | Document and table overflow | Browser narrow viewport |
| Read navigation | templates/base.html | web.py routes | Directory/detail/coverage/changes | TestClient + browser |

## Behaviour
Search is explicit GET submission; no remote keystroke search or async races. Clear resets only the query and retains other filters. Queries, filters and pages persist in URLs. Changing filters resets to page 1. Results sort by source name. Profile links preserve a safe relative directory return URL. CSV exports all matching profiles (maximum 2,000) using the active filters and spreadsheet-safe cells.

An empty baseline explains how to initialise data; no-results offers clear filters. Out-of-range pages clamp to the last page. Invalid query types show an app-owned 422 explanation. Unknown profiles and routes return a navigable 404 page.

Profile details distinguish source excerpts, captured facts and recruiter review. Summary text is extracted source text, not an AI assessment. Office facts need explicit profile contact/location evidence. Unknown fields remain visible as unknown. The initial load is a baseline, never a move. Missing profile URLs are review signals; failures do not remove anyone.

Coverage shows all 15 firms including blocked and zero-record firms. No record count is presented as total practice size. Refresh runs are CLI-only, with a file lock, bounded work and per-firm status. The browser has no write operations. CLI failures preserve last-known data. Observation time is UTC; freshness is shown independently from original first seen.

## Scope and policy sources
| Topic | Authoritative source | UI consequence |
|---|---|---|
| Practice scope | Technical assessment, page 1 | Corporate/M&A evidence required; global coverage labelled unverified |
| Website conduct | Technical assessment ground rules + user request | Blocks/access failures reported, no evasion |
| Data lifecycle | User prohibition on fabricated profiles | Source links, timestamps and evidence; no inferred departures |
| Access | Local MVP architectural decision | Read-only loopback UI; authentication required before external hosting |
| Deletion/billing | Not in MVP | No destructive actions or billing UI |

## Accessibility and locale
English (UK) interface, global name content. Native semantic tables, labels and selects. Visible focus, skip link, meaningful headings and source-link names. No custom composite widgets, colour-only state, animation, hover-only content or private data. Browser checks cover narrow viewport, keyboard, no-results, source detail and native filter controls. WCAG 2.2 AA is a design target, not a certification.
