# Track Your GEO / AI Recommend — OpenSpec project

## Product

**Track Your GEO** is an internal GEO visibility probing MVP (YAML pilots, multi-model probes, SQLite runs, operator dashboard). **AI Recommend** is the customer-facing brand for PDF/web reports and outbound pilots (`airecommend.co.uk`), built from the same probe engine and plain-language report layer.

## Repository map (behaviour specs)

| Capability | Spec | Primary code |
|------------|------|----------------|
| GEO probe & dashboard | [specs/geo-probe/spec.md](specs/geo-probe/spec.md) | `apps/api/tygeo/` |
| URL intake | [specs/url-intake/spec.md](specs/url-intake/spec.md) | `tygeo/url_intake.py` |
| Plain-language report | [specs/plain-language-report/spec.md](specs/plain-language-report/spec.md) | `tygeo/plain_report.py` |
| Customer PDF export | [specs/customer-report-export/spec.md](specs/customer-report-export/spec.md) | `tygeo/customer_export.py` |
| Batch export runner | [specs/batch-export-runner/spec.md](specs/batch-export-runner/spec.md) | `scripts/batch_export.py` |
| Customer web report | [specs/customer-web-report/spec.md](specs/customer-web-report/spec.md) | `site/`, `tygeo/customer_web_report.py` |

## Workflow

- Active proposals: `openspec/changes/<name>/`
- Shipped changes: `openspec/changes/archive/YYYY-MM-DD-<name>/`
- Agents: [AGENTS.md](../AGENTS.md), skills `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`, `openspec-sync-specs`
- Validate: `npx --yes @fission-ai/openspec@latest validate --all --strict` and `pytest eval -q`

## Out of scope for specs

Prospect lists, vault CSVs, live report PDFs for real firms, deploy credentials, and send operations stay in the Obsidian vault — never committed to git.
