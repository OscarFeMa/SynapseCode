import { useEffect, useState } from 'react'
import { Database, Trash2, RefreshCw, BarChart3 } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function CachePage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/cache/stats`)
      if (res.ok) setStats(await res.json())
    } catch (e) {
      console.warn('Cache stats unavailable')
      setStats(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleAction = async (action) => {
    setActionLoading(action)
    try {
      await fetch(`${API_BASE}/api/v1/cache/${action}`, { method: 'POST' })
      await fetchStats()
    } catch (e) {
      console.error(`Cache ${action} failed:`, e)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Cache Semantica</h1>
        <p className="text-sm text-slate-400 mt-1">Estadisticas, invalidacion y limpieza</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-500">Cargando...</div>
      ) : !stats ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
          <Database className="w-12 h-12 mx-auto text-slate-600 mb-3" />
          <p className="text-slate-500">Cache no disponible o deshabilitado</p>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Entradas', value: stats.total_entries || stats.entries || 0, icon: Database, color: 'text-blue-400' },
              { label: 'Hits', value: stats.total_hits || stats.hits || 0, icon: BarChart3, color: 'text-emerald-400' },
              { label: 'Hit Rate', value: `${((stats.hit_rate || 0) * 100).toFixed(1)}%`, icon: BarChart3, color: 'text-amber-400' },
              { label: 'Embeddings', value: stats.total_embeddings || stats.embeddings || 0, icon: Database, color: 'text-purple-400' },
            ].map((s) => (
              <div key={s.label} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <s.icon className={`w-4 h-4 ${s.color}`} />
                  <span className="text-xs text-slate-500 uppercase">{s.label}</span>
                </div>
                <div className="text-2xl font-bold text-white">{s.value}</div>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-white mb-4">Acciones</h2>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => handleAction('invalidate')}
                disabled={actionLoading === 'invalidate'}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/20 disabled:opacity-50 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                {actionLoading === 'invalidate' ? 'Invalidando...' : 'Invalidar Todo'}
              </button>
              <button
                onClick={() => handleAction('cleanup')}
                disabled={actionLoading === 'cleanup'}
                className="flex items-center gap-2 px-4 py-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-sm hover:bg-amber-500/20 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${actionLoading === 'cleanup' ? 'animate-spin' : ''}`} />
                {actionLoading === 'cleanup' ? 'Limpiando...' : 'Limpiar Expirados'}
              </button>
            </div>
          </div>

          {/* Config */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-white mb-4">Configuracion</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-500">Umbral similitud</span>
                <div className="text-white">{stats.similarity_threshold ?? '0.85'}</div>
              </div>
              <div>
                <span className="text-slate-500">TTL</span>
                <div className="text-white">{stats.ttl_seconds ? `${stats.ttl_seconds}s` : 'N/A'}</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
