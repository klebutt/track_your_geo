## ADDED Requirements

### Requirement: Branded PDF header and footer

Customer PDFs MUST render AI Recommend wordmark header and domain footer on every page.

#### Scenario: Header on multi-page export

- **WHEN** a customer PDF spans more than one page
- **THEN** each page includes the branded header and footer

### Requirement: Snapshot table visibility wording

The snapshot table MUST label visibility as **Mentioned in AI replies** with `{percent}% of replies`.

#### Scenario: Snapshot distinguishes reply rate from X of N hero

- **WHEN** a run has multiple models per query
- **THEN** the hero shows X of N unique queries while the snapshot shows per-reply mention rate

### Requirement: Customer-facing display name

Exports MUST prefer `profile_snapshot.display_name` for the visible firm label when set.

#### Scenario: Display name on PDF title block

- **WHEN** display_name is set on the snapshot
- **THEN** the PDF title block uses that label
