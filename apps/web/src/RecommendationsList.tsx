type Recommendation = {
  id: number
  title: string
  detail: string
  impact: string
  category: string
}

const CATEGORY_LABELS: Record<string, string> = {
  website: 'Website / SEO',
  third_party: 'Third-party content',
  pr_comms: 'PR / brand',
  technical: 'Technical',
  other: 'Other',
}

const CATEGORY_ICONS: Record<string, string> = {
  website: '🌐',
  third_party: '📰',
  pr_comms: '📣',
  technical: '⚙️',
  other: '💡',
}

function formatImpact(impact: string): string {
  const normalized = impact.toLowerCase()
  if (normalized === 'high') return 'High impact'
  if (normalized === 'low') return 'Low impact'
  return 'Medium impact'
}

type Props = {
  recommendations: Recommendation[]
}

export function RecommendationsList({ recommendations }: Props) {
  if (recommendations.length === 0) {
    return (
      <p className="insights-empty">
        No recommendations were generated for this run. Re-run the analysis or check API logs if this
        persists.
      </p>
    )
  }

  return (
    <div className="recommendations-grid">
      {recommendations.map((rec) => {
        const category = rec.category.toLowerCase()
        return (
          <article key={rec.id} className={`rec-card impact-${rec.impact.toLowerCase()}`}>
            <div className="rec-card-head">
              <span className="rec-category" title={CATEGORY_LABELS[category] ?? category}>
                {CATEGORY_ICONS[category] ?? '💡'}{' '}
                {CATEGORY_LABELS[category] ?? rec.category}
              </span>
              <span className={`rec-impact impact-${rec.impact.toLowerCase()}`}>
                {formatImpact(rec.impact)}
              </span>
            </div>
            <h3>{rec.title}</h3>
            <p>{rec.detail}</p>
          </article>
        )
      })}
    </div>
  )
}
