import { useState, useEffect } from 'react'
import { Search, Filter, Download, Eye, Calendar, Clock, CheckCircle, XCircle } from 'lucide-react'

export function DatabaseViewer() {
  const [debates, setDebates] = useState([])
  const [filteredDebates, setFilteredDebates] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [modeFilter, setModeFilter] = useState('all')
  const [selectedDebate, setSelectedDebate] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDebates()
  }, [])

  useEffect(() => {
    filterDebates()
  }, [debates, searchQuery, statusFilter, modeFilter])

  const fetchDebates = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/debate/history')
      if (response.ok) {
        const data = await response.json()
        setDebates(data)
      }
    } catch (e) {
      console.error('Failed to fetch debates:', e)
    } finally {
      setLoading(false)
    }
  }

  const filterDebates = () => {
    let filtered = [...debates]

    if (searchQuery) {
      filtered = filtered.filter(d => 
        d.topic?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.id?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(d => d.status === statusFilter)
    }

    if (modeFilter !== 'all') {
      filtered = filtered.filter(d => d.mode === modeFilter)
    }

    setFilteredDebates(filtered)
  }

  const handleExport = async (debate) => {
    const data = JSON.stringify(debate, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `debate-${debate.id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExportAll = () => {
    filteredDebates.forEach(debate => handleExport(debate))
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-200 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p>Cargando base de datos...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {/* Header */}
      <nav className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-white">Base de Datos de Debates</h1>
            <button
              onClick={handleExportAll}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              <span className="text-sm">Exportar Todo</span>
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Filters */}
        <div className="mb-6 p-4 bg-slate-800/50 rounded-xl border border-slate-700">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Buscar por tema o ID..."
                  className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none"
                />
              </div>
            </div>
            <div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:border-amber-500 focus:outline-none"
              >
                <option value="all">Todos los estados</option>
                <option value="completed">Completados</option>
                <option value="running">En ejecución</option>
                <option value="failed">Fallidos</option>
              </select>
            </div>
            <div>
              <select
                value={modeFilter}
                onChange={(e) => setModeFilter(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:border-amber-500 focus:outline-none"
              >
                <option value="all">Todos los modos</option>
                <option value="standard">Standard</option>
                <option value="ultra_crossing">Ultra Crossing</option>
                <option value="local_only">Local Only</option>
                <option value="cloud_ollama">Cloud Ollama</option>
              </select>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard label="Total" value={filteredDebates.length} color="blue" />
          <StatCard label="Completados" value={filteredDebates.filter(d => d.status === 'completed').length} color="green" />
          <StatCard label="En ejecución" value={filteredDebates.filter(d => d.status === 'running').length} color="amber" />
          <StatCard label="Fallidos" value={filteredDebates.filter(d => d.status === 'failed').length} color="red" />
        </div>

        {/* Debate List */}
        <div className="bg-slate-800/30 rounded-xl border border-slate-800 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-900/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-400">ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-400">Tema</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-400">Modo</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-400">Estado</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-400">Fecha</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-400">Tokens</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-slate-400">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredDebates.map((debate) => (
                <tr key={debate.id} className="border-t border-slate-800 hover:bg-slate-800/50 transition-colors">
                  <td className="px-4 py-3 text-sm text-slate-400 font-mono">{debate.id?.slice(0, 8)}...</td>
                  <td className="px-4 py-3 text-sm text-white max-w-xs truncate">{debate.topic}</td>
                  <td className="px-4 py-3 text-sm text-slate-400">{debate.mode}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={debate.status} />
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400">
                    {debate.created_at ? new Date(debate.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400">
                    {debate.total_tokens_out?.toLocaleString() || 0}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setSelectedDebate(debate)}
                      className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleExport(debate)}
                      className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredDebates.length === 0 && (
            <div className="p-8 text-center text-slate-500">
              No se encontraron debates
            </div>
          )}
        </div>

        {/* Detail Modal */}
        {selectedDebate && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-slate-900 rounded-xl border border-slate-800 max-w-4xl w-full max-h-[80vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">Detalle del Debate</h2>
                  <button
                    onClick={() => setSelectedDebate(null)}
                    className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                  >
                    ✕
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-slate-400 mb-1">ID</p>
                    <p className="text-white font-mono">{selectedDebate.id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400 mb-1">Tema</p>
                    <p className="text-white">{selectedDebate.topic}</p>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-slate-400 mb-1">Modo</p>
                      <p className="text-white">{selectedDebate.mode}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-400 mb-1">Estado</p>
                      <StatusBadge status={selectedDebate.status} />
                    </div>
                    <div>
                      <p className="text-sm text-slate-400 mb-1">Fecha</p>
                      <p className="text-white">{selectedDebate.created_at}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-slate-400 mb-1">Tokens In</p>
                      <p className="text-white">{selectedDebate.total_tokens_in?.toLocaleString() || 0}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-400 mb-1">Tokens Out</p>
                      <p className="text-white">{selectedDebate.total_tokens_out?.toLocaleString() || 0}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-400 mb-1">Latencia</p>
                      <p className="text-white">{selectedDebate.total_latency_ms}ms</p>
                    </div>
                  </div>

                  {selectedDebate.turns && selectedDebate.turns.length > 0 && (
                    <div>
                      <p className="text-sm text-slate-400 mb-2">Turnos ({selectedDebate.turns.length})</p>
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {selectedDebate.turns.map((turn, i) => (
                          <div key={i} className="p-3 bg-slate-800/50 rounded-lg">
                            <div className="flex items-center justify-between mb-1">
                              <p className="text-sm font-semibold text-white">{turn.agent_name}</p>
                              <p className="text-xs text-slate-500">{turn.model}</p>
                            </div>
                            <p className="text-xs text-slate-400 line-clamp-2">{turn.response_preview}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }) {
  const colorClasses = {
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
    amber: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
    red: 'bg-red-500/10 border-red-500/30 text-red-400'
  }

  return (
    <div className={`p-4 rounded-xl border ${colorClasses[color]}`}>
      <p className="text-sm text-slate-400 mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  )
}

function StatusBadge({ status }) {
  const statusConfig = {
    completed: { color: 'bg-green-500/10 text-green-400 border-green-500/30', icon: CheckCircle },
    running: { color: 'bg-amber-500/10 text-amber-400 border-amber-500/30', icon: Clock },
    failed: { color: 'bg-red-500/10 text-red-400 border-red-500/30', icon: XCircle }
  }

  const config = statusConfig[status] || statusConfig.running
  const Icon = config.icon

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border ${config.color}`}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  )
}
