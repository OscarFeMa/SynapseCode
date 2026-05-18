import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Download, Calendar, TrendingUp, MessageSquare, Scale,
  Clock, ChevronLeft, ChevronRight, Loader2, FileDown,
} from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import { format, subDays, parseISO } from 'date-fns'
import { es } from 'date-fns/locale'

const COLORS = ['#23403B', '#4A7C59', '#6E8B74', '#B98B4D', '#8B3A3A']

const statusBadge = {
  COMPLETED: 'badge-success',
  FAILED: 'badge-error',
  RUNNING: 'badge-neutral',
  CREATED: 'badge-neutral',
}

const consensusText = {
  CONSENSUS_REACHED: 'text-[#4A7C59]',
  PARTIAL_CONSENSUS: 'text-[#B98B4D]',
  DIVERGENT: 'text-[#8B3A3A]',
}

export function HistoryPage() {
  const [debates, setDebates] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [dateRange, setDateRange] = useState(30)
  const perPage = 10

  useEffect(() => {
    fetchDebates()
  }, [page, dateRange])

  const fetchDebates = async () => {
    setLoading(true)
    try {
      const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      const res = await fetch(
        `${base}/api/v1/sessions?page=${page}&limit=${perPage}&days=${dateRange}`
      )
      if (res.ok) {
        const data = await res.json()
        setDebates(data.items || data.sessions || [])
        setTotal(data.total || 0)
      }
    } catch (e) {
      console.error('Failed to fetch debates:', e)
    } finally {
      setLoading(false)
    }
  }

  const totalPages = Math.ceil(total / perPage)

  const stats = computeStats(debates, total)
  const trendData = buildTrendData(debates, dateRange)
  const consensusData = buildConsensusPie(debates)
  const modelData = buildModelUsage(debates)

  const handleExportCSV = () => {
    const headers = ['ID', 'Tema', 'Estado', 'Consenso', 'Turnos', 'Tokens IN', 'Tokens OUT', 'Fecha']
    const rows = debates.map((d) => [
      d.id,
      `"${(d.topic || '').replace(/"/g, '""')}"`,
      d.status || 'UNKNOWN',
      d.consensus_level || '-',
      d.turns?.length || 0,
      d.turns?.reduce((s, t) => s + (t.tokens_in || 0), 0) || 0,
      d.turns?.reduce((s, t) => s + (t.tokens_out || 0), 0) || 0,
      d.created_at || '-',
    ])
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `synapse_history_${format(new Date(), 'yyyy-MM-dd')}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl text-[#161616]">Historico</h1>
          <p className="text-sm text-[#5C5C5C] mt-1">
            {total} debates en los ultimos {dateRange} dias
          </p>
          <div className="w-8 h-0.5 bg-[#23403B] mt-3" />
        </div>
        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => {
              setDateRange(Number(e.target.value))
              setPage(1)
            }}
            className="bg-white border border-[rgba(0,0,0,0.08)] rounded px-3 py-2 text-sm text-[#161616] focus:outline-none focus:border-[rgba(0,0,0,0.16)]"
          >
            <option value={7}>7 dias</option>
            <option value={30}>30 dias</option>
            <option value={90}>90 dias</option>
          </select>
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-3 py-2 btn-secondary text-sm"
          >
            <FileDown className="w-4 h-4" />
            CSV
          </button>
        </div>
      </div>

      {/* KPI summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          icon={MessageSquare}
          label="Total Debates"
          value={stats.total}
          accent="text-[#23403B]"
        />
        <KpiCard
          icon={Scale}
          label="Tasa Consenso"
          value={`${stats.consensusRate}%`}
          accent="text-[#4A7C59]"
        />
        <KpiCard
          icon={Clock}
          label="Prom. Turnos"
          value={stats.avgTurns.toFixed(1)}
          accent="text-[#6E8B74]"
        />
        <KpiCard
          icon={TrendingUp}
          label="Prom. Tokens"
          value={formatTokens(stats.avgTokens)}
          accent="text-[#B98B4D]"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Debates por dia */}
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <h3 className="text-sm font-medium text-[#161616] mb-4">Debates por Dia</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={trendData}>
              <defs>
                <linearGradient id="colorDebates" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#23403B" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#23403B" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#8A8780' }} />
              <YAxis tick={{ fontSize: 11, fill: '#8A8780' }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: '#FFFFFF',
                  border: '1px solid rgba(0,0,0,0.08)',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#23403B"
                fillOpacity={1}
                fill="url(#colorDebates)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Tokens por dia */}
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <h3 className="text-sm font-medium text-[#161616] mb-4">Tokens Consumidos</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#8A8780' }} />
              <YAxis tick={{ fontSize: 11, fill: '#8A8780' }} />
              <Tooltip
                contentStyle={{
                  background: '#FFFFFF',
                  border: '1px solid rgba(0,0,0,0.08)',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="tokens" fill="#6E8B74" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Distribucion de consenso */}
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <h3 className="text-sm font-medium text-[#161616] mb-4">Distribucion de Consenso</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={consensusData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={4}
                dataKey="value"
              >
                {consensusData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: '#FFFFFF',
                  border: '1px solid rgba(0,0,0,0.08)',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap justify-center gap-4 mt-2">
            {consensusData.map((d, i) => (
              <span key={i} className="flex items-center gap-1.5 text-xs text-[#5C5C5C]">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS[i] }} />
                {d.name} ({d.value})
              </span>
            ))}
          </div>
        </div>

        {/* Modelos mas usados */}
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <h3 className="text-sm font-medium text-[#161616] mb-4">Modelos mas Usados</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={modelData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#8A8780' }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#8A8780' }} width={120} />
              <Tooltip
                contentStyle={{
                  background: '#FFFFFF',
                  border: '1px solid rgba(0,0,0,0.08)',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="count" fill="#B98B4D" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg shadow-card overflow-hidden">
        <div className="px-5 py-4 border-b border-[rgba(0,0,0,0.06)]">
          <h3 className="text-sm font-medium text-[#161616]">Debates Recientes</h3>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-[#23403B] animate-spin" />
          </div>
        ) : debates.length === 0 ? (
          <div className="text-center py-16 text-[#8A8780]">
            <Calendar className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p>No hay debates en este periodo</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[rgba(0,0,0,0.06)] text-xs text-[#8A8780] uppercase">
                    <th className="text-left px-5 py-3 font-medium">Tema</th>
                    <th className="text-left px-5 py-3 font-medium">Estado</th>
                    <th className="text-left px-5 py-3 font-medium hidden md:table-cell">Consenso</th>
                    <th className="text-left px-5 py-3 font-medium hidden lg:table-cell">Turnos</th>
                    <th className="text-left px-5 py-3 font-medium hidden lg:table-cell">Tokens</th>
                    <th className="text-left px-5 py-3 font-medium hidden sm:table-cell">Fecha</th>
                    <th className="px-5 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(0,0,0,0.04)]">
                  {debates.map((d) => {
                    const totalTokens =
                      (d.turns?.reduce((s, t) => s + (t.tokens_in || 0) + (t.tokens_out || 0), 0) || 0)
                    return (
                      <tr key={d.id} className="hover:bg-[#F5F3EE] transition-colors">
                        <td className="px-5 py-3">
                          <Link
                            to={`/debates/${d.id}`}
                            className="text-[#161616] hover:text-[#23403B] transition-colors font-medium truncate block max-w-[250px]"
                          >
                            {d.topic || 'Sin titulo'}
                          </Link>
                          <span className="text-xs text-[#8A8780] font-mono">{d.id}</span>
                        </td>
                        <td className="px-5 py-3">
                          <span
                            className={`text-xs px-2.5 py-1 rounded ${
                              statusBadge[d.status] || 'badge-neutral'
                            }`}
                          >
                            {d.status || 'CREATED'}
                          </span>
                        </td>
                        <td className="px-5 py-3 hidden md:table-cell">
                          <span
                            className={`text-xs font-medium ${
                              consensusText[d.consensus_level] || 'text-[#8A8780]'
                            }`}
                          >
                            {(d.consensus_level || '-').replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-[#5C5C5C] font-mono tabular-nums hidden lg:table-cell">
                          {d.turns?.length || 0}
                        </td>
                        <td className="px-5 py-3 text-[#5C5C5C] font-mono tabular-nums hidden lg:table-cell">
                          {formatTokens(totalTokens)}
                        </td>
                        <td className="px-5 py-3 text-[#5C5C5C] hidden sm:table-cell text-xs">
                          {d.created_at
                            ? format(parseISO(d.created_at), 'dd MMM HH:mm', { locale: es })
                            : '-'}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <Link
                            to={`/debates/${d.id}`}
                            className="text-[#5C5C5C] hover:text-[#23403B] transition-colors"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-5 py-3 border-t border-[rgba(0,0,0,0.06)]">
                <span className="text-xs text-[#8A8780]">
                  Pagina {page} de {totalPages}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-1.5 text-[#5C5C5C] hover:text-[#161616] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-1.5 text-[#5C5C5C] hover:text-[#161616] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function KpiCard({ icon: Icon, label, value, accent }) {
  return (
    <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-4 shadow-card">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-[#8A8780]">{label}</p>
          <p className="text-xl font-serif text-[#161616] mt-1">{value}</p>
        </div>
        <Icon className={`w-5 h-5 ${accent}`} />
      </div>
    </div>
  )
}

function computeStats(debates, total) {
  const completed = debates.filter((d) => d.status === 'COMPLETED')
  const consensusReached = debates.filter(
    (d) => d.consensus_level === 'CONSENSUS_REACHED'
  ).length
  const totalTurns = debates.reduce((s, d) => s + (d.turns?.length || 0), 0)
  const totalTokens = debates.reduce(
    (s, d) =>
      s +
      (d.turns?.reduce(
        (ss, t) => ss + (t.tokens_in || 0) + (t.tokens_out || 0),
        0
      ) || 0),
    0
  )
  const n = debates.length || 1
  return {
    total,
    consensusRate: ((consensusReached / n) * 100).toFixed(0),
    avgTurns: totalTurns / n,
    avgTokens: totalTokens / n,
  }
}

function buildTrendData(debates, days) {
  const map = {}
  for (let i = days - 1; i >= 0; i--) {
    const date = format(subDays(new Date(), i), 'dd/MM')
    map[date] = { date, count: 0, tokens: 0 }
  }
  debates.forEach((d) => {
    if (!d.created_at) return
    const date = format(parseISO(d.created_at), 'dd/MM')
    if (map[date]) {
      map[date].count += 1
      map[date].tokens +=
        d.turns?.reduce(
          (s, t) => s + (t.tokens_in || 0) + (t.tokens_out || 0),
          0
        ) || 0
    }
  })
  return Object.values(map)
}

function buildConsensusPie(debates) {
  const counts = {}
  debates.forEach((d) => {
    const level = d.consensus_level || 'UNKNOWN'
    counts[level] = (counts[level] || 0) + 1
  })
  return Object.entries(counts).map(([name, value]) => ({
    name: name.replace(/_/g, ' '),
    value,
  }))
}

function buildModelUsage(debates) {
  const counts = {}
  debates.forEach((d) => {
    d.turns?.forEach((t) => {
      const model = t.model || t.agent?.model || 'unknown'
      counts[model] = (counts[model] || 0) + 1
    })
  })
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([name, count]) => ({ name: name.slice(0, 20), count }))
}

function formatTokens(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return `${n}`
}
