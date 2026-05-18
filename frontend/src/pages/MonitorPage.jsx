import { useEffect, useState } from 'react'
import { RefreshCw, AlertTriangle, CheckCircle, XCircle, Activity, Thermometer, Cpu, Zap } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function MonitorPage() {
  const [gpuMetrics, setGpuMetrics] = useState(null)
  const [gpuHistory, setGpuHistory] = useState([])
  const [health, setHealth] = useState(null)
  const [circuitBreakers, setCircuitBreakers] = useState([])
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchData = async () => {
    try {
      const [gpuRes, histRes, healthRes, cbRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/system/worker/gpu/metrics`).then((r) => r.json()),
        fetch(`${API_BASE}/api/system/worker/gpu/history?limit=30`).then((r) => r.json()),
        fetch(`${API_BASE}/health`).then((r) => r.json()),
        fetch(`${API_BASE}/api/system/circuit-breakers/status`).then((r) => r.json()),
      ])
      if (gpuRes.status === 'fulfilled') setGpuMetrics(gpuRes.value)
      if (histRes.status === 'fulfilled' && histRes.value?.history) setGpuHistory(histRes.value.history)
      if (healthRes.status === 'fulfilled') setHealth(healthRes.value)
      if (cbRes.status === 'fulfilled') setCircuitBreakers(cbRes.value || [])
    } catch (e) {
      console.warn('Monitor fetch error:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [autoRefresh])

  const cbStatusColor = (state) => {
    switch (state) {
      case 'closed':
        return 'text-emerald-400 bg-emerald-500/10'
      case 'open':
        return 'text-red-400 bg-red-500/10'
      case 'half_open':
        return 'text-amber-400 bg-amber-500/10'
      default:
        return 'text-slate-400 bg-slate-700'
    }
  }

  const cbIcon = (state) => {
    switch (state) {
      case 'closed':
        return <CheckCircle className="w-4 h-4" />
      case 'open':
        return <XCircle className="w-4 h-4" />
      case 'half_open':
        return <AlertTriangle className="w-4 h-4" />
      default:
        return <Activity className="w-4 h-4" />
    }
  }

  const vramUsed = gpuMetrics?.memory?.used_mb || 0
  const vramTotal = gpuMetrics?.memory?.total_mb || 13500
  const vramPct = gpuMetrics?.memory?.used_pct || (vramUsed / vramTotal) * 100

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Monitor del Sistema</h1>
          <p className="text-sm text-slate-400 mt-1">GPU, Circuit Breakers y Health Checks</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
              autoRefresh ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
            }`}
          >
            Auto-refresh {autoRefresh ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={fetchData}
            className="p-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* GPU Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* VRAM */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-blue-400" />
            <h2 className="text-sm font-semibold text-white">VRAM</h2>
          </div>
          {loading ? (
            <div className="text-sm text-slate-500">Cargando...</div>
          ) : gpuMetrics?.available ? (
            <div className="space-y-3">
              <div className="flex items-end justify-between">
                <span className="text-3xl font-bold text-white">{Math.round(vramUsed)}</span>
                <span className="text-sm text-slate-500">/ {Math.round(vramTotal)} MB</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all ${
                    vramPct > 90 ? 'bg-red-500' : vramPct > 70 ? 'bg-amber-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${Math.min(vramPct, 100)}%` }}
                />
              </div>
              <div className="text-xs text-slate-500">
                {vramPct > 90 ? (
                  <span className="text-red-400 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Critico
                  </span>
                ) : vramPct > 70 ? (
                  <span className="text-amber-400">Alto</span>
                ) : (
                  <span className="text-emerald-400">Normal</span>
                )}
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">{gpuMetrics?.error || 'GPU no disponible'}</div>
          )}
        </div>

        {/* Temperature */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Thermometer className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold text-white">Temperatura</h2>
          </div>
          {loading ? (
            <div className="text-sm text-slate-500">Cargando...</div>
          ) : gpuMetrics?.available ? (
            <div className="space-y-3">
              <div className="flex items-end justify-between">
                <span className="text-3xl font-bold text-white">
                  {gpuMetrics.temperature_celsius ?? 'N/A'}
                </span>
                {gpuMetrics.temperature_celsius != null && <span className="text-sm text-slate-500">°C</span>}
              </div>
              <div className="w-full bg-slate-800 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all ${
                    (gpuMetrics.temperature_celsius || 0) > 80
                      ? 'bg-red-500'
                      : (gpuMetrics.temperature_celsius || 0) > 65
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min((gpuMetrics.temperature_celsius || 0) / 100 * 100, 100)}%` }}
                />
              </div>
              <div className="text-xs text-slate-500">
                {(gpuMetrics.temperature_celsius || 0) > 80 ? (
                  <span className="text-red-400">Sobrecalentamiento</span>
                ) : (
                  <span className="text-emerald-400">Normal</span>
                )}
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">No disponible</div>
          )}
        </div>

        {/* Utilization */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-purple-400" />
            <h2 className="text-sm font-semibold text-white">Utilizacion GPU</h2>
          </div>
          {loading ? (
            <div className="text-sm text-slate-500">Cargando...</div>
          ) : gpuMetrics?.available ? (
            <div className="space-y-3">
              <div className="flex items-end justify-between">
                <span className="text-3xl font-bold text-white">
                  {gpuMetrics.utilization_pct ?? 'N/A'}
                </span>
                {gpuMetrics.utilization_pct != null && <span className="text-sm text-slate-500">%</span>}
              </div>
              <div className="w-full bg-slate-800 rounded-full h-3">
                <div
                  className="h-3 rounded-full bg-purple-500 transition-all"
                  style={{ width: `${gpuMetrics.utilization_pct || 0}%` }}
                />
              </div>
              <div className="text-xs text-slate-500">
                {gpuMetrics.gpu_name && <span>{gpuMetrics.gpu_name}</span>}
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">No disponible</div>
          )}
        </div>
      </div>

      {/* GPU History Chart */}
      {gpuHistory.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Historico VRAM (ultimos 30 puntos)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={gpuHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(v) => new Date(v).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                  stroke="#475569"
                  tick={{ fontSize: 11 }}
                />
                <YAxis stroke="#475569" tick={{ fontSize: 11 }} label={{ value: 'MB', angle: -90, position: 'insideLeft', fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                  labelFormatter={(v) => new Date(v).toLocaleTimeString('es-ES')}
                />
                <Area
                  type="monotone"
                  dataKey="memory_used_mb"
                  stroke="#3b82f6"
                  fill="url(#vramGradient)"
                  strokeWidth={2}
                />
                <defs>
                  <linearGradient id="vramGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Circuit Breakers */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-amber-500" />
          Circuit Breakers
        </h2>
        {loading ? (
          <div className="text-sm text-slate-500">Cargando...</div>
        ) : circuitBreakers.length === 0 ? (
          <div className="text-sm text-slate-500">No hay circuit breakers configurados</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {circuitBreakers.map((cb) => (
              <div key={cb.name} className="bg-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white capitalize">{cb.name}</span>
                  <span className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${cbStatusColor(cb.state)}`}>
                    {cbIcon(cb.state)}
                    {cb.state}
                  </span>
                </div>
                <div className="space-y-1 text-xs text-slate-400">
                  <div className="flex justify-between">
                    <span>Fallos</span>
                    <span className="text-white">{cb.failure_count}/{cb.failure_threshold}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Success rate</span>
                    <span className="text-white">{(cb.success_rate * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total requests</span>
                    <span className="text-white">{cb.total_requests}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Health */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Health Check</h2>
        {loading ? (
          <div className="text-sm text-slate-500">Cargando...</div>
        ) : health ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <div className="bg-slate-800 rounded-lg p-3 text-center">
              <div className={`text-xs px-2 py-1 rounded-full inline-block ${
                health.status === 'ok' || health.status === 'online' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
              }`}>
                {health.status || 'unknown'}
              </div>
              <div className="text-xs text-slate-500 mt-1">Backend</div>
            </div>
            {health.services &&
              Object.entries(health.services).map(([name, status]) => (
                <div key={name} className="bg-slate-800 rounded-lg p-3 text-center">
                  <div className={`text-xs px-2 py-1 rounded-full inline-block ${
                    status === 'online' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-700 text-slate-400'
                  }`}>
                    {status}
                  </div>
                  <div className="text-xs text-slate-500 mt-1 capitalize">{name}</div>
                </div>
              ))}
          </div>
        ) : (
          <div className="text-sm text-red-500">No se pudo conectar</div>
        )}
      </div>
    </div>
  )
}
