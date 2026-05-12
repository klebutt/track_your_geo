# Delta spec: `geo-probe` (change `add-mvp-prototype`)

Baseline capability lives in [`../../../specs/geo-probe/spec.md`](../../../specs/geo-probe/spec.md). This change tracks the initial delivery.

## ADDED Requirements

### Requirement: Local stakeholder demo path

The delivery MUST allow a stakeholder to run the local dashboard against a YAML pilot and review visibility, gaps, recommendations, and approximate LLM cost in a single session without separate onboarding.

#### Scenario: Complete journeys 1, 2, and 4 in one session

- **WHEN** a stakeholder selects a pilot, optionally overrides brand or location, and starts a run with valid credentials
- **THEN** the UI shows visibility summary, per-query presence and competitor mentions for diagnosis, and a prioritized recommendations list
- **AND** the UI shows total USD cost for that run next to the summary stats
