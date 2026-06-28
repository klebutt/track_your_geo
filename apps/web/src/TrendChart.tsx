import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export type TrendPoint = {
  runId: number
  date: string
  visibilityPct: number
}

type TrendChartProps = {
  data: TrendPoint[]
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function TrendChart({ data }: TrendChartProps) {
  if (data.length === 0) {
    return (
      <p style={{ margin: 0, color: '#64748b', fontSize: '0.9rem' }}>
        No completed runs yet for this brand.
      </p>
    )
  }

  const sorted = [...data].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )

  return (
    <div className="trend-chart" style={{ width: '100%', height: 240 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={sorted} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fontSize: 12, fill: '#64748b' }}
            stroke="#cbd5e1"
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 12, fill: '#64748b' }}
            stroke="#cbd5e1"
            width={48}
          />
          <Tooltip
            labelFormatter={(label) => formatDate(String(label))}
            formatter={(value: number) => [`${value.toFixed(0)}%`, 'Visibility']}
            contentStyle={{
              borderRadius: 8,
              border: '1px solid #e2e8f0',
              fontSize: '0.85rem',
            }}
          />
          <Line
            type="monotone"
            dataKey="visibilityPct"
            stroke="#0ea5e9"
            strokeWidth={2}
            dot={{ r: 4, fill: '#0ea5e9' }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
