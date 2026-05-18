import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Loader2, RefreshCw, Clock, Hash, DollarSign,
  Globe, ChevronDown, ChevronUp, FileText, GitBranch, Scale,
  FlaskConical, BarChart3, MessageSquare,
} from 'lucide-react'
import { useSession } from '../hooks/useSession'
import { useWebSocket } from '../hooks/useWebSocket'
import { useSessionStore, useWebSocketStore, useUIStore } from '../store/useStore'
import { AgentCard } from '../components/Chat/AgentCard'
import { TribunalPanel } from '../components/Tribunal/TribunalPanel'

const tabs = [
  { id: 'live', label: 'En Vivo', icon: MessageSquare },
  { id: 'turns', label: 'Turnos', icon: Hash },
  { id: 'cruzamientos', label: 'Cruzamientos', icon: GitBranch },
  { id: 'tribunal', label: 'Tribunal', icon: Scale },
  { id: 'reductio', label: 'Reductio', icon: FlaskConical },
  { id: 'report', label: 'Informe', icon: FileText },
]

export function DebateLivePage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('live')

  const { session, isLoading, error, refresh } = useSession(sessionId)
  const { isConnected, events, currentPhase, isSessionComplete } = useWebSocket(sessionId)
  const { agentTokens } = useWebSocketStore()
  const { setCurrentSession } = useSessionStore()
  const { showTribunalPanel } = useUIStore()
  const [showWebResults, setShowWebResults] = useState(false)

  useEffect(() => {
    if (session) setCurrentSession(session)
  }, [session, setCurrentSession])

  const getAgentsForPhase = (phase) => {
    const phaseEvents = events.filter(
      (e) => e.type === 'agent_completed' && e.payload.phase === phase
    )
    const defaultAgents = {
      ANALYSIS: ['analyst_local_a', 'analyst_local_b', 'analyst_cloud_a', 'analyst_cloud_b'],
      CRITIQUE: ['critic_local_a', 'critic_local_b', 'critic_cloud_a', 'critic_cloud_b'],
      SYNTHESIS: ['synth_local', 'synth_cloud'],
      TRIBUNAL: ['magistrate_evidence', 'magistrate_risk', 'magistrate_alignment'],
    }
    const ids = defaultAgents[phase] || []
    return ids.map((id) => {
      const event = phaseEvents.find((e) => e.payload.agent === id)
      return {
        id,
        status: agentTokens[id]
          ? 'COMPLETED'
          : currentPhase === phase
          ? 'STREAMING'
          : 'PENDING',
        model: event?.payload?.model || 'llama3.2',
        tokens: event?.payload?.tokens || 0,
      }
    })
  }

  const currentRound =
    events.filter((e) => e.type === 'round_start').length ||
    session?.rounds_executed || 0

  const getStatusBadge = () => {
    const status = session?.status || 'CREATED'
    const statusClasses = {
      CREATED: 'bg-slate-600',
      RUNNING: 'bg-blue-600 animate-pulse',
      COMPLETED: 'bg-emerald-600',
      FAILED: 'bg-red-600',
    }
    return (
      <span
        className={`px-3 py-1 rounded-full text-xs font-medium text-white ${
          statusClasses[status] || 'bg-slate-600'
        }`}
      >
        {status}
      </span>
    )
  }

  const getConsensusBadge = () => {
    const level = session?.consensus_level || 'UNKNOWN'
    const classes = {
      CONSENSUS_REACHED: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
      PARTIAL_CONSENSUS: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
      DIVERGENT: 'bg-red-500/20 text-red-400 border border-red-500/30',
      UNKNOWN: 'bg-slate-700 text-slate-400 border border-slate-600',
    }
    return (
      <span
        className={`px-3 py-1 rounded-full text-xs font-medium ${
          classes[level] || classes.UNKNOWN
        }`}
      >
        {level.replace(/_/g, ' ')}
      </span>
    )
  }

  const progress = session?.progress || 0
  const totalTokensIn = session?.turns?.reduce((sum, t) => sum + (t.tokens_in || 0), 0) || 0
  const totalTokensOut = session?.turns?.reduce((sum, t) => sum + (t.tokens_out || 0), 0) || 0

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-400 mb-4">Error al cargar la sesion</p>
        <button
          onClick={refresh}
          className="px-4 py-2 bg-slate-800 rounded-lg text-sm text-white hover:bg-slate-700"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/debates')}
            className="p-2 text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-semibold text-white">
              {session?.topic || 'Debate'}
            </h1>
            <p className="text-xs text-slate-500 font-mono">{sessionId}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {getStatusBadge()}
          {getConsensusBadge()}
          <button
            onClick={refresh}
            className="p-2 text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {session?.status === 'RUNNING' && (
        <div className="w-full bg-slate-800 rounded-full h-1.5">
          <div
            className="bg-amber-500 h-1.5 rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Stats bar */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" /> Round {currentRound}
        </span>
        <span className="flex items-center gap-1">
          <Hash className="w-3 h-3" /> {totalTokensIn.toLocale()} tokens IN
        </span>
        <span className="flex items-center gap-1">
          <DollarSign className="w-3 h-3" /> {totalTokensOut.toLocale()} tokens OUT
        </span>
        {session?.web_search && (
          <span className="flex items-center gap-1 text-blue-400">
            <Globe className="w-3 h-3" /> Web search
          </span>
        )}
        <span
          className={`flex items-center gap-1 ${
            isConnected ? 'text-emerald-400' : 'text-red-400'
          }`}
        >
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-emerald-400' : 'bg-red-400'
            }`}
          />
          {isConnected ? 'Live' : 'Disconnected'}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-800 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-amber-500 text-amber-500'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="min-h-[400px]">
        {activeTab === 'live' && (
          <LiveTab
            session={session}
            events={events}
            currentPhase={currentPhase}
            getAgentsForPhase={getAgentsForPhase}
            showWebResults={showWebResults}
            setShowWebResults={setShowWebResults}
          />
        )}
        {activeTab === 'turns' && <TurnsTab session={session} />}
        {activeTab === 'cruzamientos' && <CruzamientosTab session={session} />}
        {activeTab === 'tribunal' && <TribunalTab session={session} />}
        {activeTab === 'reductio' && <ReductioTab session={session} />}
        {activeTab === 'report' && <ReportTab session={session} />}
      </div>
    </div>
  )
}

function LiveTab({ session, events, currentPhase, getAgentsForPhase, showWebResults, setShowWebResults }) {
  const phases = ['ANALYSIS', 'CRITIQUE', 'SYNTHESIS', 'TRIBUNAL']
  const phaseLabels = {
    ANALYSIS: 'Analisis',
    CRITIQUE: 'Critica',
    SYNTHESIS: 'Sintesis',
    TRIBUNAL: 'Tribunal',
  }

  return (
    <div className="space-y-6">
      {/* Web results */}
      {session?.web_context && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl">
          <button
            onClick={() => setShowWebResults(!showWebResults)}
            className="flex items-center justify-between w-full p-4 text-left"
          >
            <span className="text-sm font-medium text-white flex items-center gap-2">
              <Globe className="w-4 h-4 text-blue-400" />
              Resultados Web
            </span>
            {showWebResults ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </button>
          {showWebResults && (
            <div className="px-4 pb-4 text-sm text-slate-400">
              {JSON.stringify(session.web_context, null, 2)}
            </div>
          )}
        </div>
      )}

      {/* Phases */}
      {phases.map((phase) => {
        const agents = getAgentsForPhase(phase)
        const isCurrentPhase = currentPhase === phase
        const hasCompleted = agents.some((a) => a.status === 'COMPLETED')
        if (!hasCompleted && !isCurrentPhase) return null

        return (
          <div key={phase} className="space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  isCurrentPhase
                    ? 'bg-amber-500 animate-pulse'
                    : hasCompleted
                    ? 'bg-emerald-500'
                    : 'bg-slate-600'
                }`}
              />
              {phaseLabels[phase]}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {agents.map((agent) => (
                <AgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          </div>
        )
      })}

      {/* Verdict */}
      {session?.status === 'COMPLETED' && session?.final_verdict && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-3">Veredicto Final</h3>
          <p className="text-sm text-slate-300 whitespace-pre-wrap">
            {session.final_verdict}
          </p>
        </div>
      )}
    </div>
  )
}

function TurnsTab({ session }) {
  const turns = session?.turns || []
  if (turns.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <Hash className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No hay turnos registrados</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {turns.map((turn) => (
        <details
          key={turn.turn_number}
          className="bg-slate-900 border border-slate-800 rounded-lg group"
        >
          <summary className="flex items-center justify-between p-4 cursor-pointer list-none">
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-amber-500">#{turn.turn_number}</span>
              <span className="text-sm text-white">{turn.agent?.name || turn.agent_name || 'Agent'}</span>
              <span className="text-xs text-slate-500">{turn.agent?.role || turn.agent_role || ''}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">
                {turn.tokens_in || 0} → {turn.tokens_out || 0}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  turn.status === 'completed'
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : turn.status === 'failed'
                    ? 'bg-red-500/10 text-red-400'
                    : 'bg-slate-700 text-slate-400'
                }`}
              >
                {turn.status}
              </span>
            </div>
          </summary>
          <div className="px-4 pb-4 text-sm text-slate-300 whitespace-pre-wrap border-t border-slate-800 pt-3">
            {turn.response_received || '(sin respuesta)'}
          </div>
        </details>
      ))}
    </div>
  )
}

function CruzamientosTab({ session }) {
  const iterations = session?.iterations || []
  const cruzamientos = iterations.flatMap((it) => it.cruzamientos || [])

  if (cruzamientos.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <GitBranch className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No hay cruzamientos registrados</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {cruzamientos.map((c, i) => (
        <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono text-amber-500">Iter {c.iteration}</span>
            <span className="text-sm text-white">{c.from_agent}</span>
            <span className="text-slate-500">→</span>
            <span className="text-sm text-white">{c.to_agent}</span>
          </div>
          <div className="text-xs text-slate-400 mb-2">
            Objetivo: {c.target_argument?.slice(0, 100)}...
          </div>
          <div className="text-sm text-slate-300 whitespace-pre-wrap">
            {c.response?.slice(0, 500)}
            {c.response?.length > 500 && '...'}
          </div>
        </div>
      ))}
    </div>
  )
}

function TribunalTab({ session }) {
  const tribunal = session?.tribunal_verdict
  if (!tribunal) {
    return (
      <div className="text-center py-12 text-slate-500">
        <Scale className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>Tribunal no activo aun</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <TribunalPanel verdict={tribunal} />
      {tribunal.evidence_score != null && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-400">
              {(tribunal.evidence_score * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-slate-500 mt-1">Evidencia</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-red-400">
              {(tribunal.risk_score * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-slate-500 mt-1">Riesgo</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-amber-400">
              {(tribunal.alignment_score * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-slate-500 mt-1">Alineacion</div>
          </div>
        </div>
      )}
    </div>
  )
}

function ReductioTab({ session }) {
  return (
    <div className="text-center py-12 text-slate-500">
      <FlaskConical className="w-8 h-8 mx-auto mb-2 opacity-50" />
      <p>Reductio ad Absurdum - Proximamente</p>
    </div>
  )
}

function ReportTab({ session }) {
  const [generating, setGenerating] = useState(false)

  const handleExport = async (format) => {
    setGenerating(true)
    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/sessions/${session?.id}/export/${format}`,
        { method: 'POST' }
      )
      if (res.ok) {
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `debate_${session?.id}.${format}`
        a.click()
        URL.revokeObjectURL(url)
      }
    } catch (e) {
      console.error('Export failed:', e)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Exportar Informe</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => handleExport('pdf')}
            disabled={generating}
            className="px-4 py-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/20 disabled:opacity-50 transition-colors"
          >
            PDF
          </button>
          <button
            onClick={() => handleExport('docx')}
            disabled={generating}
            className="px-4 py-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg text-sm hover:bg-blue-500/20 disabled:opacity-50 transition-colors"
          >
            Word
          </button>
          <button
            onClick={() => handleExport('md')}
            disabled={generating}
            className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/20 disabled:opacity-50 transition-colors"
          >
            Markdown
          </button>
        </div>
      </div>

      {session?.structured_report && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Resumen Estructurado</h3>
          <pre className="text-xs text-slate-400 whitespace-pre-wrap overflow-auto max-h-96">
            {JSON.stringify(session.structured_report, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
