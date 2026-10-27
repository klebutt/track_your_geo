## ADDED Requirements

### Requirement: Operator overrides on URL runs

`POST /api/runs/from-url` MUST accept optional `location` and `display_name` fields for batch CSV handoff.

#### Scenario: Batch CSV location override

- **WHEN** batch export passes `location` for a firm URL
- **THEN** the from-url body includes that location and probes use the overridden geography
