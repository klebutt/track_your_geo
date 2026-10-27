# Capability: Plain-language report

## Purpose

Deterministic, customer-readable recommendation summary from stored probe rows (no extra LLM), used in the operator dashboard, customer PDF/markdown export, and web report pages.

## Requirements

### Requirement: Plain-language recommendation summary

The system MUST be able to present a completed analysis run as a plain-language recommendation report that answers whether AI assistants recommend the business, without requiring the reader to understand GEO scoring terminology. The report MUST be derived from stored run evidence (query results and visibility signals). The system MUST NOT require a new LLM call to produce the core headline and win/loss lists for this capability.

#### Scenario: Headline recommend rate

- **WHEN** a completed run with probe results is shown in the plain-language report
- **THEN** the report presents a headline of the form that the business was recommended in X of N customer-intent searches
- **AND** N is based on unique query texts (not raw per-model probe row count)
- **AND** X counts queries where at least one model reply mentioned the brand (using the same brand matching rules as probe scoring)

#### Scenario: Wins and losses lists

- **WHEN** the plain-language report is rendered for a completed run
- **THEN** it lists example searches where the business appeared (when any)
- **AND** it lists example searches where configured competitors appeared and the business did not (when such rows exist), including competitor names when present in stored evidence

#### Scenario: Minimal jargon on report surface

- **WHEN** the operator views the plain-language report section
- **THEN** the primary copy uses recommend/AI-search language rather than leading with "GEO score" or "visibility gate"
- **AND** existing technical summary/insights sections MAY remain available for operator depth

### Requirement: Geography note from locality stance

When locality stance is available on the run profile snapshot, the plain-language report MUST include a short geography note describing whether searches were mostly local, a local/UK-wide mix, or mostly UK-wide/remote, using plain English (not raw stance codes on customer surfaces).

#### Scenario: Geography note from stance

- **WHEN** a completed run has `locality_stance` on its profile snapshot
- **THEN** the plain-language report includes a short note reflecting that stance's local vs UK-wide mix

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

The customer-facing plain-language report surface MUST present, in order: a one-sentence explanation of what was measured; the X of N result; who showed up instead (names); what this means; a short deeper-insights next step. Empty "where you appeared" lists MUST NOT dominate the first screen. Technical GEO composite MUST NOT lead the plain report.

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

When visibility rate and composite GEO score are shown near the report (for example Snapshot), the system MUST provide a short plain-language note that visibility is how often the name appeared in replies and the index is a directional blend, not a ChatGPT replica. The plain report MUST continue to lead with X of N rather than the composite score.

#### Scenario: Index note with scores

- **WHEN** a completed run's Summary shows visibility and composite score
- **THEN** a short honesty / dual-score explanation is available from the plain report payload or adjacent copy

### Requirement: Customer-facing deeper insights and gloss

The plain-language report MUST use Sales-locked customer copy for deeper insights and the composite gloss: the action-plan insight title MUST include the firm (brand) name, not the town/location; the optional deeper next-steps lead-in MUST NOT include the word "Soft"; the index note MUST name visibility, position, sentiment, and citations as a compass (not consumer ChatGPT parity); customer-facing report strings MUST NOT use Unicode em dashes (U+2014).

#### Scenario: Action plan names the firm

- **WHEN** a completed plain-language report is built for brand "Riverside Accountants" with location "Derby, UK"
- **THEN** a deeper-insights title includes "Riverside Accountants"
- **AND** that title does not use "Derby" as the action-plan subject

#### Scenario: Soft removed from next-steps lead-in

- **WHEN** the dashboard or export shows the deeper next-steps lead-in
- **THEN** the text does not contain the word "Soft"
- **AND** it still invites a book-a-call or email reply

#### Scenario: Composite gloss lists four signals

- **WHEN** the plain-language report provides `index_note`
- **THEN** it mentions visibility, position, sentiment, and citations
- **AND** it frames the index as a compass, not a replica of consumer ChatGPT

#### Scenario: No em dashes in customer report fields

- **WHEN** `what_this_is`, `index_note`, deeper-insight titles/details, or meaning/gap strings are produced for customer use
- **THEN** those strings do not contain the Unicode em dash character

### Requirement: Loss lines keep specific queries

The plain-language report MUST continue to attach the specific query text on who-showed-up / loss entries so export matches the dashboard shape.

#### Scenario: Loss entry includes query

- **WHEN** a search has tracked competitors and no brand mention
- **THEN** `loss_entries` include both competitor names and the query text for that search

### Requirement: Gap copy for weak visibility

When no queries recommend the brand, or when at most two of ten or more queries recommend the brand, `gap_summary` MUST use plain-English weak-visibility wording derived deterministically from X and N (without a new LLM call).

#### Scenario: Zero appearances

- **WHEN** X is 0 for a completed run
- **THEN** gap summary states the firm did not appear and describes a visibility gap

### Requirement: Report available for URL and demo runs

The plain-language report MUST work for runs started from URL intake and for demo pilot runs that have completed probe results.

#### Scenario: URL run report

- **WHEN** a completed URL-started run is loaded in the dashboard
- **THEN** the plain-language report section is available using that run's stored results and inferred brand name

#### Scenario: Empty or running run

- **WHEN** a run is still running or has no query results
- **THEN** the plain-language report is not presented as a finished recommend-rate headline
