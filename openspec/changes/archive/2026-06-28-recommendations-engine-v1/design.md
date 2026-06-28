# OpenSpec Design: Recommendations Engine v1

## 1. Backend: Enriched Logic (`apps/api/tygeo/analysis.py`)

### Input Data Prep
Update `execute_run` to gather richer summary data after all probes are complete:
- `avg_sentiment`: Breakdown of pos/neu/neg.
- `avg_position`: Mean position score.
- `citation_gaps`: List of top domains citing competitors but NOT the brand.

### Prompt Refinement (`llm.py`)
Update the `run_recommendations` prompt:
> "You are a GEO Optimization Expert. Analyze this data:
> - Brand: {brand}
> - Visibility: {vis}% | Sentiment: {sent} | Position: {pos}
> - Competitor wins: {competitors}
> - Citation Gaps: {citations}
> 
> Task: Provide 3-5 specific, high-impact recommendations to improve their Generative Engine Optimization score."

## 2. Frontend: Insights & Optimization Section (`apps/web/`)

### Layout
Insert a new section between the **Trend Chart** and the **Neutral Probes Table**.

### Component: Score Breakdown
A simple visual guide (using progress bars or a pie chart) showing:
- **GEO Score: XX/100**
- *How it's calculated:* [40% Visibility] [30% Position] [20% Sentiment] [10% Citations]

### Component: Recommendation Cards
Display the array of recommendations from the API as cards with:
- **Impact Badge:** (High/Med/Low)
- **Category Icon:** (Website, PR, etc.)
- **Action Title & Detailed Advice**

## 3. Data Integration
- Ensure `POST /api/runs` triggers `run_recommendations` at the very end of the background task.
- Update `RunOut` schema to include the `recommendations` list.
