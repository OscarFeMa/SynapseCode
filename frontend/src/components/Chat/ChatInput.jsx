import { useState } from 'react'
import { Send, Loader2, Settings2 } from 'lucide-react'
import { useCreateSession } from '../../hooks/useSession'
import { useConfigStore, useSessionStore } from '../../store/useStore'

export function ChatInput({ onSessionCreated }) {
  const [query, setQuery] = useState('')
  const [title, setTitle] = useState('')
  const [showOptions, setShowOptions] = useState(false)
  const [maxRounds, setMaxRounds] = useState(2)
  
  const { create, isLoading, error } = useCreateSession()
  const { defaultRounds } = useConfigStore()
  const { clearError } = useSessionStore()
  
  // Initialize maxRounds from config
  useState(() => setMaxRounds(defaultRounds))
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim() || isLoading) return
    
    clearError()
    const sessionId = await create(query.trim(), title.trim() || null, maxRounds)
    
    if (sessionId && onSessionCreated) {
      onSessionCreated(sessionId)
      // Reset form
      setQuery('')
      setTitle('')
    }
  }
  
  const suggestedQueries = [
    "¿Debería implementar una semana laboral de 4 días?",
    "¿Cuáles son los riesgos de migrar a microservicios?",
    "¿Vale la pena adoptar Rust para mi proyecto?",
    "¿Cómo debería estructurar mi equipo de IA?",
  ]
  
  return (
    <div className="w-full max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">
          Synapse <span className="text-amber-500">Council</span>
        </h1>
        <p className="text-slate-400">
          Razonamiento colectivo híbrido con Tribunal de Magistrados
        </p>
      </div>
      
      {/* Error display */}
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          {error}
        </div>
      )}
      
      {/* Input form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Title input (optional) */}
        <div className="relative">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Título opcional..."
            className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-slate-300 placeholder-slate-500 focus:border-amber-500 focus:outline-none transition-colors"
          />
        </div>
        
        {/* Main query textarea */}
        <div className="relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Plantea tu pregunta o problema para el consejo de IAs..."
            rows={4}
            maxLength={2000}
            className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none transition-colors resize-none"
          />
          <div className="absolute bottom-3 right-3 text-xs text-slate-500">
            {query.length}/2000
          </div>
        </div>
        
        {/* Options toggle */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => setShowOptions(!showOptions)}
            className="flex items-center gap-2 text-slate-400 hover:text-amber-500 transition-colors"
          >
            <Settings2 size={18} />
            <span className="text-sm">Opciones</span>
          </button>
          
          {/* Submit button */}
          <button
            type="submit"
            disabled={!query.trim() || isLoading}
            className="flex items-center gap-2 px-6 py-2 bg-amber-500 hover:bg-amber-600 disabled:bg-slate-700 disabled:cursor-not-allowed text-slate-900 font-semibold rounded-lg transition-colors"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Iniciando...</span>
              </>
            ) : (
              <>
                <Send size={18} />
                <span>Consultar al Consejo</span>
              </>
            )}
          </button>
        </div>
        
        {/* Advanced options */}
        {showOptions && (
          <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-4 animate-fade-in">
            <div>
              <label className="block text-sm text-slate-400 mb-2">
                Número de rondas de debate
              </label>
              <div className="flex gap-2">
                {[1, 2, 3].map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => setMaxRounds(num)}
                    className={`px-4 py-2 rounded-lg border transition-colors ${
                      maxRounds === num
                        ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                        : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    {num} {num === 1 ? 'ronda' : 'rondas'}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Más rondas = mayor profundidad pero más tiempo y tokens.
                El sistema detendrá automáticamente si se alcanza convergencia.
              </p>
            </div>
          </div>
        )}
      </form>
      
      {/* Suggested queries */}
      {!query && (
        <div className="mt-8">
          <p className="text-sm text-slate-500 mb-3">Ejemplos de consultas:</p>
          <div className="flex flex-wrap gap-2">
            {suggestedQueries.map((q, i) => (
              <button
                key={i}
                onClick={() => setQuery(q)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-full text-sm text-slate-400 hover:text-slate-200 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Info */}
      <div className="mt-8 p-4 bg-slate-800/30 rounded-lg border border-slate-800">
        <h3 className="text-sm font-semibold text-amber-500 mb-2">¿Cómo funciona?</h3>
        <ul className="text-sm text-slate-400 space-y-1">
          <li>• 4 analistas (2 locales + 2 en nube) examinan tu consulta desde diferentes ángulos</li>
          <li>• 4 críticos cruzan y evalúan los análisis (cruce híbrido)</li>
          <li>• 2 sintetizadores integran las perspectivas</li>
          <li>• El <strong>Tribunal de Magistrados</strong> (3 roles) emite el veredicto final</li>
          <li>• Streaming en tiempo real de todo el proceso</li>
        </ul>
      </div>
    </div>
  )
}
