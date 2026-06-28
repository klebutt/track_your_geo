# OpenSpec Proposal: Structured Extraction

## Goal
Replace the binary substring visibility check with deep structured extraction using an LLM. This unlocks sentiment and mention position data, allowing for a fully spec-compliant GEO score.

## Problem
Currently, the prototype uses a simple case-insensitive substring search to determine if a brand is mentioned. This is effective for a basic "yes/no" visibility rate, but fails to capture:
1. **Sentiment:** Is the brand being recommended positively or negatively?
2. **Mention Position:** Is the brand the first recommendation or buried at the bottom?
3. **Accuracy:** Substring matches can sometimes lead to false positives (e.g., matching "Dish" for "Dishoom").

## Solution
1. **Visibility Gate:** Retain the substring match as a fast, free first pass.
2. **LLM Extraction:** Only if the brand is detected via substring, perform a second cheap LLM call (e.g., `gpt-4o-mini`) using structured output (JSON mode) to extract:
    - `sentiment`: (positive, neutral, negative)
    - `position`: (first_mentioned, secondary, not_mentioned)
    - `relevance_score`: (0.0 to 1.0)
3. **Database Update:** Store these new fields on the `query_results` table.
4. **GEO Score Formula:** Update the `composite_score` calculation to include these components as per the technical spec.

## Impact
- **Intelligence:** Moves the product from a simple "keyword tracker" to a true sentiment and visibility analysis engine.
- **Reporting:** Allows for "Brand Sentiment" and "Average Share of Voice (Position)" reporting.
- **Spec Compliance:** Fully implements the core logic of the GEO Tracker Technical Core.

## Cost
~$0.001 per visible query result. Total run cost impact: negligible (< $0.03 extra per full pilot).
