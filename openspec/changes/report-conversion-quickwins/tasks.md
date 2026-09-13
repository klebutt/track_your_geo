## 1. API plain report

- [x] 1.1 Extend `PlainReportOut` with `loss_entries`, `what_this_is`, `meaning`, `competitor_summary`, `deeper_insights`, `index_note`
- [x] 1.2 Aggregate named competitors into `loss_entries`; keep `loss_queries` derived
- [x] 1.3 Add deterministic deeper-insights forks and story/copy fields

## 2. UI

- [x] 2.1 Rebuild plain-report panel to 60s hierarchy (what / X-N / who instead / meaning / deeper CTA)
- [x] 2.2 Add dual-score honesty line under Summary stats; demote empty wins

## 3. Tests and samples

- [x] 3.1 Update `eval/test_plain_report.py` for named losses, empty tracked competitors, deeper_insights length
- [x] 3.2 Run `pytest eval -q`
- [x] 3.3 Refresh vault Hamilton/Hewitt sample reports from runs #18/#19
- [x] 3.4 Worklog entry
