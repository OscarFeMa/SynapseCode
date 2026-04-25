import { Scale, Shield, Target, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { useWebSocketStore } from '../../store/useStore'

const magistrates = [
  {
    id: 'magistrate_evidence',
    name: 'Magistrado de Evidencias',
    role: 'Auditor Técnico',
    icon: Scale,
    color: 'blue',
    description: 'Valida rigor técnico y evidencia empírica',
  },
  {
    id: 'magistrate_risk',
    name: 'Magistrado de Riesgos',
    role: 'Abogado del Diablo',
    icon: Shield,
    color: 'red',
    description: 'Identifica vulnerabilidades y riesgos ocultos',
  },
  {
    id: 'magistrate_alignment',
    name: 'Magistrado de Alineación',
    role: 'Product Owner',
    icon: Target,
    color: 'amber',
    description: 'Garantiza solución pragmática al problema',
  },
]

const colorClasses = {
  blue: {
    border: 'border-blue-500/50',
    bg: 'bg-blue-500/10',
    text: 'text-blue-400',
    icon: 'text-blue-400',
  },
  red: {
    border: 'border-red-500/50',
    bg: 'bg-red-500/10',
    text: 'text-red-400',
    icon: 'text-red-400',
  },
  amber: {
    border: 'border-amber-500/50',
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    icon: 'text-amber-400',
  },
}

export function TribunalPanel({ sessionId, verdict, isActive }) {
  const events = useWebSocketStore((state) => state.events)
  const agentTokens = useWebSocketStore((state) => state.agentTokens)
  const tribunalScores = useWebSocketStore((state) => state.tribunalScores)
  
  // Get latest tribunal events
  const tribunalEvents = events.filter(e => 
    e.type.startsWith('tribunal_') || 
    (e.type === 'phase_started' && e.payload.phase === 'TRIBUNAL')
  )
  
  const latestVerdictEvent = events
    .filter(e => e.type === 'tribunal_verdict')
    .pop()
  
  const latestObjections = events
    .filter(e => e.type === 'tribunal_objection')
    .slice(-3)
  
  // Get magistrate status
  const getMagistrateStatus = (id) => {
    const hasText = !!agentTokens[id]
    const completed = events.some(e => 
      e.type === 'agent_completed' && e.payload.agent === id
    )
    
    if (completed) return 'completed'
    if (hasText) return 'active'
    return 'pending'
  }
  
  // Score from verdict or realtime scores
  const scores = tribunalScores || (verdict ? {
    evidence: verdict.evidence_score,
    risk: verdict.risk_score,
    alignment: verdict.alignment_score,
    consensus: verdict.consensus_reached,
  } : null)
  
  return (
    <div className="p-4 bg-slate-900 rounded-lg border border-amber-500/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-amber-400 flex items-center gap-2">
          <Scale size={16} />
          Tribunal de Magistrados
        </h3>
        {isActive && (
          <span className="text-xs text-amber-400 animate-pulse">
            ● En sesión
          </span>
        )}
      </div>
      
      {/* Magistrates */}
      <div className="space-y-3">
        {magistrates.map((magistrate) => {
          const colors = colorClasses[magistrate.color]
          const status = getMagistrateStatus(magistrate.id)
          const text = agentTokens[magistrate.id] || ''
          
          return (
            <div 
              key={magistrate.id}
              className={`p-3 rounded-lg border ${colors.border} ${colors.bg} transition-all`}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg bg-slate-800 ${colors.icon}`}>
                  <magistrate.icon size={16} />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className={`font-medium text-sm ${colors.text}`}>
                      {magistrate.name}
                    </h4>
                    <StatusIcon status={status} />
                  </div>
                  
                  <p className="text-xs text-slate-500 mt-0.5">
                    {magistrate.role}
                  </p>
                  
                  {/* Score if available */}
                  {scores && magistrate.id === 'magistrate_evidence' && scores.evidence > 0 && (
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            scores.evidence >= 70 ? 'bg-green-500' :
                            scores.evidence >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${scores.evidence}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400">{scores.evidence}/100</span>
                    </div>
                  )}
                  
                  {scores && magistrate.id === 'magistrate_risk' && scores.risk > 0 && (
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            scores.risk >= 70 ? 'bg-green-500' :
                            scores.risk >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${scores.risk}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400">{scores.risk}/100</span>
                    </div>
                  )}
                  
                  {/* Preview text */}
                  {text && (
                    <div className="mt-2 p-2 bg-slate-900/50 rounded text-xs text-slate-400 font-mono line-clamp-3">
                      {text.slice(0, 200)}...
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      
      {/* Objections */}
      {latestObjections.length > 0 && (
        <div className="mt-4">
          <h4 className="text-xs font-medium text-slate-500 mb-2">Objeciones Recientes</h4>
          <div className="space-y-2">
            {latestObjections.map((obj, i) => (
              <div 
                key={i}
                className={`p-2 rounded text-xs ${
                  obj.payload.blocking 
                    ? 'bg-red-500/10 border border-red-500/30 text-red-400' 
                    : 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-400'
                }`}
              >
                <div className="flex items-center gap-1">
                  {obj.payload.blocking ? <XCircle size={12} /> : <AlertTriangle size={12} />}
                  <span className="font-medium">
                    {obj.payload.role === 'evidence' ? 'Evidencias' : 'Riesgos'}
                  </span>
                  {obj.payload.score && (
                    <span className="text-slate-500">(score: {obj.payload.score})</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Consensus result */}
      {scores && (
        <div className="mt-4 pt-4 border-t border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-400">Consenso del Tribunal</span>
            <span className={`flex items-center gap-1 text-sm font-medium ${
              scores.consensus ? 'text-green-400' : 'text-yellow-400'
            }`}>
              {scores.consensus ? (
                <><CheckCircle size={16} /> Alcanzado</>
              ) : (
                <><AlertTriangle size={16} /> No alcanzado</>
              )}
            </span>
          </div>
          
          {latestVerdictEvent && (
            <div className="mt-2 text-xs text-slate-500">
              Iteraciones PCO: {latestVerdictEvent.payload.iterations}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatusIcon({ status }) {
  if (status === 'completed') {
    return <CheckCircle size={16} className="text-green-400" />
  }
  if (status === 'active') {
    return <span className="w-4 h-4 rounded-full border-2 border-amber-500 border-t-transparent animate-spin" />
  }
  return <span className="w-2 h-2 rounded-full bg-slate-600" />
}
