import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, RefreshCw, Clock, Hash, DollarSign, Globe, ChevronDown, ChevronUp } from 'lucide-react'
import { useSession } from '../../hooks/useSession'
import { useWebSocket } from '../../hooks/useWebSocket'
import { useSessionStore, useWebSocketStore, useUIStore } from '../../store/useStore'
import { AgentCard } from './AgentCard'
import { TribunalPanel } from '../Tribunal/TribunalPanel'

export function SessionView() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  
  const { session, isLoading, error, refresh } = useSession(sessionId)
  const { isConnected, events, currentPhase, isSessionComplete } = useWebSocket(sessionId)
  const { agentTokens } = useWebSocketStore()
  const { setCurrentSession } = useSessionStore()
  const { showTribunalPanel } = useUIStore()
  const [showWebResults, setShowWebResults] = useState(false)
  
  // Set current session in store
  useEffect(() => {
    if (session) {
      setCurrentSession(session)
    }
  }, [session, setCurrentSession])
  
  // Build agent list from events and session data
  const getAgentsForPhase = (phase) => {
    const phaseEvents = events.filter(e => e.type === 'agent_completed' && e.payload.phase === phase)
    
    // Default agent IDs for each phase
    const defaultAgents = {
      ANALYSIS: ['analyst_local_a', 'analyst_local_b', 'analyst_cloud_a', 'analyst_cloud_b'],
      CRITIQUE: ['critic_local_a', 'critic_local_b', 'critic_cloud_a', 'critic_cloud_b'],
      SYNTHESIS: ['synth_local', 'synth_cloud'],
      TRIBUNAL: ['magistrate_evidence', 'magistrate_risk', 'magistrate_alignment'],
    }
    
    const ids = defaultAgents[phase] || []
    
    return ids.map(id => {
      const event = phaseEvents.find(e => e.payload.agent === id)
      return {
        id,
        status: agentTokens[id] ? 'COMPLETED' : (currentPhase === phase ? 'STREAMING' : 'PENDING'),
        model: event?.payload?.model || 'llama3.2',
        tokens: event?.payload?.tokens || 0,
      }
    })
  }
  
  // Get current round
  const currentRound = events.filter(e => e.type === 'round_start').length || 
                       (session?.rounds_executed || 0)
  
  // Status badge
  const getStatusBadge = () => {
    const status = session?.status || 'CREATED'
    const statusClasses = {
      CREATED: 'bg-slate-600',
      RUNNING: 'bg-blue-600 animate-pulse',
      COMPLETED: 'bg-green-600',
      FAILED: 'bg-red-600',
    }
    
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium text-white ${statusClasses[status] || 'bg-slate-600'}`}>
        {status}
      </span>
    )
  }
  
  // Consensus badge
  const getConsensusBadge = () => {
    const level = session?.consensus_level || 'UNKNOWN'
    const classes = {
      CONSENSUS_REACHED: 'bg-green-500/20 text-green-400 border border-green-500/30',
      PARTIAL_CONSENSUS: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
      DIVERGENT: 'bg-red-500/20 text-red-400 border border-red-500/30',
    }
    
    const labels = {
      CONSENSUS_REACHED: 'Consenso Alcanzado',
      PARTIAL_CONSENSUS: 'Consenso Parcial',
      DIVERGENT: 'Divergencia',
    }
    
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium ${classes[level] || 'bg-slate-700 text-slate-400'}`}>
        {labels[level] || level}
      </span>
    )
  }
  
  if (isLoading && !session) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="animate-spin text-amber-500" size={32} />
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen p-6">
        <div className="text-red-400 mb-4">Error: {error}</div>
        <button 
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
        >
          <ArrowLeft size={18} />
          Volver al inicio
        </button>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button 
                onClick={() => navigate('/')}
                className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <ArrowLeft size={20} />
              </button>
              
              <div>
                <h1 className="text-lg font-semibold text-white truncate max-w-md">
                  {session?.title || 'Sin título'}
                </h1>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span>{sessionId?.slice(0, 8)}...</span>
                  <span>•</span>
                  <span className={isConnected ? 'text-green-400' : 'text-red-400'}>
                    {isConnected ? '● En vivo' : '○ Desconectado'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {getStatusBadge()}
              {session?.consensus_level && getConsensusBadge()}
              
              <button 
                onClick={refresh}
                className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                title="Refrescar"
              >
                <RefreshCw size={18} />
              </button>
            </div>
          </div>
          
          {/* Progress bar */}
          {session?.status === 'RUNNING' && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span>Ronda {currentRound} de {session?.max_rounds}</span>
                <span>{currentPhase || 'Iniciando...'}</span>
              </div>
              <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-amber-500 transition-all duration-500"
                  style={{ width: `${(currentRound / (session?.max_rounds || 1)) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </header>
      
      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column: Debate flow */}
          <div className="lg:col-span-2 space-y-6">
            {/* Query card */}
            <div className="p-4 bg-slate-900 rounded-lg border border-slate-800">
              <h3 className="text-xs font-medium text-slate-500 uppercase mb-2">Consulta</h3>
              <p className="text-slate-200">{session?.query}</p>
            </div>
            
            {/* Web Search Results */}
            {session?.web_context && (
              <div className="p-4 bg-slate-900 rounded-lg border border-cyan-500/30">
                <button
                  onClick={() => setShowWebResults(!showWebResults)}
                  className="w-full flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-2">
                    <Globe size={16} className="text-cyan-400" />
                    <h3 className="text-sm font-semibold text-cyan-400">
                      Búsqueda Web ({session.web_context.searches?.filter(s => s.success).length || 0} fuentes)
                    </h3>
                    <span className="px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 text-xs">
                      {new Date(session.web_context.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  {showWebResults ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                
                {showWebResults && (
                  <div className="mt-4 space-y-4 max-h-96 overflow-y-auto">
                    {session.web_context.searches?.map((result, i) => (
                      <div key={i} className={`p-3 rounded-lg border ${result.success ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-slate-200">{result.site_label}</span>
                          <span className={`px-2 py-0.5 rounded text-xs ${result.success ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                            {result.success ? '✅ Disponible' : '❌ Error'}
                          </span>
                        </div>
                        {result.success ? (
                          <p className="text-sm text-slate-300 whitespace-pre-wrap">{result.response?.slice(0, 1500)}{result.response?.length > 1500 ? '...' : ''}</p>
                        ) : (
                          <p className="text-sm text-red-400">{result.error}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* Phase: Analysis */}
            <section>
              <h2 className="text-sm font-semibold text-blue-400 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-400" />
                Fase 1: Análisis (4 perspectivas)
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {getAgentsForPhase('ANALYSIS').map(agent => (
                  <AgentCard key={agent.id} {...agent} phase="ANALYSIS" />
                ))}
              </div>
            </section>
            
            {/* Phase: Critique */}
            {(currentPhase === 'CRITIQUE' || currentPhase === 'SYNTHESIS' || currentPhase === 'TRIBUNAL' || isSessionComplete) && (
              <section>
                <h2 className="text-sm font-semibold text-yellow-400 mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-yellow-400" />
                  Fase 2: Crítica (cruce híbrido)
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {getAgentsForPhase('CRITIQUE').map(agent => (
                    <AgentCard key={agent.id} {...agent} phase="CRITIQUE" />
                  ))}
                </div>
              </section>
            )}
            
            {/* Phase: Synthesis */}
            {(currentPhase === 'SYNTHESIS' || currentPhase === 'TRIBUNAL' || isSessionComplete) && (
              <section>
                <h2 className="text-sm font-semibold text-purple-400 mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-purple-400" />
                  Fase 3: Síntesis (integración por nodo)
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {getAgentsForPhase('SYNTHESIS').map(agent => (
                    <AgentCard key={agent.id} {...agent} phase="SYNTHESIS" />
                  ))}
                </div>
              </section>
            )}
            
            {/* Final Summary */}
            {session?.final_summary && (
              <section className="p-6 bg-slate-900/50 rounded-lg border border-amber-500/30">
                <h2 className="text-lg font-semibold text-amber-400 mb-4">
                  🏛️ Veredicto Final del Tribunal
                </h2>
                <div className="prose prose-invert prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-slate-300">
                    {session.final_summary}
                  </pre>
                </div>
              </section>
            )}
          </div>
          
          {/* Right column: Tribunal & Stats */}
          <div className="space-y-6">
            {/* Tribunal Panel */}
            {showTribunalPanel && (
              <TribunalPanel 
                sessionId={sessionId}
                verdict={session?.tribunal_verdict}
                isActive={currentPhase === 'TRIBUNAL' || (currentPhase === 'SYNTHESIS' && !isSessionComplete)}
              />
            )}
            
            {/* Stats */}
            <div className="p-4 bg-slate-900 rounded-lg border border-slate-800">
              <h3 className="text-sm font-semibold text-slate-400 mb-4">Estadísticas</h3>
              
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-2">
                    <Hash size={14} />
                    Rondas
                  </span>
                  <span className="text-slate-300">{session?.rounds_executed || 0} / {session?.max_rounds || 0}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-2">
                    <Clock size={14} />
                    Tokens IN
                  </span>
                  <span className="text-slate-300">{session?.total_tokens_in?.toLocaleString() || 0}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-2">
                    <Clock size={14} />
                    Tokens OUT
                  </span>
                  <span className="text-slate-300">{session?.total_tokens_out?.toLocaleString() || 0}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 flex items-center gap-2">
                    <DollarSign size={14} />
                    Costo Est.
                  </span>
                  <span className="text-slate-300">${session?.estimated_cost_usd?.toFixed(4) || '0.0000'} USD</span>
                </div>
              </div>
            </div>
            
            {/* Events log */}
            <div className="p-4 bg-slate-900 rounded-lg border border-slate-800">
              <h3 className="text-sm font-semibold text-slate-400 mb-4">Eventos ({events.length})</h3>
              <div className="h-64 overflow-y-auto space-y-1 text-xs font-mono">
                {events.slice(-50).map((event, i) => (
                  <div key={i} className="text-slate-500">
                    <span className="text-amber-500/70">[{new Date(event.timestamp).toLocaleTimeString()}]</span>
                    {' '}
                    <span className={
                      event.type.includes('error') ? 'text-red-400' :
                      event.type.includes('completed') ? 'text-green-400' :
                      'text-slate-400'
                    }>
                      {event.type}
                    </span>
                  </div>
                ))}
                {events.length === 0 && (
                  <span className="text-slate-600 italic">Esperando eventos...</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
