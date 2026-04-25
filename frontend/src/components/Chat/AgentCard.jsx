import { useState } from 'react'
import { Bot, Brain, Cloud, Shield, Scale, Sparkles, ChevronDown, ChevronUp } from 'lucide-react'
import { useWebSocketStore } from '../../store/useStore'

const agentIcons = {
  analyst_local_a: Bot,
  analyst_local_b: Brain,
  analyst_cloud_a: Cloud,
  analyst_cloud_b: Sparkles,
  critic_local_a: Shield,
  critic_local_b: Shield,
  critic_cloud_a: Shield,
  critic_cloud_b: Shield,
  synth_local: Brain,
  synth_cloud: Cloud,
  magistrate_evidence: Scale,
  magistrate_risk: Shield,
  magistrate_alignment: Scale,
}

const agentNames = {
  analyst_local_a: 'Analista Técnico (Local)',
  analyst_local_b: 'Analista Estratégico (Local)',
  analyst_cloud_a: 'Analista Empírico (Nube)',
  analyst_cloud_b: 'Analista Organizacional (Nube)',
  critic_local_a: 'Crítico Técnico (Local)',
  critic_local_b: 'Crítico Estratégico (Local)',
  critic_cloud_a: 'Crítico Empírico (Nube)',
  critic_cloud_b: 'Crítico Organizacional (Nube)',
  synth_local: 'Sintetizador Local',
  synth_cloud: 'Sintetizador Nube',
  magistrate_evidence: 'Magistrado de Evidencias',
  magistrate_risk: 'Magistrado de Riesgos',
  magistrate_alignment: 'Magistrado de Alineación',
}

const phaseColors = {
  ANALYSIS: 'border-blue-500/50 bg-blue-500/10',
  CRITIQUE: 'border-yellow-500/50 bg-yellow-500/10',
  SYNTHESIS: 'border-purple-500/50 bg-purple-500/10',
  TRIBUNAL: 'border-amber-500/50 bg-amber-500/10',
}

export function AgentCard({ agentId, phase, status, model, tokens }) {
  const [expanded, setExpanded] = useState(false)
  const agentText = useWebSocketStore((state) => state.agentTokens[agentId] || '')
  
  const Icon = agentIcons[agentId] || Bot
  const name = agentNames[agentId] || agentId
  const phaseStyle = phaseColors[phase] || 'border-slate-700 bg-slate-800'
  
  const isActive = status === 'STREAMING' || status === 'RUNNING'
  const isComplete = status === 'COMPLETED'
  const hasError = status === 'FAILED' || status === 'TIMEOUT'
  
  return (
    <div className={`rounded-lg border ${phaseStyle} overflow-hidden transition-all duration-300`}>
      {/* Header */}
      <div 
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className={`p-2 rounded-lg ${isActive ? 'bg-amber-500/20 animate-pulse' : 'bg-slate-700'}`}>
          <Icon size={18} className={isActive ? 'text-amber-400' : 'text-slate-400'} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-sm text-slate-200 truncate">{name}</h4>
            {isComplete && <span className="text-xs text-green-400">✓</span>}
            {hasError && <span className="text-xs text-red-400">✗</span>}
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span>{model || 'unknown'}</span>
            {tokens > 0 && <span>• {tokens} tokens</span>}
          </div>
        </div>
        
        <button className="p-1 hover:bg-white/10 rounded transition-colors">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>
      
      {/* Content (when expanded or streaming) */}
      {(expanded || agentText) && (
        <div className="px-3 pb-3">
          <div className="p-3 bg-slate-900/50 rounded text-sm text-slate-300 font-mono whitespace-pre-wrap max-h-64 overflow-y-auto">
            {agentText || (
              <span className="text-slate-500 italic">
                {isActive ? 'Generando respuesta...' : 'Esperando inicio...'}
              </span>
            )}
            {isActive && <span className="animate-pulse">▋</span>}
          </div>
        </div>
      )}
    </div>
  )
}

export function AgentGrid({ agents, phase }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {agents.map((agent) => (
        <AgentCard
          key={agent.id}
          agentId={agent.id}
          phase={phase}
          status={agent.status}
          model={agent.model}
          tokens={agent.tokens}
        />
      ))}
    </div>
  )
}
