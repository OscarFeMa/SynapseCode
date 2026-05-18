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
    const badgeMap = {
      CREATED: 'badge-neutral',
      RUNNING: 'badge-neutral',
      COMPLETED: 'badge-success',
      FAILED: 'badge-error',
    }
    return (
      <span className={`text-xs px-2.5 py-1 rounded font-medium ${badgeMap[status] || 'badge-neutral'}`}>
        {status}
      </span>
    )
  }

  const getConsensusBadge = () => {
    const level = session?.consensus_level || 'UNKNOWN'
    const badgeMap = {
      CONSENSUS_REACHED: 'badge-success',
      PARTIAL_CONSENSUS: 'badge-warning',
      DIVERGENT: 'badge-error',
      UNKNOWN: 'badge-neutral',
    }
    return (
      <span className={`text-xs px-2.5 py-1 rounded font-medium ${badgeMap[level] || 'badge-neutral'}`}>
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
        <Loader2 className="w-8 h-8 text-[#23403B] animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-[#8B3A3A] mb-4">Error al cargar la sesion</p>
        <button
          onClick={refresh}
          className="px-4 py-2 bg-white border border-[rgba(0,0,0,0.08)] rounded text-sm text-[#161616] hover:bg-[#F5F3EE]"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/debates')}
            className="p-2 text-[#5C5C5C] hover:text-[#161616] transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl text-[#161616] font-serif">
              {session?.topic || 'Debate'}
            </h1>
            <p className="text-xs text-[#8A8780] font-mono">{sessionId}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {getStatusBadge()}
          {getConsensusBadge()}
          <button
            onClick={refresh}
            className="p-2 text-[#5C5C5C] hover:text-[#161616] transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {session?.status === 'RUNNING' && (
        <div className="w-full bg-[#ECE9E2] rounded h-1">
          <div
            className="bg-[#23403B] h-1 rounded transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Stats bar */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-[#5C5C5C]">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" /> Round {currentRound}
        </span>
        <span className="flex items-center gap-1">
          <Hash className="w-3 h-3" /> {totalTokensIn.toLocaleString()} tokens IN
        </span>
        <span className="flex items-center gap-1">
          <DollarSign className="w-3 h-3" /> {totalTokensOut.toLocaleString()} tokens OUT
        </span>
        {session?.web_search && (
          <span className="flex items-center gap-1 text-[#23403B]">
            <Globe className="w-3 h-3" /> Web search
          </span>
        )}
        <span
          className={`flex items-center gap-1 ${
            isConnected ? 'text-[#4A7C59]' : 'text-[#8B3A3A]'
          }`}
        >
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-[#4A7C59]' : 'bg-[#8B3A3A]'
            }`}
          />
          {isConnected ? 'Live' : 'Disconnected'}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[rgba(0,0,0,0.08)] overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-[#23403B] text-[#23403B] font-medium'
                : 'border-transparent text-[#5C5C5C] hover:text-[#161616]'
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
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg">
          <button
            onClick={() => setShowWebResults(!showWebResults)}
            className="flex items-center justify-between w-full p-4 text-left"
          >
            <span className="text-sm font-medium text-[#161616] flex items-center gap-2">
              <Globe className="w-4 h-4 text-[#23403B]" />
              Resultados Web
            </span>
            {showWebResults ? (
              <ChevronUp className="w-4 h-4 text-[#8A8780]" />
            ) : (
              <ChevronDown className="w-4 h-4 text-[#8A8780]" />
            )}
          </button>
          {showWebResults && (
            <div className="px-4 pb-4 text-sm text-[#5C5C5C]">
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
            <h3 className="text-sm font-semibold text-[#161616] flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  isCurrentPhase
                    ? 'bg-[#6E8B74] animate-pulse'
                    : hasCompleted
                    ? 'bg-[#4A7C59]'
                    : 'bg-[#B8B5AE]'
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
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <h3 className="text-sm font-semibold text-[#161616] mb-3">Veredicto Final</h3>
          <p className="text-sm text-[#5C5C5C] whitespace-pre-wrap">
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
      <div className="text-center py-12 text-[#8A8780]">
        <Hash className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p>No hay turnos registrados</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {turns.map((turn) => (
        <details
          key={turn.turn_number}
          className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg group"
        >
          <summary className="flex items-center justify-between p-4 cursor-pointer list-none">
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-[#23403B]">#{turn.turn_number}</span>
              <span className="text-sm text-[#161616]">{turn.agent?.name || turn.agent_name || 'Agent'}</span>
              <span className="text-xs text-[#8A8780]">{turn.agent?.role || turn.agent_role || ''}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-[#5C5C5C]">
                {turn.tokens_in || 0} → {turn.tokens_out || 0}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded ${
                  turn.status === 'completed'
                    ? 'badge-success'
                    : turn.status === 'failed'
                    ? 'badge-error'
                    : 'badge-neutral'
                }`}
              >
                {turn.status}
              </span>
            </div>
          </summary>
          <div className="px-4 pb-4 text-sm text-[#5C5C5C] whitespace-pre-wrap border-t border-[rgba(0,0,0,0.06)] pt-3">
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
      <div className="text-center py-12 text-[#8A8780]">
        <GitBranch className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p>No hay cruzamientos registrados</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {cruzamientos.map((c, i) => (
        <div key={i} className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono text-[#23403B]">Iter {c.iteration}</span>
            <span className="text-sm text-[#161616]">{c.from_agent}</span>
            <span className="text-[#8A8780]">→</span>
            <span className="text-sm text-[#161616]">{c.to_agent}</span>
          </div>
          <div className="text-xs text-[#5C5C5C] mb-2">
            Objetivo: {c.target_argument?.slice(0, 100)}...
          </div>
          <div className="text-sm text-[#5C5C5C] whitespace-pre-wrap">
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
      <div className="text-center py-12 text-[#8A8780]">
        <Scale className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p>Tribunal no activo aun</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <TribunalPanel verdict={tribunal} />
      {tribunal.evidence_score != null && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-4 text-center shadow-card">
            <div className="text-2xl font-serif text-[#23403B]">
              {(tribunal.evidence_score * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-[#8A8780] mt-1">Evidencia</div>
          </div>
          <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-4 text-center shadow-card">
            <div className="text-2xl font-serif text-[#8B3A3A]">
              {(tribunal.risk_score * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-[#8A8780] mt-1">Riesgo</div>
          </div>
          <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-4 text-center shadow-card">
            <div className="text-2xl font-serif text-[#B98B4D]">
              {(tribunal.alignment_score * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-[#8A8780] mt-1">Alineacion</div>
          </div>
        </div>
      )}
    </div>
  )
}

function ReductioTab({ session }) {
  return (
    <div className="text-center py-12 text-[#8A8780]">
      <FlaskConical className="w-8 h-8 mx-auto mb-2 opacity-40" />
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
      <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
        <h3 className="text-sm font-semibold text-[#161616] mb-4">Exportar Informe</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => handleExport('pdf')}
            disabled={generating}
            className="btn-secondary px-4 py-2 text-sm disabled:opacity-50"
          >
            PDF
          </button>
          <button
            onClick={() => handleExport('docx')}
            disabled={generating}
            className="btn-secondary px-4 py-2 text-sm disabled:opacity-50"
          >
            Word
          </button>
          <button
            onClick={() => handleExport('md')}
            disabled={generating}
            className="btn-secondary px-4 py-2 text-sm disabled:opacity-50"
          >
            Markdown
          </button>
        </div>
      </div>

      {session?.structured_report && (
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card">
          <h3 className="text-sm font-semibold text-[#161616] mb-4">Resumen Estructurado</h3>
          <pre className="text-xs text-[#5C5C5C] whitespace-pre-wrap overflow-auto max-h-96 font-mono">
            {JSON.stringify(session.structured_report, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
