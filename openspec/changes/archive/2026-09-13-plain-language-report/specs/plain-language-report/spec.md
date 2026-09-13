## ADDED Requirements

### Requirement: Plain-language recommendation summary

The system MUST be able to present a completed analysis run as a plain-language recommendation report that answers whether AI assistants recommend the business, without requiring the reader to understand GEO scoring terminology. The report MUST be derived from stored run evidence (query results and visibility signals). The system MUST NOT require a new LLM call to produce the core headline and win/loss lists for this capability.

#### Scenario: Headline recommend rate

- **WHEN** a completed run with probe results is shown in the plain-language report
- **THEN** the report presents a headline of the form that the business was recommended in X of N customer-intent searches
- **AND** N is based on unique query texts (not raw per-model probe row count)
- **AND** X counts queries where at least one model reply mentioned the brand (or an alias already applied in visibility matching)

#### Scenario: Wins and losses lists

- **WHEN** the plain-language report is rendered for a completed run
- **THEN** it lists example searches where the business appeared
- **AND** it lists example searches where configured competitors appeared and the business did not (when such rows exist)

#### Scenario: Minimal jargon on report surface

- **WHEN** the operator views the plain-language report section
- **THEN** the primary copy uses recommend/AI-search language rather than leading with “GEO score” or “visibility gate”
- **AND** existing technical summary/insights sections MAY remain available for operator depth

### Requirement: Report available for URL and demo runs

The plain-language report MUST work for runs started from URL intake and for demo pilot runs that have completed probe results.

#### Scenario: URL run report

- **WHEN** a completed URL-started run is loaded in the dashboard
- **THEN** the plain-language report section is available using that run’s stored results and inferred brand name

#### Scenario: Empty or running run

- **WHEN** a run is still running or has no query results
- **THEN** the plain-language report is not presented as a finished recommend-rate headline
