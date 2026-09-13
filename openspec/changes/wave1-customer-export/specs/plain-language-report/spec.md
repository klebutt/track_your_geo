## ADDED Requirements

### Requirement: Customer-facing deeper insights and gloss

The plain-language report MUST use Sales-locked customer copy for deeper insights and the composite gloss: the action-plan insight title MUST include the firm (brand) name, not the town/location; the optional £5–20 next-steps lead-in MUST NOT include the word “Soft”; the index note MUST name visibility, position, sentiment, and citations as a compass (not consumer ChatGPT parity); customer-facing report strings MUST NOT use Unicode em dashes (U+2014).

#### Scenario: Action plan names the firm

- **WHEN** a completed plain-language report is built for brand “Hewitt Accountancy” with location “Bristol, UK”
- **THEN** a deeper-insights title includes “Hewitt Accountancy”
- **AND** that title does not use “Bristol” as the action-plan subject

#### Scenario: Soft removed from next-steps lead-in

- **WHEN** the dashboard or export shows the £5–20 deeper next-steps lead-in
- **THEN** the text does not contain the word “Soft”
- **AND** it still anchors the £5–20 range and invites a reply

#### Scenario: Composite gloss lists four signals

- **WHEN** the plain-language report provides `index_note`
- **THEN** it mentions visibility, position, sentiment, and citations
- **AND** it frames the index as a compass, not a replica of consumer ChatGPT

#### Scenario: No em dashes in customer report fields

- **WHEN** `what_this_is`, `index_note`, deeper-insight titles/details, or meaning/gap strings are produced for customer use
- **THEN** those strings do not contain the Unicode em dash character

### Requirement: Loss lines keep specific queries

The plain-language report MUST continue to attach the specific query text on who-showed-up / loss entries so export matches the current UI and Hewitt sample shape.

#### Scenario: Loss entry includes query

- **WHEN** a search has tracked competitors and no brand mention
- **THEN** `loss_entries` include both competitor names and the query text for that search
