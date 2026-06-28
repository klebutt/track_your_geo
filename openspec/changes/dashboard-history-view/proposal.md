# OpenSpec Proposal: Dashboard History View

## Goal
Improve the dashboard UX by automatically loading the most recent analysis for a selected brand and displaying a historical trend chart.

## Problem
Currently, the UI starts empty when a brand is selected. A user must trigger a new (expensive and slow) run to see any results, even if a run was completed minutes ago. Furthermore, there is no way to visualize how a brand's GEO visibility is changing over time.

## Solution
1. **API Enhancement:** Add a filtered list/latest endpoint for runs.
2. **Auto-Loading:** On brand selection, the frontend automatically fetches and displays the most recent completed run.
3. **Trend Visualization:** Add a line chart showing "Visibility Rate" and "Citation Count" across all historical runs for the selected brand.

## Impact
- **Instant Value:** Demos become faster and more impressive as data appears immediately.
- **Strategic Insight:** Users can see if their optimization efforts are actually improving their visibility over time.
- **Cost Savings:** Reduces unnecessary "test" runs just to see the UI populated.

## Cost
$0. No LLM calls. Purely database and frontend work.
