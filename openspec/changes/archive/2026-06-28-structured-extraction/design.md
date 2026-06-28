# OpenSpec Design: Structured Extraction

## 1. Database Changes (`apps/api/tygeo/models.py`)
Add the following columns to the `QueryResult` table:
- `sentiment`: `String(32)` (positive, neutral, negative)
- `mention_position`: `String(32)` (first_mentioned, secondary, not_mentioned)
- `relevance_score`: `Float` (default 0.0)

## 2. Core Logic (`apps/api/tygeo/execute.py` or `llm.py`)

### The Extraction Prompt
Create a new function `extract_mention_details(answer_text, brand_name)` that uses a concise prompt:
> "Analyze the following AI response for mentions of the brand '{brand_name}'. 
> Return a JSON object with:
> - 'sentiment': one of [positive, neutral, negative]
> - 'position': one of [first_mentioned, secondary, not_mentioned]
> - 'relevance': a score from 0.0 to 1.0 reflecting how prominently the brand is featured."

### Integration in the Pipeline
In `execute_run`:
1. Perform the existing substring match check (`is_visible`).
2. If `is_visible` is `True`:
    - Call `extract_mention_details` using a fast model (e.g., `gpt-4o-mini`).
    - Update the result object with the extracted values.
3. If `is_visible` is `False`:
    - Set defaults: `sentiment='neutral'`, `position='not_mentioned'`, `relevance=0.0`.

## 3. GEO Score Update (`apps/api/tygeo/scoring.py`)
Update the `calculate_composite_score` function to follow the spec formula (documented in `docs/geo-scoring-formula.md`):
- **Visibility:** 40% (Is the brand there?)
- **Position:** 30% (Is it first? First = 1.0, Secondary = 0.5, Not Mentioned = 0)
- **Sentiment:** 20% (Positive = 1.0, Neutral = 0.5, Negative = 0)
- **Citation Volume:** 10% (Number of citations capped at 5; 1.0 for 5+, scaled linearly below that)

## 4. Frontend Changes (`apps/web/`)
Update the `ResultsTable` to include two new columns:
- **Sentiment:** Display as text or color-coded chips (Green/Gray/Red).
- **Position:** Display as "First" or "Secondary".

## 5. Cost Tracking
Ensure the extra extraction call cost is added to the `Run.total_cost_usd`.
