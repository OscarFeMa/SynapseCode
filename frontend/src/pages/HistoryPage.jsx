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

const COLORS = ['#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#8b5cf6']

const statusColors = {
  COMPLETED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  FAILED: 'bg-red-500/10 text-red-400 border-red-500/20',
  RUNNING: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  CREATED: 'bg-slate-700 text-slate-400 border-slate-600',
}

const consensusColors = {
  CONSENSUS_REACHED: 'text-emerald-400',
  PARTIAL_CONSENSUS: 'text-amber-400',
  DIVERGENT: 'text-red-400',
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Historico</h1>
          <p className="text-sm text-slate-400 mt-1">
            {total} debates en los ultimos {dateRange} dias
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => {
              setDateRange(Number(e.target.value))
              setPage(1)
            }}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value={7}>7 dias</option>
            <option value={30}>30 dias</option>
            <option value={90}>90 dias</option>
          </select>
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white hover:bg-slate-700 transition-colors"
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
          color="text-amber-500"
        />
        <KpiCard
          icon={Scale}
          label="Tasa Consenso"
          value={`${stats.consensusRate}%`}
          color="text-emerald-500"
        />
        <KpiCard
          icon={Clock}
          label="Prom. Turnos"
          value={stats.avgTurns.toFixed(1)}
          color="text-blue-500"
        />
        <KpiCard
          icon={TrendingUp}
          label="Prom. Tokens"
          value={formatTokens(stats.avgTokens)}
          color="text-purple-500"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Debates por dia */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-white mb-4">Debates por Dia</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={trendData}>
              <defs>
                <linearGradient id="colorDebates" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#f59e0b"
                fillOpacity={1}
                fill="url(#colorDebates)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Tokens por dia */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-white mb-4">Tokens Consumidos</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
              <Tooltip
                contentStyle={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="tokens" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Distribucion de consenso */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-white mb-4">Distribucion de Consenso</h3>
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
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap justify-center gap-4 mt-2">
            {consensusData.map((d, i) => (
              <span key={i} className="flex items-center gap-1.5 text-xs text-slate-400">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS[i] }} />
                {d.name} ({d.value})
              </span>
            ))}
          </div>
        </div>

        {/* Modelos mas usados */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-white mb-4">Modelos mas Usados</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={modelData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#64748b' }} width={120} />
              <Tooltip
                contentStyle={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800">
          <h3 className="text-sm font-medium text-white">Debates Recientes</h3>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
          </div>
        ) : debates.length === 0 ? (
          <div className="text-center py-16 text-slate-500">
            <Calendar className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No hay debates en este periodo</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs text-slate-500 uppercase">
                    <th className="text-left px-5 py-3 font-medium">Tema</th>
                    <th className="text-left px-5 py-3 font-medium">Estado</th>
                    <th className="text-left px-5 py-3 font-medium hidden md:table-cell">Consenso</th>
                    <th className="text-left px-5 py-3 font-medium hidden lg:table-cell">Turnos</th>
                    <th className="text-left px-5 py-3 font-medium hidden lg:table-cell">Tokens</th>
                    <th className="text-left px-5 py-3 font-medium hidden sm:table-cell">Fecha</th>
                    <th className="px-5 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {debates.map((d) => {
                    const totalTokens =
                      (d.turns?.reduce((s, t) => s + (t.tokens_in || 0) + (t.tokens_out || 0), 0) || 0)
                    return (
                      <tr key={d.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                        <td className="px-5 py-3">
                          <Link
                            to={`/debates/${d.id}`}
                            className="text-white hover:text-amber-400 transition-colors font-medium truncate block max-w-[250px]"
                          >
                            {d.topic || 'Sin titulo'}
                          </Link>
                          <span className="text-xs text-slate-600 font-mono">{d.id}</span>
                        </td>
                        <td className="px-5 py-3">
                          <span
                            className={`text-xs px-2 py-1 rounded-full border ${
                              statusColors[d.status] || statusColors.CREATED
                            }`}
                          >
                            {d.status || 'CREATED'}
                          </span>
                        </td>
                        <td className="px-5 py-3 hidden md:table-cell">
                          <span
                            className={`text-xs font-medium ${
                              consensusColors[d.consensus_level] || 'text-slate-500'
                            }`}
                          >
                            {(d.consensus_level || '-').replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-slate-400 hidden lg:table-cell">
                          {d.turns?.length || 0}
                        </td>
                        <td className="px-5 py-3 text-slate-400 hidden lg:table-cell">
                          {formatTokens(totalTokens)}
                        </td>
                        <td className="px-5 py-3 text-slate-400 hidden sm:table-cell text-xs">
                          {d.created_at
                            ? format(parseISO(d.created_at), 'dd MMM HH:mm', { locale: es })
                            : '-'}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <Link
                            to={`/debates/${d.id}`}
                            className="text-slate-400 hover:text-amber-400 transition-colors"
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
              <div className="flex items-center justify-between px-5 py-3 border-t border-slate-800">
                <span className="text-xs text-slate-500">
                  Pagina {page} de {totalPages}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
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

function KpiCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-500">{label}</p>
          <p className="text-xl font-bold text-white mt-1">{value}</p>
        </div>
        <Icon className={`w-5 h-5 ${color}`} />
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
