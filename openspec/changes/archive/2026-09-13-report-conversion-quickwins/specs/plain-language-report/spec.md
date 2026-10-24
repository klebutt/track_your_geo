## ADDED Requirements

### Requirement: Named competitor losses

The plain-language report MUST list competitor losses with the **names** of configured competitors that appeared in stored probe evidence when the brand did not, not only the query text. When a search had no tracked competitor mentions, the system MUST NOT invent firm names.

#### Scenario: Loss entry includes competitor names

- **WHEN** a completed run has a unique query where no model mentioned the brand and at least one model mentioned a configured competitor
- **THEN** the plain report includes a loss entry for that query that lists those competitor names

#### Scenario: No tracked competitors on a miss

- **WHEN** a completed run has queries where the brand was not mentioned and no configured competitor was mentioned
- **THEN** the plain report does not fabricate competitor names for those queries
- **AND** customer-facing copy MAY state that no tracked competitors were named

### Requirement: Sixty-second report hierarchy

The customer-facing plain-language report surface MUST present, in order: a one-sentence explanation of what was measured; the X of N result; who showed up instead (names); what this means; a short deeper-insights next step. Empty “where you appeared” lists MUST NOT dominate the first screen. Technical GEO composite MUST NOT lead the plain report.

#### Scenario: Hero order

- **WHEN** an operator views the plain-language report for a completed run
- **THEN** the section leads with what-this-is and the recommend-rate headline before deeper technical summary content
- **AND** named competitor losses appear before operator Insights recommendations

### Requirement: Deterministic deeper-insights close

The plain-language report MUST include a short deterministic deeper-insights block (without a new LLM call) that tees optional next steps such as model-level who/phrases, a locality-aware action plan, and a re-test after changes. LLM-generated SEO-style recommendations MAY remain available outside this block for operator depth.

#### Scenario: Deeper insights present when report ready

- **WHEN** the plain-language report is ready for a completed run
- **THEN** it includes at least two deterministic deeper-insight items
- **AND** producing them does not require an additional LLM call

### Requirement: Dual-score honesty line

When visibility rate and composite GEO score are shown near the report (e.g. Summary), the system MUST provide a short plain-language note that visibility is how often the name appeared and the index is a directional blend, not a ChatGPT replica. The plain report MUST continue to lead with X of N rather than the composite score.

#### Scenario: Index note with scores

- **WHEN** a completed run’s Summary shows visibility and composite score
- **THEN** a short honesty / dual-score explanation is available from the plain report payload or adjacent copy

## MODIFIED Requirements

### Requirement: Wins and losses lists

The system MUST be able to present a completed analysis run as a plain-language recommendation report that answers whether AI assistants recommend the business, without requiring the reader to understand GEO scoring terminology. For losses, the report MUST prefer structured loss entries that include query text and competitor names from stored evidence. A back-compat list of loss query strings MAY still be provided.

#### Scenario: Wins and losses lists

- **WHEN** the plain-language report is rendered for a completed run
- **THEN** it lists example searches where the business appeared (when any)
- **AND** it lists example searches where configured competitors appeared and the business did not (when such rows exist), including competitor names when present in stored evidence
