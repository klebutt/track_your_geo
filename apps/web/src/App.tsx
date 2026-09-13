import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'
import { RecommendationsList } from './RecommendationsList'
import { ScoreBreakdown } from './ScoreBreakdown'
import { TrendChart, type TrendPoint } from './TrendChart'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

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
  model_name: string
  latency_ms: number
  cost_usd: number
  sentiment: string
  mention_position: string
  relevance_score: number
}

function formatSentiment(sentiment: string): string {
  return sentiment.charAt(0).toUpperCase() + sentiment.slice(1)
}

function formatPosition(position: string): string {
  if (position === 'first_mentioned') return 'First'
  if (position === 'secondary') return 'Secondary'
  if (position === 'not_mentioned') return '—'
  return position
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

type RunListItem = {
  id: number
  created_at: string
  pilot_id: string
  brand_name: string
  status: string
  visibility_rate: number
  total_cost_usd: number
  source_url?: string | null
}

type LossEntry = {
  query: string
  competitors: string[]
}

type DeeperInsight = {
  title: string
  detail: string
}

type PlainReport = {
  ready: boolean
  searches_recommended: number
  searches_total: number
  headline: string
  win_queries: string[]
  loss_queries: string[]
  loss_entries?: LossEntry[]
  gap_summary?: string | null
  models_note?: string | null
  geography_note?: string | null
  what_this_is?: string | null
  meaning?: string | null
  competitor_summary?: string | null
  deeper_insights?: DeeperInsight[]
  deeper_insights_lead?: string | null
  index_note?: string | null
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
  usage_log?: Array<{ phase?: string; model?: string; error?: string }> | null
  source_url?: string | null
  profile_snapshot?: {
    brand_name?: string
    aliases?: string[]
    location?: string
    url?: string
    competitors?: string[]
    queries?: string[]
    brand_domains?: string[]
  } | null
  plain_report?: PlainReport | null
}

type ViewSource = 'demo' | 'url'

function isUrlRunListItem(r: RunListItem): boolean {
  return Boolean(r.source_url) || r.pilot_id.startsWith('url-')
}

function formatProbeTemplate(template: string, brand: string, location: string): string {
  return template.replaceAll('{brand}', brand).replaceAll('{location}', location)
}

function formatRunDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatRunDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

function formatUrlRunOption(r: RunListItem): string {
  return `${r.brand_name} — ${formatRunDate(r.created_at)}`
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json() as Promise<T>
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function pollUntilRunComplete(
  apiBase: string,
  runId: number,
  onProgress: (run: Run) => void,
): Promise<Run> {
  const deadline = Date.now() + 20 * 60 * 1000
  while (Date.now() < deadline) {
    const current = await fetchJson<Run>(`${apiBase}/api/runs/${runId}`)
    onProgress(current)
    if (current.status === 'completed') return current
    if (current.status === 'failed') {
      throw new Error('Analysis run failed on the server. Check API logs and provider keys.')
    }
    await sleep(3000)
  }
  throw new Error(
    'Run is still in progress after 20 minutes. Refresh the page later or check run history.',
  )
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
  const [urlInput, setUrlInput] = useState('')
  const [run, setRun] = useState<Run | null>(null)
  const [runHistory, setRunHistory] = useState<RunListItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [urlRunOptions, setUrlRunOptions] = useState<RunListItem[]>([])
  const [selectedUrlRunId, setSelectedUrlRunId] = useState<number | ''>('')
  const [viewSource, setViewSource] = useState<ViewSource>('demo')
  const [loadingUrlOptions, setLoadingUrlOptions] = useState(false)
  const [loadingUrlRun, setLoadingUrlRun] = useState(false)

  const loadRunHistory = useCallback(
    async (id: string, options?: { setActiveRun?: boolean }) => {
      if (!id) {
        setRunHistory([])
        if (options?.setActiveRun) setRun(null)
        return
      }
      setLoadingHistory(true)
      try {
        const list = await fetchJson<RunListItem[]>(
          `${API_BASE}/api/runs?pilot_id=${encodeURIComponent(id)}&limit=20`,
        )
        const completed = list.filter((r) => r.status === 'completed')
        setRunHistory(completed)
        if (options?.setActiveRun) {
          const latest = completed[0]
          if (latest) {
            const full = await fetchJson<Run>(`${API_BASE}/api/runs/${latest.id}`)
            setRun(full)
            setSelectedUrlRunId('')
          } else {
            setRun(null)
          }
        }
      } catch (e) {
        if (options?.setActiveRun) setRun(null)
        setRunHistory([])
        setError(e instanceof Error ? e.message : 'Failed to load run history')
      } finally {
        setLoadingHistory(false)
      }
    },
    [],
  )

  const loadUrlRunOptions = useCallback(async () => {
    setLoadingUrlOptions(true)
    try {
      const list = await fetchJson<RunListItem[]>(`${API_BASE}/api/runs?limit=50`)
      const urlRuns = list.filter((r) => r.status === 'completed' && isUrlRunListItem(r))
      setUrlRunOptions(urlRuns)
      return urlRuns
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load past URL analyses')
      return [] as RunListItem[]
    } finally {
      setLoadingUrlOptions(false)
    }
  }, [])

  const selectUrlRun = useCallback(
    async (runId: number) => {
      setError(null)
      setViewSource('url')
      setSelectedUrlRunId(runId)
      setLoadingUrlRun(true)
      try {
        const full = await fetchJson<Run>(`${API_BASE}/api/runs/${runId}`)
        setRun(full)
        if (full.source_url) setUrlInput(full.source_url)
        if (full.pilot_id) {
          await loadRunHistory(full.pilot_id, { setActiveRun: false })
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load URL run')
      } finally {
        setLoadingUrlRun(false)
      }
    },
    [loadRunHistory],
  )

  const loadPilots = useCallback(async () => {
    setLoadingPilots(true)
    setError(null)
    try {
      const list = await fetchJson<PilotSummary[]>(`${API_BASE}/api/pilots`)
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
    void loadUrlRunOptions()
  }, [loadUrlRunOptions])

  useEffect(() => {
    if (!pilotId) {
      setPilotDetail(null)
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const d = await fetchJson<PilotDetail>(`${API_BASE}/api/pilots/${encodeURIComponent(pilotId)}`)
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

  // Demo brand owns the active run only while viewSource is 'demo' — never overwrite a URL selection.
  useEffect(() => {
    if (!pilotId || running || viewSource !== 'demo') return
    void loadRunHistory(pilotId, { setActiveRun: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally omit `running`
  }, [pilotId, loadRunHistory, viewSource])

  const trendData = useMemo<TrendPoint[]>(
    () =>
      runHistory.map((r) => ({
        runId: r.id,
        date: r.created_at,
        visibilityPct: r.visibility_rate * 100,
      })),
    [runHistory],
  )

  const resolvedProbes = useMemo(() => {
    if (!pilotDetail) return []
    const b = brand.trim() || pilotDetail.brand_name
    const loc = location.trim() || pilotDetail.location
    return pilotDetail.queries.map((t) => formatProbeTemplate(t, b, loc))
  }, [pilotDetail, brand, location])

  const urlAnalysisProbes = useMemo(() => {
    if (viewSource !== 'url' || !run) return []
    const snapQueries = run.profile_snapshot?.queries
    if (snapQueries?.length) return snapQueries
    const seen = new Set<string>()
    const unique: string[] = []
    for (const q of run.query_results) {
      if (q.query_text && !seen.has(q.query_text)) {
        seen.add(q.query_text)
        unique.push(q.query_text)
      }
    }
    return unique
  }, [viewSource, run])

  const urlCompetitors = useMemo(
    () => (viewSource === 'url' ? run?.profile_snapshot?.competitors ?? [] : []),
    [viewSource, run],
  )

  const brandDomainsHint = useMemo(() => {
    if (viewSource === 'url') {
      const domains = run?.profile_snapshot?.brand_domains
      return domains?.length ? domains.join(', ') : 'heuristic'
    }
    return pilotDetail?.brand_domains?.length
      ? pilotDetail.brand_domains.join(', ')
      : 'heuristic'
  }, [viewSource, run, pilotDetail])

  const probeErrors = useMemo(
    () => (run?.usage_log ?? []).filter((e) => e.phase === 'probe_error'),
    [run],
  )

  const onRun = async () => {
    setViewSource('demo')
    setSelectedUrlRunId('')
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
      const started = await fetchJson<Run>(`${API_BASE}/api/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      setRun(started)
      if (started.status === 'running') {
        const completed = await pollUntilRunComplete(API_BASE, started.id, setRun)
        setRun(completed)
      }
      await loadRunHistory(pilotId)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run failed')
    } finally {
      setRunning(false)
    }
  }

  const onRunFromUrl = async () => {
    const url = urlInput.trim()
    if (!url) {
      setError('Paste a website URL to analyse.')
      return
    }
    setViewSource('url')
    setRunning(true)
    setError(null)
    setRun(null)
    try {
      const started = await fetchJson<Run>(`${API_BASE}/api/runs/from-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, vertical: 'accountants' }),
      })
      setRun(started)
      setSelectedUrlRunId(started.id)
      let finished = started
      if (started.status === 'running') {
        finished = await pollUntilRunComplete(API_BASE, started.id, setRun)
        setRun(finished)
      }
      setSelectedUrlRunId(finished.id)
      if (finished.pilot_id) {
        await loadRunHistory(finished.pilot_id, { setActiveRun: false })
      }
      await loadUrlRunOptions()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'URL analysis failed')
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
          the brand string, extract <strong>sentiment</strong> and <strong>position</strong> when it
          does, and track how often configured competitors appear. After each run, the API generates
          tailored optimization recommendations from sentiment, position, and citation gaps.
        </p>
      </header>

      <div className="disclaimer">
        <strong>Limitations:</strong> Probes fan out to configured models (default: OpenAI search,{' '}
        Perplexity sonar-pro, Gemini 2.5 Flash) — API paths, not consumer chat UIs. Visibility uses
        a substring gate; visible rows get an LLM extraction pass for sentiment and position.{' '}
        <strong>Sources</strong> are domains from provider citation metadata (and URLs in reply
        text). Gemini free tier may rate-limit; partial results are possible. Treat outputs as
        directional.
      </div>

      <section className="panel">
        <h2>1 · Analyse from URL (accountants)</h2>
        <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.9rem' }}>
          Paste a firm website. The API infers name, aliases, location, competitors, and intent
          queries, then runs the usual GEO probes. No multi-field form.
        </p>
        <div className="grid two">
          <div>
            <label htmlFor="url-input">Website URL</label>
            <input
              id="url-input"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://www.example-accountants.co.uk"
              disabled={running}
            />
          </div>
          <div>
            <label>&nbsp;</label>
            <button
              type="button"
              className="primary"
              onClick={() => void onRunFromUrl()}
              disabled={running || !urlInput.trim()}
            >
              {running
                ? `Analysing URL… (${run?.query_results?.length ?? 0} probes)`
                : 'Analyse URL'}
            </button>
          </div>
        </div>
        <div className="grid two" style={{ marginTop: '0.75rem' }}>
          <div>
            <label htmlFor="past-url-run">Past URL analyses</label>
            <select
              id="past-url-run"
              value={selectedUrlRunId === '' ? '' : String(selectedUrlRunId)}
              onChange={(e) => {
                const raw = e.target.value
                if (!raw) {
                  setSelectedUrlRunId('')
                  return
                }
                void selectUrlRun(Number(raw))
              }}
              disabled={running || loadingUrlRun || loadingUrlOptions || urlRunOptions.length === 0}
            >
              <option value="">
                {loadingUrlOptions
                  ? 'Loading…'
                  : urlRunOptions.length === 0
                    ? 'No completed URL analyses yet'
                    : 'Select a past analysis…'}
              </option>
              {urlRunOptions.map((r) => (
                <option key={r.id} value={r.id}>
                  {formatUrlRunOption(r)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>&nbsp;</label>
            <p style={{ margin: '0.55rem 0 0', color: '#64748b', fontSize: '0.85rem' }}>
              {loadingUrlRun
                ? 'Loading selected run…'
                : 'Opens a finished URL run without spending again. All sections below follow this selection.'}
            </p>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>2 · Demo brand and run</h2>
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
                onChange={(e) => {
                  setViewSource('demo')
                  setPilotId(e.target.value)
                }}
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
                {running
                  ? `Running probes… (${run?.query_results?.length ?? 0} complete)`
                  : 'Run analysis'}
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

      {run && (
        <>
          {run.plain_report?.ready ? (
            <section className="panel plain-report">
              <h2>Your AI recommendation report</h2>
              {run.plain_report.what_this_is ? (
                <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.95rem', maxWidth: '65ch' }}>
                  {run.plain_report.what_this_is}
                </p>
              ) : null}
              <p className="plain-report-headline">{run.plain_report.headline}</p>
              <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.95rem', maxWidth: '65ch' }}>
                That is {run.plain_report.searches_recommended} of {run.plain_report.searches_total}{' '}
                customer-intent questions where at least one AI reply named{' '}
                <strong>{run.brand_name}</strong>.
              </p>

              <h3 className="insights-subheading">Who showed up instead</h3>
              {(run.plain_report.loss_entries?.length ?? 0) > 0 ? (
                <>
                  {run.plain_report.competitor_summary ? (
                    <p style={{ maxWidth: '65ch', marginTop: 0 }}>{run.plain_report.competitor_summary}</p>
                  ) : null}
                  <ul className="plain-report-list">
                    {(run.plain_report.loss_entries ?? []).map((entry) => (
                      <li key={entry.query}>
                        <strong>{entry.competitors.join(', ')}</strong>
                        <span style={{ color: '#64748b' }}> - on “{entry.query}”</span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p style={{ color: '#64748b', fontSize: '0.9rem', maxWidth: '65ch' }}>
                  {run.plain_report.competitor_summary ||
                    'No tracked competitors were named on searches where you were missing.'}
                </p>
              )}

              {run.plain_report.win_queries.length > 0 ? (
                <>
                  <h3 className="insights-subheading">Where you appeared</h3>
                  <ul className="plain-report-list">
                    {run.plain_report.win_queries.map((q) => (
                      <li key={q}>{q}</li>
                    ))}
                  </ul>
                </>
              ) : null}

              <h3 className="insights-subheading">What this means</h3>
              <p style={{ maxWidth: '65ch' }}>
                {run.plain_report.meaning || run.plain_report.gap_summary}
              </p>
              {run.plain_report.geography_note ? (
                <p style={{ maxWidth: '65ch', color: '#64748b', fontSize: '0.9rem' }}>
                  {run.plain_report.geography_note}
                </p>
              ) : null}

              {(run.plain_report.deeper_insights?.length ?? 0) > 0 ? (
                <>
                  <h3 className="insights-subheading">Optional deeper next steps</h3>
                  <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.9rem', maxWidth: '65ch' }}>
                    {run.plain_report.deeper_insights_lead ||
                      'One-off options typically in the £5-20 range if you want to go further - reply if any of these would help.'}
                  </p>
                  <ul className="plain-report-list deeper-insights-list">
                    {(run.plain_report.deeper_insights ?? []).map((item) => (
                      <li key={item.title}>
                        <strong>{item.title}</strong>
                        <div style={{ color: '#475569', fontSize: '0.9rem', marginTop: '0.2rem' }}>
                          {item.detail}
                        </div>
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}

              {run.plain_report.models_note ? (
                <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: 0, maxWidth: '70ch' }}>
                  {run.plain_report.models_note}
                </p>
              ) : null}
            </section>
          ) : null}

          <section className="panel">
            <h2>3 · Summary</h2>
            <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.9rem' }}>
              Last probe: <time dateTime={run.created_at}>{formatRunDateTime(run.created_at)}</time>
              {run.source_url ? (
                <>
                  {' '}
                  · Source:{' '}
                  <a href={run.source_url} target="_blank" rel="noreferrer">
                    {run.source_url}
                  </a>
                </>
              ) : null}
              {run.brand_name && run.brand_name !== '(inferring…)' ? (
                <>
                  {' '}
                  · Inferred brand: <strong>{run.brand_name}</strong>
                  {run.location ? ` (${run.location})` : ''}
                </>
              ) : null}
            </p>
            <div className="stats">
              <div className="stat">
                <div className="k">Visibility rate</div>
                <div className="v">{(run.visibility_rate * 100).toFixed(0)}%</div>
              </div>
              <div className="stat">
                <div className="k">Composite index</div>
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
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: 0, maxWidth: '70ch' }}>
              {run.plain_report?.index_note ||
                'Visibility = how often you appear in these replies. The composite index also reflects how strongly you are recommended, the tone when you are mentioned, and whether you are cited as a source - a compass, not a replica of consumer ChatGPT.'}{' '}
              Tokens: {run.total_prompt_tokens} prompt + {run.total_completion_tokens} completion.
              {probeErrors.length > 0 && (
                <>
                  {' '}
                  <strong style={{ color: '#b45309' }}>
                    {probeErrors.length} probe(s) failed
                  </strong>{' '}
                  (often Gemini quota or a missing key) — results below are partial.
                </>
              )}
            </p>
          </section>

          <section className="panel">
            <h2>4 · Visibility trend</h2>
            <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.9rem', maxWidth: '65ch' }}>
              Historical visibility rate across completed runs for this brand
              {loadingHistory ? ' (loading…)' : ''}.
            </p>
            <TrendChart data={trendData} />
          </section>

          <section className="panel">
            <h2>4 · Insights &amp; optimization</h2>
            <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.9rem', maxWidth: '65ch' }}>
              Operator depth: how the composite index is calculated, plus LLM-generated actions from
              this run&apos;s visibility, sentiment, position, and citation gaps (not the customer
              hero report above).
            </p>
            <ScoreBreakdown compositeScore={run.composite_score} queryResults={run.query_results} />
            <h3 className="insights-subheading">Operator recommended actions</h3>
            <RecommendationsList recommendations={run.recommendations} />
          </section>
        </>
      )}

      {viewSource === 'url' && urlAnalysisProbes.length > 0 ? (
        <section className="panel">
          <h2>5 · Neutral GEO probes used in this analysis</h2>
          <p style={{ marginTop: 0, color: '#64748b', maxWidth: '65ch' }}>
            These are the brand-neutral questions that were probed for the selected URL run. None of
            them include the tracked brand name in the prompt.
          </p>
          {urlCompetitors.length > 0 && (
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginTop: 0 }}>
              Competitor substring checks:{' '}
              <span className="mono">{urlCompetitors.join(', ')}</span>
            </p>
          )}
          <ol className="probe-list" style={{ marginBottom: 0 }}>
            {urlAnalysisProbes.map((q) => (
              <li key={q} style={{ marginBottom: '0.5rem' }}>
                <span className="mono" style={{ fontSize: '0.82rem' }}>
                  {q}
                </span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {viewSource === 'demo' && pilotDetail && resolvedProbes.length > 0 ? (
        <section className="panel">
          <h2>5 · Neutral GEO probes for this scenario</h2>
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
      ) : null}

      {run && (
        <>
          <section className="panel">
            <h2>6 · Query-level results</h2>
            <p style={{ marginTop: 0, fontSize: '0.85rem', color: '#64748b' }}>
              Domains from web-search citation metadata per probe. Teal = brand-owned (
              {brandDomainsHint}
              ). Higher cost than plain chat — see run total.
            </p>
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Brand?</th>
                    <th>Sentiment</th>
                    <th>Position</th>
                    <th>Model</th>
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
                      <td>
                        <span
                          className={`badge sentiment-${q.sentiment ?? 'neutral'}`}
                          title={`Relevance: ${(q.relevance_score ?? 0).toFixed(2)}`}
                        >
                          {formatSentiment(q.sentiment ?? 'neutral')}
                        </span>
                      </td>
                      <td>{formatPosition(q.mention_position ?? 'not_mentioned')}</td>
                      <td className="mono" style={{ fontSize: '0.72rem', maxWidth: '120px' }}>
                        {q.model_name || '—'}
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
            <h2>7 · Full model replies</h2>
            {run.query_results.map((q) => (
              <details key={`ex-${q.id}`} style={{ marginBottom: '0.75rem' }}>
                <summary className="mono" style={{ cursor: 'pointer', fontSize: '0.8rem' }}>
                  {q.model_name ? `[${q.model_name}] ` : ''}
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
        </>
      )}
    </div>
  )
}

export default App
