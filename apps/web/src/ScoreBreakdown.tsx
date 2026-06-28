type QueryResultLike = {
  brand_mentioned: boolean
  mention_position: string
  sentiment: string
  cited_domains?: unknown[]
}

type ScoreComponents = {
  visibility: number
  position: number
  sentiment: number
  citations: number
}

function computeComponents(rows: QueryResultLike[]): ScoreComponents {
  const n = rows.length || 1
  let vis = 0
  let pos = 0
  let sent = 0
  let cit = 0
  for (const q of rows) {
    vis += q.brand_mentioned ? 1 : 0
    pos +=
      q.mention_position === 'first_mentioned'
        ? 1
        : q.mention_position === 'secondary'
          ? 0.5
          : 0
    sent += q.sentiment === 'positive' ? 1 : q.sentiment === 'neutral' ? 0.5 : 0
    cit += Math.min(1, (q.cited_domains?.length ?? 0) / 5)
  }
  return {
    visibility: (vis / n) * 40,
    position: (pos / n) * 30,
    sentiment: (sent / n) * 20,
    citations: (cit / n) * 10,
  }
}

const WEIGHTS = [
  { key: 'visibility' as const, label: 'Visibility', weight: '40%' },
  { key: 'position' as const, label: 'Position', weight: '30%' },
  { key: 'sentiment' as const, label: 'Sentiment', weight: '20%' },
  { key: 'citations' as const, label: 'Citations', weight: '10%' },
]

type Props = {
  compositeScore: number
  queryResults: QueryResultLike[]
}

export function ScoreBreakdown({ compositeScore, queryResults }: Props) {
  const components = computeComponents(queryResults)

  return (
    <div className="score-breakdown">
      <div className="score-breakdown-header">
        <div>
          <div className="score-breakdown-label">GEO score</div>
          <div className="score-breakdown-value">{compositeScore.toFixed(1)} / 100</div>
        </div>
        <p className="score-breakdown-note">
          Weighted average across neutral probes: visibility gate (40%), mention position (30%),
          sentiment when visible (20%), cited domains (10%).
        </p>
      </div>
      <div className="score-breakdown-bars">
        {WEIGHTS.map(({ key, label, weight }) => (
          <div key={key} className="score-bar-row">
            <div className="score-bar-meta">
              <span>{label}</span>
              <span className="score-bar-weight">{weight}</span>
            </div>
            <div className="score-bar-track">
              <div
                className={`score-bar-fill score-bar-${key}`}
                style={{ width: `${Math.min(100, (components[key] / parseFloat(weight)) * 100)}%` }}
              />
            </div>
            <div className="score-bar-points">{components[key].toFixed(1)} pts</div>
          </div>
        ))}
      </div>
    </div>
  )
}
