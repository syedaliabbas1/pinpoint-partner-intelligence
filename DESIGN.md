---
version: alpha
name: Pinpoint partner intelligence
colors:
  primary: "#155e75"
  ink: "#142b42"
  muted: "#526477"
  surface: "#ffffff"
  canvas: "#f1f5f9"
  border: "#d4dfe8"
  warning: "#92400e"
  success: "#166534"
typography:
  display:
    fontFamily: "Palatino Linotype, Book Antiqua, Georgia, serif"
  body:
    fontFamily: "Segoe UI, system-ui, sans-serif"
  utility:
    fontFamily: "Consolas, monospace"
rounded:
  control: "0.375rem"
spacing:
  unit: "0.5rem"
components:
  panel:
    backgroundColor: "#ffffff"
---

## Overview
A recruiter's research desk: restrained navy navigation, cool white work surfaces and precise evidence labels. Product register. The signature is a fifteen-firm coverage strip that connects each firm directly to its profiles. Its segments encode actual captured counts, never inferred market share. Avoid marketing heroes, decorative metrics and implied completeness.

## Colors
`pinpoint/static/app.css` is the canonical runtime token source. Frontmatter mirrors accepted tokens. Each color maps by name to `--primary`, `--ink`, `--muted`, `--surface`, `--canvas`, `--border`, `--warning`, `--success`; shared panels, badges and controls consume those variables. Labels carry meaning as well as color. Light theme only.

## Typography
Palatino is used sparingly in page titles, with Segoe UI for research tables and controls; Consolas for evidence hashes. Local fonts only; no external font requests. Body 16px, secondary metadata at least 14px. Preserve accented professional names.

## Layout
Desktop: 220px navigation and a fluid workspace. Directory table uses natural document scrolling, horizontal overflow at narrow widths, and 25 results per page. Below 860px navigation becomes a top bar and forms wrap. Profile pages pair the brief with a distinct evidence panel. No fixed-height work areas. Global scrollbar styles and stable gutters live in app.css.

## Elevation & Depth
Flat bordered surfaces. No shadows, gradients or animated decoration. Focus outlines must remain visible.

## Shapes
6px control radius. Tags have a compact 4px radius. Native select popups intentionally follow the operating system.

## Components
Shared `base.html` owns navigation, feedback and the coverage strip. `filters.html` owns query controls. Page templates share table, panel, badge, empty-state and button classes. Form state lives in URL queries. Native selects are canonical. No dialogs, date pickers, bulk selection or destructive UI.

## Do's and Don'ts
Show unknown offices as "Not captured". Show observation times in UTC with explicit timezone. Separate observed changes from confirmed moves. Keep incomplete coverage visible beside the results. Do not add fictional partner details, automatic outreach or AI claims. Motion is unnecessary; reduced-motion users receive the same experience.
