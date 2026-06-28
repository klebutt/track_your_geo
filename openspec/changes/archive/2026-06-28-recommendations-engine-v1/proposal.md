# OpenSpec Proposal: Recommendations Engine v1

## Goal
Transform the "Recommendations" feature from a placeholder into a high-value, actionable advisor. This moves the product from "monitoring" (what happened) to "optimization" (what to do next).

## Problem
The existing recommendation logic is disabled and uses very basic data (just binary visibility). It doesn't leverage the rich sentiment, position, and citation data we just built, making its advice generic.

## Solution
1. **Enriched Prompt:** Update `run_recommendations` to include a deep analysis of:
    - Sentiment patterns (e.g., "Your competitors are consistently more positive than you")
    - Position gaps ("You are visible but always in 3rd place")
    - Citation "misses" ("Competitors are cited on Domain X, Y, and Z, but you are not")
2. **Actionable Categories:** Refine the categories to: `Website/SEO`, `Third-Party Content`, `PR/Brand`, `Technical`.
3. **UI Integration:** Add a new **"Insights & Optimization"** section underneath the visibility trend chart.
4. **Scoring Transparency:** Include a clear visual breakdown/explanation of how the GEO score is derived (Visibility 40%, Position 30%, Sentiment 20%, Citations 10%).

## Impact
- **Sales Conversion:** Pilots become much more compelling when they provide a "to-do list" for the customer.
- **Strategic Value:** Connects the raw data to real-world marketing actions.

## Cost
~$0.005 per run.
