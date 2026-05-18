import { useEffect, useState } from 'react'
import { Database, Trash2, RefreshCw, BarChart3 } from 'lucide-react'
import { toast } from 'sonner'

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
      toast.success(action === 'invalidate' ? 'Cache invalidado' : 'Cache expirado limpiado')
      await fetchStats()
    } catch (e) {
      toast.error(`Error al ${action === 'invalidate' ? 'invalidar' : 'limpiar'} el cache`)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl text-[#161616]">Cache Semantica</h1>
        <p className="text-sm text-[#5C5C5C] mt-1">Estadisticas, invalidacion y limpieza</p>
        <div className="w-8 h-0.5 bg-[#23403B] mt-3" />
      </div>

      {loading ? (
        <div className="text-center py-12 text-[#8A8780]">Cargando...</div>
      ) : !stats ? (
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-8 text-center shadow-card">
          <Database className="w-12 h-12 mx-auto text-[#B8B5AE] mb-3" />
          <p className="text-[#8A8780]">Cache no disponible o deshabilitado</p>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Entradas', value: stats.total_entries || stats.entries || 0, icon: Database, accent: 'text-[#23403B]' },
              { label: 'Hits', value: stats.total_hits || stats.hits || 0, icon: BarChart3, accent: 'text-[#4A7C59]' },
              { label: 'Hit Rate', value: `${((stats.hit_rate || 0) * 100).toFixed(1)}%`, icon: BarChart3, accent: 'text-[#B98B4D]' },
              { label: 'Embeddings', value: stats.total_embeddings || stats.embeddings || 0, icon: Database, accent: 'text-[#6E8B74]' },
            ].map((s) => (
              <div key={s.label} className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
                <div className="flex items-center gap-2 mb-2">
                  <s.icon className={`w-4 h-4 ${s.accent}`} />
                  <span className="text-xs text-[#8A8780] uppercase tracking-wider">{s.label}</span>
                </div>
                <div className="text-2xl font-serif text-[#161616]">{s.value}</div>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
            <h2 className="text-sm font-semibold text-[#161616] mb-4">Acciones</h2>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => handleAction('invalidate')}
                disabled={actionLoading === 'invalidate'}
                className="flex items-center gap-2 px-4 py-2 btn-secondary text-[#8B3A3A] border-[#8B3A3A]/20 hover:bg-[#8B3A3A] hover:text-white disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" />
                {actionLoading === 'invalidate' ? 'Invalidando...' : 'Invalidar Todo'}
              </button>
              <button
                onClick={() => handleAction('cleanup')}
                disabled={actionLoading === 'cleanup'}
                className="flex items-center gap-2 px-4 py-2 btn-secondary text-[#B98B4D] border-[#B98B4D]/20 hover:bg-[#B98B4D] hover:text-white disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${actionLoading === 'cleanup' ? 'animate-spin' : ''}`} />
                {actionLoading === 'cleanup' ? 'Limpiando...' : 'Limpiar Expirados'}
              </button>
            </div>
          </div>

          {/* Config */}
          <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
            <h2 className="text-sm font-semibold text-[#161616] mb-4">Configuracion</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-[#8A8780]">Umbral similitud</span>
                <div className="text-[#161616] font-mono tabular-nums">{stats.similarity_threshold ?? '0.85'}</div>
              </div>
              <div>
                <span className="text-[#8A8780]">TTL</span>
                <div className="text-[#161616] font-mono tabular-nums">{stats.ttl_seconds ? `${stats.ttl_seconds}s` : 'N/A'}</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
