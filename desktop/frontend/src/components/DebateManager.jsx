import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Plus, Eye, Trash2, Loader2, Settings2 } from 'lucide-react'

export function DebateManager() {
  const navigate = useNavigate()
  const [activeDebates, setActiveDebates] = useState([])
  const [showNewDebate, setShowNewDebate] = useState(false)
  const [newDebateConfig, setNewDebateConfig] = useState({
    topic: '',
    mode: 'standard',
    maxRounds: 2
  })
  const [isLoading, setIsLoading] = useState(false)

  const debateModes = [
    { id: 'standard', name: 'Standard', description: '4 analistas + 4 críticos + 2 sintetizadores' },
    { id: 'ultra_crossing', name: 'Ultra Crossing', description: 'Debate multi-etapa con Groq' },
    { id: 'local_only', name: 'Local Only', description: 'Solo modelos locales (Ollama)' },
    { id: 'cloud_ollama', name: 'Cloud Ollama', description: 'Modelos Ollama Cloud' }
  ]

  useEffect(() => {
    fetchActiveDebates()
    const interval = setInterval(fetchActiveDebates, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchActiveDebates = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/debate/active')
      if (response.ok) {
        const data = await response.json()
        setActiveDebates(data)
      }
    } catch (e) {
      console.error('Failed to fetch active debates:', e)
    }
  }

  const handleCreateDebate = async () => {
    if (!newDebateConfig.topic.trim()) return

    setIsLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/debate/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: newDebateConfig.topic,
          mode: newDebateConfig.mode,
          max_turns: newDebateConfig.maxRounds
        })
      })

      if (response.ok) {
        const data = await response.json()
        navigate(`/session/${data.session_id}`)
      }
    } catch (e) {
      console.error('Failed to create debate:', e)
    } finally {
      setIsLoading(false)
    }
  }

  const handleViewDebate = (sessionId) => {
    navigate(`/session/${sessionId}`)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {/* Header */}
      <nav className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-white">Gestor de Debates</h1>
            <button
              onClick={() => setShowNewDebate(!showNewDebate)}
              className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-900 font-semibold rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Nuevo Debate</span>
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* New Debate Form */}
        {showNewDebate && (
          <div className="mb-6 p-6 bg-slate-800/50 rounded-xl border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-4">Crear Nuevo Debate</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Tema del Debate</label>
                <textarea
                  value={newDebateConfig.topic}
                  onChange={(e) => setNewDebateConfig({ ...newDebateConfig, topic: e.target.value })}
                  placeholder="Describe el tema o pregunta para el debate..."
                  rows={3}
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none resize-none"
                />
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Modo de Debate</label>
                <div className="grid grid-cols-2 gap-3">
                  {debateModes.map((mode) => (
                    <button
                      key={mode.id}
                      onClick={() => setNewDebateConfig({ ...newDebateConfig, mode: mode.id })}
                      className={`p-4 rounded-lg border-2 text-left transition-all ${
                        newDebateConfig.mode === mode.id
                          ? 'bg-amber-500/10 border-amber-500'
                          : 'bg-slate-900 border-slate-700 hover:border-slate-600'
                      }`}
                    >
                      <p className="font-semibold text-white mb-1">{mode.name}</p>
                      <p className="text-xs text-slate-400">{mode.description}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Número de Rondas</label>
                <div className="flex gap-2">
                  {[1, 2, 3].map((num) => (
                    <button
                      key={num}
                      onClick={() => setNewDebateConfig({ ...newDebateConfig, maxRounds: num })}
                      className={`px-4 py-2 rounded-lg border transition-colors ${
                        newDebateConfig.maxRounds === num
                          ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                          : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      {num} {num === 1 ? 'ronda' : 'rondas'}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleCreateDebate}
                  disabled={!newDebateConfig.topic.trim() || isLoading}
                  className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-amber-500 hover:bg-amber-600 disabled:bg-slate-700 disabled:cursor-not-allowed text-slate-900 font-semibold rounded-lg transition-colors"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Iniciando...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5" />
                      <span>Iniciar Debate</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => setShowNewDebate(false)}
                  className="px-6 py-3 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Active Debates */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Debates Activos ({activeDebates.length})</h2>
          
          {activeDebates.length === 0 ? (
            <div className="p-8 bg-slate-800/30 rounded-xl border border-slate-800 text-center text-slate-500">
              No hay debates activos. Crea uno nuevo para comenzar.
            </div>
          ) : (
            <div className="grid gap-4">
              {activeDebates.map((debate) => (
                <div key={debate.id} className="p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          debate.mode === 'ultra_crossing' ? 'bg-purple-500/20 text-purple-400' :
                          debate.mode === 'local_only' ? 'bg-blue-500/20 text-blue-400' :
                          debate.mode === 'cloud_ollama' ? 'bg-green-500/20 text-green-400' :
                          'bg-amber-500/20 text-amber-400'
                        }`}>
                          {debate.mode}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          debate.status === 'running' ? 'bg-green-500/20 text-green-400' :
                          debate.status === 'completed' ? 'bg-blue-500/20 text-blue-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {debate.status}
                        </span>
                      </div>
                      <h3 className="font-semibold text-white mb-1">{debate.topic}</h3>
                      <p className="text-sm text-slate-400">
                        ID: {debate.id?.slice(0, 8)}... | 
                        Turnos: {debate.turns?.length || 0} | 
                        Tokens: {debate.total_tokens_out?.toLocaleString() || 0}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleViewDebate(debate.id)}
                        className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                        title="Ver debate"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Info */}
        <div className="mt-8 p-4 bg-slate-800/30 rounded-xl border border-slate-800">
          <h3 className="text-sm font-semibold text-amber-500 mb-2">Información sobre Modos</h3>
          <div className="space-y-2 text-sm text-slate-400">
            <p><strong>Standard:</strong> 4 analistas (2 locales + 2 nube) + 4 críticos + 2 sintetizadores + Tribunal</p>
            <p><strong>Ultra Crossing:</strong> Debate multi-etapa con Groq (Propuestas → Expansión → Crítica → Síntesis)</p>
            <p><strong>Local Only:</strong> Solo modelos locales (Ollama, LM Studio, Jan)</p>
            <p><strong>Cloud Ollama:</strong> Modelos Ollama Cloud ejecutados localmente</p>
          </div>
        </div>
      </div>
    </div>
  )
}
