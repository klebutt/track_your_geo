import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'

type PilotSummary = {
  id: string
  brand_name: string
  location: string
  query_count: number
}

type PilotDetail = PilotSummary & {
  competitors: string[]
  queries: string[]
  seed_domains: string[]
  brand_domains: string[]
}

type CitedDomain = {
  domain: string
  kind: 'brand_owned' | 'third_party'
}

type QueryResult = {
  id: number
  query_text: string
  response_text: string
  brand_mentioned: boolean
  competitors_mentioned: Record<string, boolean> | null
  cited_domains: CitedDomain[]
  latency_ms: number
  cost_usd: number
}

function CitedDomainChips({ cited }: { cited: CitedDomain[] | undefined }) {
  if (!cited?.length) {
    return <span className="cited-empty">No domains cited</span>
  }
  return (
    <div className="cited-domains">
      {cited.map((c) => (
        <span key={c.domain} className={`domain-chip ${c.kind}`} title={c.kind === 'brand_owned' ? 'Brand-owned domain' : 'Third-party domain'}>
          {c.domain}
          {c.kind === 'brand_owned' ? ' · yours' : ''}
        </span>
      ))}
    </div>
  )
}

type Recommendation = {
  id: number
  title: string
  detail: string
  impact: string
  category: string
}

type Run = {
  id: number
  created_at: string
  pilot_id: string
  brand_name: string
  location: string
  model_name: string
  status: string
  total_cost_usd: number
  total_prompt_tokens: number
  total_completion_tokens: number
  visibility_rate: number
  composite_score: number
  query_results: QueryResult[]
  recommendations: Recommendation[]
}

function formatProbeTemplate(template: string, brand: string, location: string): string {
  return template.replaceAll('{brand}', brand).replaceAll('{location}', location)
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json() as Promise<T>
}

function App() {
  const [pilots, setPilots] = useState<PilotSummary[]>([])
  const [pilotId, setPilotId] = useState('')
  const [pilotDetail, setPilotDetail] = useState<PilotDetail | null>(null)
  const [brand, setBrand] = useState('')
  const [location, setLocation] = useState('')
  const [loadingPilots, setLoadingPilots] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [run, setRun] = useState<Run | null>(null)

  const loadPilots = useCallback(async () => {
    setLoadingPilots(true)
    setError(null)
    try {
      const list = await fetchJson<PilotSummary[]>('/api/pilots')
      setPilots(list)
      setPilotId((prev) =>
        prev && list.some((p) => p.id === prev) ? prev : (list[0]?.id ?? ''),
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load demo brands')
    } finally {
      setLoadingPilots(false)
    }
  }, [])

  useEffect(() => {
    void loadPilots()
  }, [loadPilots])

  useEffect(() => {
    if (!pilotId) {
      setPilotDetail(null)
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const d = await fetchJson<PilotDetail>(`/api/pilots/${encodeURIComponent(pilotId)}`)
        if (!cancelled) {
          setPilotDetail(d)
          setBrand(d.brand_name)
          setLocation(d.location)
        }
      } catch {
        if (!cancelled) setPilotDetail(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [pilotId])

  const resolvedProbes = useMemo(() => {
    if (!pilotDetail) return []
    const b = brand.trim() || pilotDetail.brand_name
    const loc = location.trim() || pilotDetail.location
    return pilotDetail.queries.map((t) => formatProbeTemplate(t, b, loc))
  }, [pilotDetail, brand, location])

  const onRun = async () => {
    setRunning(true)
    setError(null)
    setRun(null)
    try {
      const body: {
        pilot_id: string
        brand_name?: string
        location?: string
      } = { pilot_id: pilotId }
      if (brand.trim()) body.brand_name = brand.trim()
      if (location.trim()) body.location = location.trim()
      const r = await fetchJson<Run>('/api/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      setRun(r)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run failed')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="app">
      <header>
        <span className="tag">Prototype</span>
        <h1>Track Your GEO</h1>
        <p style={{ margin: '0.35rem 0 0', color: '#64748b', maxWidth: '62ch' }}>
          Simulated GEO visibility: the API runs a bank of <strong>brand-neutral</strong> user-style
          questions (they never name your brand). We measure whether the model&apos;s reply contains
          the brand string and how often configured competitors appear. Recommendations are
          disabled in this build.
        </p>
      </header>

      <div className="disclaimer">
        <strong>Limitations:</strong> Probes use OpenAI&apos;s <strong>web search</strong> model (
        <span className="mono">gpt-4o-mini-search-preview</span>) — closer to search-style answers
        but not identical to consumer ChatGPT. Visibility uses a{' '}
        <strong>case-insensitive substring</strong> match on the brand name.{' '}
        <strong>Sources</strong> are domains from search citation metadata (and any URLs in the
        reply text). Treat outputs as directional.
      </div>

      <section className="panel">
        <h2>1 · Demo brand and run</h2>
        {loadingPilots ? (
          <p>Loading demo brands…</p>
        ) : pilots.length === 0 ? (
          <p className="error">No demo brands configured. Check API built-in pilots.</p>
        ) : (
          <div className="grid two">
            <div>
              <label htmlFor="pilot">Demo brand</label>
              <select
                id="pilot"
                value={pilotId}
                onChange={(e) => setPilotId(e.target.value)}
                disabled={running}
              >
                {pilots.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.brand_name} — {p.location} ({p.query_count} neutral probes)
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>&nbsp;</label>
              <button type="button" className="primary" onClick={() => void onRun()} disabled={running || !pilotId}>
                {running ? 'Running probes…' : 'Run analysis'}
              </button>
            </div>
            <div>
              <label htmlFor="brand">Brand override (optional)</label>
              <input id="brand" value={brand} onChange={(e) => setBrand(e.target.value)} disabled={running} />
            </div>
            <div>
              <label htmlFor="loc">Location override (optional)</label>
              <input id="loc" value={location} onChange={(e) => setLocation(e.target.value)} disabled={running} />
            </div>
          </div>
        )}
        {error && <div className="error mono">{error}</div>}
      </section>

      {pilotDetail && resolvedProbes.length > 0 && (
        <section className="panel">
          <h2>2 · Neutral GEO probes for this scenario</h2>
          <p style={{ marginTop: 0, color: '#64748b', maxWidth: '65ch' }}>
            These are the exact questions sent for the next run (with your brand and location
            substituted where <span className="mono">{'{location}'}</span> appears). None of them
            include the tracked brand name in the prompt.
          </p>
          {pilotDetail.competitors.length > 0 && (
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginTop: 0 }}>
              Competitor substring checks:{' '}
              <span className="mono">{pilotDetail.competitors.join(', ')}</span>
            </p>
          )}
          <ol className="probe-list" style={{ marginBottom: 0 }}>
            {resolvedProbes.map((q) => (
              <li key={q} style={{ marginBottom: '0.5rem' }}>
                <span className="mono" style={{ fontSize: '0.82rem' }}>
                  {q}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {run && (
        <>
          <section className="panel">
            <h2>3 · Summary</h2>
            <div className="stats">
              <div className="stat">
                <div className="k">Visibility rate</div>
                <div className="v">{(run.visibility_rate * 100).toFixed(0)}%</div>
              </div>
              <div className="stat">
                <div className="k">Composite score (v0.1)</div>
                <div className="v">{run.composite_score.toFixed(1)}</div>
              </div>
              <div className="stat">
                <div className="k">Neutral probes run</div>
                <div className="v">{run.query_results.length}</div>
              </div>
              <div className="stat">
                <div className="k">Run cost (USD)</div>
                <div className="v">${run.total_cost_usd.toFixed(4)}</div>
              </div>
              <div className="stat">
                <div className="k">Model</div>
                <div className="v mono" style={{ fontSize: '0.85rem' }}>
                  {run.model_name}
                </div>
              </div>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: 0 }}>
              Visibility = fraction of probes where the assistant text contained &quot;
              {run.brand_name}&quot; (substring). Tokens: {run.total_prompt_tokens} prompt +{' '}
              {run.total_completion_tokens} completion.
            </p>
          </section>

          <section className="panel">
            <h2>4 · Query-level results</h2>
            <p style={{ marginTop: 0, fontSize: '0.85rem', color: '#64748b' }}>
              Domains from web-search citation metadata per probe. Teal = brand-owned (
              {pilotDetail?.brand_domains?.length
                ? pilotDetail.brand_domains.join(', ')
                : 'heuristic'}
              ). Higher cost than plain chat — see run total.
            </p>
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Brand?</th>
                    <th>Query</th>
                    <th>Sources (domains)</th>
                    <th>Competitors mentioned</th>
                    <th>Latency</th>
                    <th>Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {run.query_results.map((q) => (
                    <tr key={q.id} className={q.brand_mentioned ? '' : 'miss'}>
                      <td>
                        <span className={q.brand_mentioned ? 'badge ok' : 'badge no'}>
                          {q.brand_mentioned ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td style={{ maxWidth: '280px' }}>
                        <div className="mono" style={{ fontSize: '0.78rem' }}>
                          {q.query_text}
                        </div>
                      </td>
                      <td style={{ minWidth: '140px' }}>
                        <CitedDomainChips cited={q.cited_domains} />
                      </td>
                      <td>
                        {q.competitors_mentioned
                          ? Object.entries(q.competitors_mentioned)
                              .filter(([, v]) => v)
                              .map(([k]) => k)
                              .join(', ') || '—'
                          : '—'}
                      </td>
                      <td>{q.latency_ms.toFixed(0)} ms</td>
                      <td>${q.cost_usd.toFixed(5)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <h2>5 · Full model replies</h2>
            {run.query_results.map((q) => (
              <details key={`ex-${q.id}`} style={{ marginBottom: '0.75rem' }}>
                <summary className="mono" style={{ cursor: 'pointer', fontSize: '0.8rem' }}>
                  {q.query_text.slice(0, 80)}
                  {q.query_text.length > 80 ? '…' : ''}
                </summary>
                <div style={{ margin: '0.5rem 0' }}>
                  <CitedDomainChips cited={q.cited_domains} />
                </div>
                <pre
                  style={{
                    whiteSpace: 'pre-wrap',
                    fontSize: '0.82rem',
                    background: '#f8fafc',
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                  }}
                >
                  {q.response_text}
                </pre>
              </details>
            ))}
          </section>

          {run.recommendations.length > 0 && (
            <section className="panel">
              <h2>Recommended actions</h2>
              {run.recommendations.map((r) => (
                <div key={r.id} className="rec">
                  <div className="impact">
                    {r.impact} · {r.category}
                  </div>
                  <h3>{r.title}</h3>
                  <p>{r.detail}</p>
                </div>
              ))}
            </section>
          )}
        </>
      )}
    </div>
  )
}

export default App
