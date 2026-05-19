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
        fetch(`${API_BASE}/api/v1/system/worker/gpu/metrics`).then((r) => r.json()),
        fetch(`${API_BASE}/api/v1/system/worker/gpu/history?limit=30`).then((r) => r.json()),
        fetch(`${API_BASE}/health`).then((r) => r.json()),
        fetch(`${API_BASE}/api/v1/system/circuit-breakers/status`).then((r) => r.json()),
      ])
      if (gpuRes.status === 'fulfilled') setGpuMetrics(gpuRes.value)
      if (histRes.status === 'fulfilled' && histRes.value?.history) setGpuHistory(Array.isArray(histRes.value.history) ? histRes.value.history : [])
      if (healthRes.status === 'fulfilled') setHealth(healthRes.value)
      if (cbRes.status === 'fulfilled') {
        const cbData = cbRes.value
        setCircuitBreakers(Array.isArray(cbData) ? cbData : [])
      }
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
        return 'badge-success'
      case 'open':
        return 'badge-error'
      case 'half_open':
        return 'badge-warning'
      default:
        return 'badge-neutral'
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
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl text-[#161616]">Monitor del Sistema</h1>
          <p className="text-sm text-[#5C5C5C] mt-1">GPU, Circuit Breakers y Health Checks</p>
          <div className="w-8 h-0.5 bg-[#23403B] mt-3" />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1.5 text-xs rounded transition-colors ${
              autoRefresh
                ? 'bg-[#4A7C59]/[0.08] text-[#4A7C59] border border-[#4A7C59]/15'
                : 'bg-white text-[#5C5C5C] border border-[rgba(0,0,0,0.08)]'
            }`}
          >
            Auto-refresh {autoRefresh ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={fetchData}
            className="p-2 bg-white border border-[rgba(0,0,0,0.08)] rounded text-[#5C5C5C] hover:text-[#161616] hover:border-[rgba(0,0,0,0.12)] transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* GPU Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* VRAM */}
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-[#23403B]" />
            <h2 className="text-sm font-semibold text-[#161616]">VRAM</h2>
          </div>
          {loading ? (
            <div className="text-sm text-[#8A8780]">Cargando...</div>
          ) : gpuMetrics?.available ? (
            <div className="space-y-3">
              <div className="flex items-end justify-between">
                <span className="text-3xl font-serif text-[#161616]">{Math.round(vramUsed)}</span>
                <span className="text-sm text-[#8A8780]">/ {Math.round(vramTotal)} MB</span>
              </div>
              <div className="w-full bg-[#F5F3EE] rounded h-2">
                <div
                  className={`h-2 rounded transition-all ${
                    vramPct > 90 ? 'bg-[#8B3A3A]' : vramPct > 70 ? 'bg-[#B98B4D]' : 'bg-[#23403B]'
                  }`}
                  style={{ width: `${Math.min(vramPct, 100)}%` }}
                />
              </div>
              <div className="text-xs">
                {vramPct > 90 ? (
                  <span className="text-[#8B3A3A] flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Critico
                  </span>
                ) : vramPct > 70 ? (
                  <span className="text-[#B98B4D]">Alto</span>
                ) : (
                  <span className="text-[#4A7C59]">Normal</span>
                )}
              </div>
            </div>
          ) : (
            <div className="text-sm text-[#8A8780]">{typeof gpuMetrics?.error === 'string' ? gpuMetrics.error : 'GPU no disponible'}</div>
          )}
        </div>

        {/* Temperature */}
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <div className="flex items-center gap-2 mb-4">
            <Thermometer className="w-5 h-5 text-[#B98B4D]" />
            <h2 className="text-sm font-semibold text-[#161616]">Temperatura</h2>
          </div>
          {loading ? (
            <div className="text-sm text-[#8A8780]">Cargando...</div>
          ) : gpuMetrics?.available ? (
            <div className="space-y-3">
              <div className="flex items-end justify-between">
                <span className="text-3xl font-serif text-[#161616]">
                  {gpuMetrics.temperature_celsius ?? 'N/A'}
                </span>
                {gpuMetrics.temperature_celsius != null && <span className="text-sm text-[#8A8780]">°C</span>}
              </div>
              <div className="w-full bg-[#F5F3EE] rounded h-2">
                <div
                  className={`h-2 rounded transition-all ${
                    (gpuMetrics.temperature_celsius || 0) > 80
                      ? 'bg-[#8B3A3A]'
                      : (gpuMetrics.temperature_celsius || 0) > 65
                      ? 'bg-[#B98B4D]'
                      : 'bg-[#4A7C59]'
                  }`}
                  style={{ width: `${Math.min((gpuMetrics.temperature_celsius || 0) / 100 * 100, 100)}%` }}
                />
              </div>
              <div className="text-xs">
                {(gpuMetrics.temperature_celsius || 0) > 80 ? (
                  <span className="text-[#8B3A3A]">Sobrecalentamiento</span>
                ) : (
                  <span className="text-[#4A7C59]">Normal</span>
                )}
              </div>
            </div>
          ) : (
            <div className="text-sm text-[#8A8780]">No disponible</div>
          )}
        </div>

        {/* Utilization */}
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-[#6E8B74]" />
            <h2 className="text-sm font-semibold text-[#161616]">Utilizacion GPU</h2>
          </div>
          {loading ? (
            <div className="text-sm text-[#8A8780]">Cargando...</div>
          ) : gpuMetrics?.available ? (
            <div className="space-y-3">
              <div className="flex items-end justify-between">
                <span className="text-3xl font-serif text-[#161616]">
                  {gpuMetrics.utilization_pct ?? 'N/A'}
                </span>
                {gpuMetrics.utilization_pct != null && <span className="text-sm text-[#8A8780]">%</span>}
              </div>
              <div className="w-full bg-[#F5F3EE] rounded h-2">
                <div
                  className="h-2 rounded bg-[#6E8B74] transition-all"
                  style={{ width: `${gpuMetrics.utilization_pct || 0}%` }}
                />
              </div>
              <div className="text-xs text-[#5C5C5C]">
                {gpuMetrics.gpu_name && <span>{gpuMetrics.gpu_name}</span>}
              </div>
            </div>
          ) : (
            <div className="text-sm text-[#8A8780]">No disponible</div>
          )}
        </div>
      </div>

      {/* GPU History Chart */}
      {gpuHistory.length > 0 && (
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <h2 className="text-sm font-semibold text-[#161616] mb-4">Historico VRAM (ultimos 30 puntos)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={gpuHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(v) => new Date(v).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                  stroke="#B8B5AE"
                  tick={{ fontSize: 11, fill: '#8A8780' }}
                />
                <YAxis stroke="#B8B5AE" tick={{ fontSize: 11, fill: '#8A8780' }} label={{ value: 'MB', angle: -90, position: 'insideLeft', fill: '#8A8780' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#FFFFFF', border: '1px solid rgba(0,0,0,0.08)', borderRadius: '6px', fontSize: '12px' }}
                  labelFormatter={(v) => new Date(v).toLocaleTimeString('es-ES')}
                />
                <Area
                  type="monotone"
                  dataKey="memory_used_mb"
                  stroke="#23403B"
                  fill="url(#vramGradient)"
                  strokeWidth={2}
                />
                <defs>
                  <linearGradient id="vramGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#23403B" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#23403B" stopOpacity={0} />
                  </linearGradient>
                </defs>
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Circuit Breakers */}
      <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
        <h2 className="text-sm font-semibold text-[#161616] mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#B98B4D]" />
          Circuit Breakers
        </h2>
        {loading ? (
          <div className="text-sm text-[#8A8780]">Cargando...</div>
        ) : circuitBreakers.length === 0 ? (
          <div className="text-sm text-[#8A8780]">No hay circuit breakers configurados</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {circuitBreakers.map((cb) => (
              <div key={cb.name} className="bg-[#F5F3EE] rounded p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-[#161616] capitalize">{cb.name}</span>
                  <span className={`text-xs px-2 py-1 rounded flex items-center gap-1 ${cbStatusColor(cb.state)}`}>
                    {cbIcon(cb.state)}
                    {cb.state}
                  </span>
                </div>
                <div className="space-y-1 text-xs text-[#5C5C5C]">
                  <div className="flex justify-between">
                    <span>Fallos</span>
                    <span className="text-[#161616] font-mono tabular-nums">{cb.failure_count}/{cb.failure_threshold}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Success rate</span>
                    <span className="text-[#161616] font-mono tabular-nums">{(cb.success_rate * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total requests</span>
                    <span className="text-[#161616] font-mono tabular-nums">{cb.total_requests}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Health */}
      <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
        <h2 className="text-sm font-semibold text-[#161616] mb-4">Health Check</h2>
        {loading ? (
          <div className="text-sm text-[#8A8780]">Cargando...</div>
        ) : health ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <div className="bg-[#F5F3EE] rounded p-3 text-center">
              <div className={`text-xs px-2 py-1 rounded inline-block ${
                health.status === 'ok' || health.status === 'online' ? 'badge-success' : 'badge-error'
              }`}>
                {health.status || 'unknown'}
              </div>
              <div className="text-xs text-[#8A8780] mt-1">Backend</div>
            </div>
            {health.services &&
              Object.entries(health.services).map(([name, detail]) => {
                const statusStr = typeof detail === 'string' ? detail : detail?.status || 'unknown'
                const isOnline = statusStr === 'online' || statusStr === 'ok' || statusStr === 'healthy'
                return (
                  <div key={name} className="bg-[#F5F3EE] rounded p-3 text-center">
                    <div className={`text-xs px-2 py-1 rounded inline-block ${
                      isOnline ? 'badge-success' : 'badge-neutral'
                    }`}>
                      {statusStr}
                    </div>
                    <div className="text-xs text-[#8A8780] mt-1 capitalize">{name}</div>
                  </div>
                )
              })}
          </div>
        ) : (
          <div className="text-sm text-[#8B3A3A]">No se pudo conectar</div>
        )}
      </div>
    </div>
  )
}
