# Worklog — 2026-09-13 (past URL runs dropdown)

## Problem

“Show latest URL analysis” only recovered one run; section 5 still showed the demo pilot’s probes while other panels showed the URL run.

## Shipped

- Replaced the button with a **Past URL analyses** `<select>` (completed URL runs, brand + date).
- `viewSource: 'demo' | 'url'` so demo brand changes do not overwrite an active URL selection.
- Section 5/6 bind to `profile_snapshot` (queries, competitors, brand domains) when viewing a URL run.

## Validation

Browser smoke: Hamilton-Eddy (#18) then Hewitt (#19) — plain report, summary, probes, competitors, and query replies all matched the selected run.
