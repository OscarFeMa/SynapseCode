import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Filter, Plus, Eye, Trash2, Play, Pause, RefreshCw } from 'lucide-react'
import { useSessionStore } from '../store/useStore'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { toast } from 'sonner'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const statusConfig = {
  created: { label: 'Creado', badge: 'badge-neutral', dot: 'bg-[#B8B5AE]' },
  running: { label: 'En curso', badge: 'badge-neutral', dot: 'bg-[#6E8B74] animate-pulse' },
  completed: { label: 'Completado', badge: 'badge-success', dot: 'bg-[#4A7C59]' },
  failed: { label: 'Fallido', badge: 'badge-error', dot: 'bg-[#8B3A3A]' },
  paused: { label: 'Pausado', badge: 'badge-warning', dot: 'bg-[#B98B4D]' },
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
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl text-[#161616]">Debates</h1>
          <p className="text-sm text-[#5C5C5C] mt-1">
            {filtered.length} debates{statusFilter !== 'all' && ` (${statusFilter})`}
          </p>
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

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8A8780]" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Buscar por tema o ID..."
            className="w-full pl-10 pr-4 py-2 bg-white border border-[rgba(0,0,0,0.08)] rounded text-sm text-[#161616] placeholder-[#8A8780] focus:outline-none focus:border-[rgba(0,0,0,0.16)]"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-[#8A8780]" />
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setPage(1)
            }}
            className="px-3 py-2 bg-white border border-[rgba(0,0,0,0.08)] rounded text-sm text-[#161616] focus:outline-none focus:border-[rgba(0,0,0,0.16)]"
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
          className="p-2 bg-white border border-[rgba(0,0,0,0.08)] rounded text-[#5C5C5C] hover:text-[#161616] hover:border-[rgba(0,0,0,0.12)] transition-colors"
          title="Refrescar"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Table */}
      <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg shadow-card overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-[#8A8780]">Cargando debates...</div>
        ) : paginated.length === 0 ? (
          <div className="p-8 text-center text-[#8A8780]">
            <p>No se encontraron debates</p>
            <Link to="/debates/new" className="text-[#23403B] text-sm hover:text-[#2D524C] mt-2 inline-block font-medium">
              Crear uno →
            </Link>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[rgba(0,0,0,0.06)]">
                    <th className="text-left px-5 py-3 text-xs font-semibold text-[#8A8780] uppercase tracking-wider">
                      Tema
                    </th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-[#8A8780] uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-[#8A8780] uppercase tracking-wider hidden md:table-cell">
                      Creado
                    </th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-[#8A8780] uppercase tracking-wider hidden lg:table-cell">
                      Turnos
                    </th>
                    <th className="text-right px-5 py-3 text-xs font-semibold text-[#8A8780] uppercase tracking-wider">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(0,0,0,0.04)]">
                  {paginated.map((session) => {
                    const sc = statusConfig[session.status] || statusConfig.created
                    return (
                      <tr
                        key={session.id}
                        className="hover:bg-[#F5F3EE] transition-colors"
                      >
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full ${sc.dot}`} />
                            <div>
                              <Link
                                to={`/debates/${session.id}`}
                                className="text-[#161616] hover:text-[#23403B] transition-colors font-medium truncate block max-w-[300px]"
                              >
                                {session.topic || 'Sin titulo'}
                              </Link>
                              <span className="text-xs text-[#8A8780] font-mono">{session.id}</span>
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span className={`text-xs px-2.5 py-1 rounded font-medium ${sc.badge}`}>
                            {sc.label}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-[#5C5C5C] hidden md:table-cell">
                          {session.created_at
                            ? formatDistanceToNow(new Date(session.created_at), { locale: es, addSuffix: true })
                            : '-'}
                        </td>
                        <td className="px-5 py-3 text-[#5C5C5C] font-mono tabular-nums hidden lg:table-cell">
                          {session.turns?.length || 0}
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex items-center justify-end gap-1">
                            <Link
                              to={`/debates/${session.id}`}
                              className="p-1.5 text-[#5C5C5C] hover:text-[#161616] hover:bg-[#F5F3EE] rounded transition-colors"
                              title="Ver"
                            >
                              <Eye className="w-4 h-4" />
                            </Link>
                            {session.status === 'running' && (
                              <button
                                onClick={() => handlePause(session.id)}
                                className="p-1.5 text-[#B98B4D] hover:bg-[#F5F3EE] rounded transition-colors"
                                title="Pausar"
                              >
                                <Pause className="w-4 h-4" />
                              </button>
                            )}
                            {session.status === 'paused' && (
                              <button
                                onClick={() => handleResume(session.id)}
                                className="p-1.5 text-[#4A7C59] hover:bg-[#F5F3EE] rounded transition-colors"
                                title="Reanudar"
                              >
                                <Play className="w-4 h-4" />
                              </button>
                            )}
                            <button
                              onClick={() => handleDelete(session.id)}
                              className="p-1.5 text-[#8B3A3A] hover:bg-[#F5F3EE] rounded transition-colors"
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
              <div className="flex items-center justify-between px-5 py-3 border-t border-[rgba(0,0,0,0.06)]">
                <span className="text-xs text-[#8A8780]">
                  Mostrando {(page - 1) * perPage + 1}-{Math.min(page * perPage, filtered.length)} de{' '}
                  {filtered.length}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 text-xs bg-white border border-[rgba(0,0,0,0.08)] text-[#5C5C5C] rounded hover:text-[#161616] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Anterior
                  </button>
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`w-7 h-7 text-xs rounded transition-colors ${
                        p === page
                          ? 'bg-[#23403B] text-[#F5F3EE] font-medium'
                          : 'text-[#5C5C5C] hover:bg-[#F5F3EE]'
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1 text-xs bg-white border border-[rgba(0,0,0,0.08)] text-[#5C5C5C] rounded hover:text-[#161616] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
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
