import { useEffect, useState } from 'react'
import { Search, RefreshCw, Star, Zap, Brain, Code } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const specIcons = {
  coding: Code,
  reasoning: Brain,
  fast: Zap,
  analysis: Star,
}

export function ModelsPage() {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterProvider, setFilterProvider] = useState('all')
  const [updating, setUpdating] = useState(false)

  const fetchModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/system/model-registry/models`)
      if (res.ok) {
        const data = await res.json()
        setModels(data.models || data || [])
      }
    } catch (e) {
      console.warn('Failed to fetch models, using defaults')
      setModels([
        { id: 'llama3.2:latest', provider: 'ollama', params_b: 3, context_window: 32000, rank: 7.5, strengths: ['Fast', 'General'] },
        { id: 'qwen2.5-coder:7b', provider: 'ollama', params_b: 7, context_window: 32000, rank: 8.2, strengths: ['Coding', 'Reasoning'] },
        { id: 'google/gemini-2.5-flash', provider: 'openrouter', params_b: 0, context_window: 1000000, rank: 9.0, strengths: ['Fast', 'Multimodal'] },
        { id: 'meta-llama/llama-3.3-70b-instruct', provider: 'openrouter', params_b: 70, context_window: 128000, rank: 8.8, strengths: ['Analysis', 'Reasoning'] },
        { id: 'deepseek-chat', provider: 'deepseek', params_b: 67, context_window: 128000, rank: 8.5, strengths: ['Coding', 'Fast'] },
        { id: 'groq/llama-3.1-8b-instant', provider: 'groq', params_b: 8, context_window: 128000, rank: 7.8, strengths: ['Fast'] },
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchModels()
  }, [])

  const handleUpdateRankings = async () => {
    setUpdating(true)
    try {
      await fetch(`${API_BASE}/api/system/model-registry/refresh-rankings`, { method: 'POST' })
      await fetchModels()
    } catch (e) {
      console.warn('Failed to update rankings')
    } finally {
      setUpdating(false)
    }
  }

  const providers = ['all', ...new Set(models.map((m) => m.provider || m.node))]
  const filtered = models.filter((m) => {
    const name = m.id || m.name || ''
    const matchSearch = !search || name.toLowerCase().includes(search.toLowerCase())
    const matchProvider = filterProvider === 'all' || m.provider === filterProvider || m.node === filterProvider
    return matchSearch && matchProvider
  })

  const getRankColor = (rank) => {
    if (rank >= 9) return 'text-[#4A7C59]'
    if (rank >= 8) return 'text-[#B98B4D]'
    if (rank >= 7) return 'text-[#23403B]'
    return 'text-[#8A8780]'
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl text-[#161616]">Model Registry</h1>
          <p className="text-sm text-[#5C5C5C] mt-1">{filtered.length} modelos registrados</p>
          <div className="w-8 h-0.5 bg-[#23403B] mt-3" />
        </div>
        <button
          onClick={handleUpdateRankings}
          disabled={updating}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-[rgba(0,0,0,0.08)] rounded text-sm text-[#5C5C5C] hover:text-[#161616] disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${updating ? 'animate-spin' : ''}`} />
          Actualizar Rankings
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8A8780]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar modelos..."
            className="w-full pl-10 pr-4 py-2 bg-white border border-[rgba(0,0,0,0.08)] rounded text-sm text-[#161616] placeholder-[#8A8780] focus:outline-none focus:border-[rgba(0,0,0,0.16)]"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {providers.map((p) => (
            <button
              key={p}
              onClick={() => setFilterProvider(p)}
              className={`px-3 py-1.5 text-xs rounded transition-colors ${
                filterProvider === p
                  ? 'bg-[#23403B]/[0.06] text-[#23403B] border border-[#23403B]/15 font-medium'
                  : 'bg-white text-[#5C5C5C] border border-[rgba(0,0,0,0.08)] hover:text-[#161616]'
              }`}
            >
              {p === 'all' ? 'Todos' : p}
            </button>
          ))}
        </div>
      </div>

      {/* Models Grid */}
      {loading ? (
        <div className="text-center py-12 text-[#8A8780]">Cargando modelos...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-[#8A8780]">No se encontraron modelos</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((model, i) => {
            const name = model.id || model.name || 'Unknown'
            const provider = model.provider || model.node || 'unknown'
            const rank = model.rank || model.ranking || 0
            const strengths = model.strengths || model.tags || []
            const ctx = model.context_window ? `${(model.context_window / 1000).toFixed(0)}K` : 'N/A'
            const params = model.params_b ? `${model.params_b}B` : 'Cloud'

            return (
              <div
                key={i}
                className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card hover:border-[rgba(0,0,0,0.12)] transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-[#161616] truncate">{name}</h3>
                    <span className="text-xs text-[#8A8780] capitalize">{provider}</span>
                  </div>
                  <div className={`text-lg font-serif ${getRankColor(rank)}`}>{rank.toFixed(1)}</div>
                </div>

                <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
                  <div className="bg-[#F5F3EE] rounded px-2 py-1.5">
                    <span className="text-[#8A8780]">Params</span>
                    <div className="text-[#161616] font-mono tabular-nums">{params}</div>
                  </div>
                  <div className="bg-[#F5F3EE] rounded px-2 py-1.5">
                    <span className="text-[#8A8780]">Contexto</span>
                    <div className="text-[#161616] font-mono tabular-nums">{ctx}</div>
                  </div>
                </div>

                {strengths.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {strengths.slice(0, 3).map((s) => {
                      const Icon = specIcons[s.toLowerCase()] || Star
                      return (
                        <span
                          key={s}
                          className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-[#F5F3EE] text-[#5C5C5C] rounded"
                        >
                          <Icon className="w-3 h-3" />
                          {s}
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
