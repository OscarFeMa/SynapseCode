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
  const completedSessions = sessions.filter((s) => s.status === 'COMPLETED').length
  const activeSessions = sessions.filter((s) => s.status === 'RUNNING').length

  const kpis = [
    {
      label: 'Debates Totales',
      value: totalSessions,
      icon: MessageSquare,
      accent: 'text-[#23403B]',
      bg: 'bg-[#23403B]/[0.06]',
    },
    {
      label: 'Completados',
      value: completedSessions,
      icon: CheckCircle,
      accent: 'text-[#4A7C59]',
      bg: 'bg-[#4A7C59]/[0.06]',
    },
    {
      label: 'Activos',
      value: activeSessions,
      icon: Activity,
      accent: 'text-[#6E8B74]',
      bg: 'bg-[#6E8B74]/[0.06]',
    },
    {
      label: 'Tasa Exito',
      value: totalSessions > 0 ? `${Math.round((completedSessions / totalSessions) * 100)}%` : '0%',
      icon: TrendingUp,
      accent: 'text-[#B98B4D]',
      bg: 'bg-[#B98B4D]/[0.06]',
    },
  ]

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl text-[#161616]">Dashboard</h1>
          <p className="text-sm text-[#5C5C5C] mt-1">Vista general del sistema SynapseCode</p>
          <div className="w-8 h-0.5 bg-[#23403B] mt-3" />
        </div>
        <Link
          to="/debates/new"
          className="flex items-center gap-2 px-4 py-2 bg-[#23403B] hover:bg-[#2D524C] text-[#F5F3EE] text-sm font-medium rounded transition-colors"
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
            className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card hover:border-[rgba(0,0,0,0.12)] transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[#8A8780] uppercase tracking-wider">{kpi.label}</p>
                <p className="text-2xl font-semibold text-[#161616] mt-1 font-serif">
                  {loading ? '—' : kpi.value}
                </p>
              </div>
              <div className={`w-10 h-10 ${kpi.bg} rounded flex items-center justify-center`}>
                <kpi.icon className={`w-5 h-5 ${kpi.accent}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* System Status + GPU */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* System Health */}
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <h2 className="text-sm font-semibold text-[#161616] mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-[#B98B4D]" />
            Estado del Sistema
          </h2>
          {loading ? (
            <div className="text-sm text-[#8A8780]">Cargando...</div>
          ) : health ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#5C5C5C]">Backend</span>
                <span
                  className={`text-xs font-medium px-2.5 py-1 rounded ${
                    health.status === 'ok' || health.status === 'online'
                      ? 'badge-success'
                      : 'badge-error'
                  }`}
                >
                  {health.status || 'unknown'}
                </span>
              </div>
              {health.database && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#5C5C5C]">Base de datos</span>
                  <span className="text-xs font-medium px-2.5 py-1 rounded badge-success">
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
                      <span className="text-sm text-[#5C5C5C] capitalize">{name}</span>
                      <span
                        className={`text-xs font-medium px-2.5 py-1 rounded ${
                          isOnline ? 'badge-success' : 'badge-neutral'
                        }`}
                      >
                        {statusStr}
                      </span>
                    </div>
                  )
                })}
            </div>
          ) : (
            <div className="text-sm text-[#8B3A3A]">No se pudo conectar al backend</div>
          )}
        </div>

        {/* GPU Metrics */}
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <h2 className="text-sm font-semibold text-[#161616] mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-[#23403B]" />
            GPU Worker
          </h2>
          {loading ? (
            <div className="text-sm text-[#8A8780]">Cargando...</div>
          ) : gpuMetrics?.available ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#5C5C5C]">VRAM Usada</span>
                <span className="text-sm font-mono text-[#161616] tabular-nums">
                  {gpuMetrics.memory?.used_mb ? `${Math.round(gpuMetrics.memory.used_mb)} MB` : 'N/A'}
                </span>
              </div>
              <div className="w-full bg-[#F5F3EE] rounded h-1.5">
                <div
                  className="bg-[#23403B] h-1.5 rounded transition-all"
                  style={{ width: `${gpuMetrics.memory?.used_pct || 0}%` }}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#5C5C5C]">Temperatura</span>
                <span className="text-sm font-mono text-[#161616] tabular-nums">
                  {gpuMetrics.temperature_celsius ? `${gpuMetrics.temperature_celsius}°C` : 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#5C5C5C]">Utilizacion</span>
                <span className="text-sm font-mono text-[#161616] tabular-nums">
                  {gpuMetrics.utilization_pct != null ? `${gpuMetrics.utilization_pct}%` : 'N/A'}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-sm text-[#8A8780]">
              {typeof gpuMetrics?.error === 'string' ? gpuMetrics.error : 'GPU no disponible'}
            </div>
          )}
        </div>
      </div>

      {/* Recent Debates */}
      <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg shadow-card">
        <div className="px-5 py-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[#161616]">Debates Recientes</h2>
          <Link to="/debates" className="text-xs text-[#23403B] hover:text-[#2D524C] flex items-center gap-1 font-medium">
            Ver todos <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
        {sessions.length === 0 ? (
          <div className="text-center py-12 text-[#8A8780]">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p className="text-sm">No hay debates aun</p>
            <Link
              to="/debates/new"
              className="text-[#23403B] text-sm hover:text-[#2D524C] mt-2 inline-block font-medium"
            >
              Crear el primero →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-[rgba(0,0,0,0.04)]">
            {sessions.slice(0, 5).map((session) => (
              <Link
                key={session.id}
                to={`/debates/${session.id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-[#F5F3EE] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      session.status === 'COMPLETED'
                        ? 'bg-[#4A7C59]'
                        : session.status === 'RUNNING'
                        ? 'bg-[#6E8B74] animate-pulse'
                        : 'bg-[#B8B5AE]'
                    }`}
                  />
                  <div>
                    <p className="text-sm text-[#161616] truncate max-w-[300px] font-medium">{session.title || session.query}</p>
                    <p className="text-xs text-[#8A8780] font-mono">{session.id}</p>
                  </div>
                </div>
                <span
                  className={`text-xs px-2.5 py-1 rounded ${
                    session.status === 'COMPLETED'
                      ? 'badge-success'
                      : session.status === 'RUNNING'
                      ? 'badge-neutral'
                      : 'badge-neutral'
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
