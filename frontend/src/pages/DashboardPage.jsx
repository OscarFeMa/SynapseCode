import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  MessageSquare,
  CheckCircle,
  TrendingUp,
  Cpu,
  Activity,
  Zap,
  Plus,
  ExternalLink,
} from 'lucide-react'
import { useSessionStore } from '../store/useStore'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function DashboardPage() {
  const sessions = useSessionStore((s) => s.sessions)
  const fetchSessions = useSessionStore((s) => s.fetchSessions)
  const [health, setHealth] = useState(null)
  const [gpuMetrics, setGpuMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadData = async () => {
      try {
        await fetchSessions()
        const [healthRes, gpuRes] = await Promise.allSettled([
          fetch(`${API_BASE}/health`).then((r) => r.json()),
          fetch(`${API_BASE}/api/system/worker/gpu/metrics`).then((r) => r.json()),
        ])
        if (healthRes.status === 'fulfilled') setHealth(healthRes.value)
        if (gpuRes.status === 'fulfilled') setGpuMetrics(gpuRes.value)
      } catch (e) {
        console.warn('Dashboard load error:', e)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [fetchSessions])

  const totalSessions = sessions.length
  const completedSessions = sessions.filter((s) => s.status === 'completed').length
  const activeSessions = sessions.filter((s) => s.status === 'running').length

  const kpis = [
    {
      label: 'Debates Totales',
      value: totalSessions,
      icon: MessageSquare,
      color: 'text-amber-500',
      bg: 'bg-amber-500/10',
    },
    {
      label: 'Completados',
      value: completedSessions,
      icon: CheckCircle,
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10',
    },
    {
      label: 'Activos',
      value: activeSessions,
      icon: Activity,
      color: 'text-blue-500',
      bg: 'bg-blue-500/10',
    },
    {
      label: 'Tasa Exito',
      value: totalSessions > 0 ? `${Math.round((completedSessions / totalSessions) * 100)}%` : '0%',
      icon: TrendingUp,
      color: 'text-purple-500',
      bg: 'bg-purple-500/10',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">Vista general del sistema SynapseCode</p>
        </div>
        <Link
          to="/debates/new"
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-900 text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nuevo Debate
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider">{kpi.label}</p>
                <p className="text-2xl font-bold text-white mt-1">{loading ? '...' : kpi.value}</p>
              </div>
              <div className={`w-10 h-10 ${kpi.bg} rounded-lg flex items-center justify-center`}>
                <kpi.icon className={`w-5 h-5 ${kpi.color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* System Status + GPU */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* System Health */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-500" />
            Estado del Sistema
          </h2>
          {loading ? (
            <div className="text-sm text-slate-500">Cargando...</div>
          ) : health ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Backend</span>
                <span
                  className={`text-xs font-medium px-2 py-1 rounded-full ${
                    health.status === 'ok' || health.status === 'online'
                      ? 'bg-emerald-500/10 text-emerald-500'
                      : 'bg-red-500/10 text-red-500'
                  }`}
                >
                  {health.status || 'unknown'}
                </span>
              </div>
              {health.database && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Base de datos</span>
                  <span className="text-xs font-medium px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-500">
                    {typeof health.database === 'string' ? health.database : health.database?.status || 'connected'}
                  </span>
                </div>
              )}
              {health.services &&
                Object.entries(health.services).map(([name, detail]) => {
                  const statusStr = typeof detail === 'string' ? detail : detail?.status || 'unknown'
                  const isOnline = statusStr === 'online' || statusStr === 'ok' || statusStr === 'healthy'
                  return (
                    <div key={name} className="flex items-center justify-between">
                      <span className="text-sm text-slate-400 capitalize">{name}</span>
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded-full ${
                          isOnline
                            ? 'bg-emerald-500/10 text-emerald-500'
                            : 'bg-slate-700 text-slate-400'
                        }`}
                      >
                        {statusStr}
                      </span>
                    </div>
                  )
                })}
            </div>
          ) : (
            <div className="text-sm text-red-500">No se pudo conectar al backend</div>
          )}
        </div>

        {/* GPU Metrics */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-blue-500" />
            GPU Worker
          </h2>
          {loading ? (
            <div className="text-sm text-slate-500">Cargando...</div>
          ) : gpuMetrics?.available ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">VRAM Usada</span>
                <span className="text-sm font-mono text-white">
                  {gpuMetrics.memory?.used_mb ? `${Math.round(gpuMetrics.memory.used_mb)} MB` : 'N/A'}
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{ width: `${gpuMetrics.memory?.used_pct || 0}%` }}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Temperatura</span>
                <span className="text-sm font-mono text-white">
                  {gpuMetrics.temperature_celsius ? `${gpuMetrics.temperature_celsius}°C` : 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Utilizacion</span>
                <span className="text-sm font-mono text-white">
                  {gpuMetrics.utilization_pct != null ? `${gpuMetrics.utilization_pct}%` : 'N/A'}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">
              {typeof gpuMetrics?.error === 'string' ? gpuMetrics.error : 'GPU no disponible'}
            </div>
          )}
        </div>
      </div>

      {/* Recent Debates */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Debates Recientes</h2>
          <Link to="/debates" className="text-xs text-amber-500 hover:text-amber-400 flex items-center gap-1">
            Ver todos <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
        {sessions.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No hay debates aun</p>
            <Link
              to="/debates/new"
              className="text-amber-500 text-sm hover:text-amber-400 mt-2 inline-block"
            >
              Crear el primero →
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.slice(0, 5).map((session) => (
              <Link
                key={session.id}
                to={`/debates/${session.id}`}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      session.status === 'completed'
                        ? 'bg-emerald-500'
                        : session.status === 'running'
                        ? 'bg-blue-500 animate-pulse'
                        : 'bg-slate-600'
                    }`}
                  />
                  <div>
                    <p className="text-sm text-white truncate max-w-[300px]">{session.topic}</p>
                    <p className="text-xs text-slate-500">{session.id}</p>
                  </div>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    session.status === 'completed'
                      ? 'bg-emerald-500/10 text-emerald-500'
                      : session.status === 'running'
                      ? 'bg-blue-500/10 text-blue-500'
                      : 'bg-slate-700 text-slate-400'
                  }`}
                >
                  {session.status}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
