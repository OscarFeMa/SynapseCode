import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Filter, Plus, Eye, Trash2, Play, Pause, RefreshCw } from 'lucide-react'
import { useSessionStore } from '../store/useStore'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { toast } from 'sonner'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const statusConfig = {
  created: { label: 'Creado', color: 'bg-slate-700 text-slate-300', dot: 'bg-slate-500' },
  running: { label: 'En curso', color: 'bg-blue-500/10 text-blue-400', dot: 'bg-blue-500 animate-pulse' },
  completed: { label: 'Completado', color: 'bg-emerald-500/10 text-emerald-400', dot: 'bg-emerald-500' },
  failed: { label: 'Fallido', color: 'bg-red-500/10 text-red-400', dot: 'bg-red-500' },
  paused: { label: 'Pausado', color: 'bg-amber-500/10 text-amber-400', dot: 'bg-amber-500' },
}

export function DebatesPage() {
  const sessions = useSessionStore((s) => s.sessions)
  const fetchSessions = useSessionStore((s) => s.fetchSessions)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const perPage = 10

  useEffect(() => {
    const load = async () => {
      try {
        await fetchSessions()
      } catch (e) {
        console.warn('Failed to fetch sessions:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [fetchSessions])

  const filtered = sessions.filter((s) => {
    const matchSearch =
      !search ||
      s.topic?.toLowerCase().includes(search.toLowerCase()) ||
      s.id?.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || s.status === statusFilter
    return matchSearch && matchStatus
  })

  const totalPages = Math.ceil(filtered.length / perPage)
  const paginated = filtered.slice((page - 1) * perPage, page * perPage)

  const handleDelete = async (id) => {
    if (!confirm('Eliminar este debate?')) return
    try {
      await fetch(`${API_BASE}/api/v1/sessions/${id}`, { method: 'DELETE' })
      toast.success('Debate eliminado')
      await fetchSessions()
    } catch (e) {
      toast.error('Error al eliminar el debate')
    }
  }

  const handlePause = async (id) => {
    try {
      await fetch(`${API_BASE}/api/v1/sessions/${id}/pause`, { method: 'POST' })
      toast.info('Debate pausado')
      await fetchSessions()
    } catch (e) {
      toast.error('Error al pausar')
    }
  }

  const handleResume = async (id) => {
    try {
      await fetch(`${API_BASE}/api/v1/sessions/${id}/resume`, { method: 'POST' })
      toast.info('Debate reanudado')
      await fetchSessions()
    } catch (e) {
      toast.error('Error al reanudar')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Debates</h1>
          <p className="text-sm text-slate-400 mt-1">
            {filtered.length} debates{statusFilter !== 'all' && ` (${statusFilter})`}
          </p>
        </div>
        <Link
          to="/debates/new"
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-900 text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nuevo Debate
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Buscar por tema o ID..."
            className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setPage(1)
            }}
            className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-sm text-white focus:outline-none focus:border-amber-500"
          >
            <option value="all">Todos</option>
            <option value="running">En curso</option>
            <option value="completed">Completados</option>
            <option value="paused">Pausados</option>
            <option value="failed">Fallidos</option>
            <option value="created">Creados</option>
          </select>
        </div>
        <button
          onClick={() => fetchSessions()}
          className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 hover:text-white hover:border-slate-700 transition-colors"
          title="Refrescar"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-500">Cargando debates...</div>
        ) : paginated.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <p>No se encontraron debates</p>
            <Link to="/debates/new" className="text-amber-500 text-sm hover:text-amber-400 mt-2 inline-block">
              Crear uno →
            </Link>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Tema
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">
                      Creado
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden lg:table-cell">
                      Turnos
                    </th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((session) => {
                    const sc = statusConfig[session.status] || statusConfig.created
                    return (
                      <tr
                        key={session.id}
                        className="border-b border-slate-800/50 hover:bg-slate-800/50 transition-colors"
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full ${sc.dot}`} />
                            <div>
                              <Link
                                to={`/debates/${session.id}`}
                                className="text-white hover:text-amber-400 transition-colors font-medium truncate block max-w-[300px]"
                              >
                                {session.topic || 'Sin titulo'}
                              </Link>
                              <span className="text-xs text-slate-500 font-mono">{session.id}</span>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-1 rounded-full font-medium ${sc.color}`}>
                            {sc.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400 hidden md:table-cell">
                          {session.created_at
                            ? formatDistanceToNow(new Date(session.created_at), { locale: es, addSuffix: true })
                            : '-'}
                        </td>
                        <td className="px-4 py-3 text-slate-400 hidden lg:table-cell">
                          {session.turns?.length || 0}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-1">
                            <Link
                              to={`/debates/${session.id}`}
                              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
                              title="Ver"
                            >
                              <Eye className="w-4 h-4" />
                            </Link>
                            {session.status === 'running' && (
                              <button
                                onClick={() => handlePause(session.id)}
                                className="p-1.5 text-amber-400 hover:bg-slate-700 rounded transition-colors"
                                title="Pausar"
                              >
                                <Pause className="w-4 h-4" />
                              </button>
                            )}
                            {session.status === 'paused' && (
                              <button
                                onClick={() => handleResume(session.id)}
                                className="p-1.5 text-emerald-400 hover:bg-slate-700 rounded transition-colors"
                                title="Reanudar"
                              >
                                <Play className="w-4 h-4" />
                              </button>
                            )}
                            <button
                              onClick={() => handleDelete(session.id)}
                              className="p-1.5 text-red-400 hover:bg-slate-700 rounded transition-colors"
                              title="Eliminar"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
                <span className="text-xs text-slate-500">
                  Mostrando {(page - 1) * perPage + 1}-{Math.min(page * perPage, filtered.length)} de{' '}
                  {filtered.length}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 text-xs bg-slate-800 text-slate-400 rounded hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Anterior
                  </button>
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`w-7 h-7 text-xs rounded transition-colors ${
                        p === page
                          ? 'bg-amber-500 text-slate-900 font-medium'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1 text-xs bg-slate-800 text-slate-400 rounded hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Siguiente
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
