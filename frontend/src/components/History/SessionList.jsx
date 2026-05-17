import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  ArrowRight, 
  Trash2, 
  Loader2,
  MessageSquare,
  Hash,
  Globe,
} from 'lucide-react'
import { useSessionList } from '../../hooks/useSession'
import { deleteSession } from '../../hooks/useSession'

const statusConfig = {
  CREATED: { icon: Clock, color: 'text-slate-400', bg: 'bg-slate-500/10' },
  RUNNING: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  COMPLETED: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10' },
  FAILED: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/10' },
  CONSENSUS_NOT_REACHED: { icon: AlertCircle, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
}

const consensusConfig = {
  CONSENSUS_REACHED: { label: 'Consenso', className: 'bg-green-500/20 text-green-400' },
  PARTIAL_CONSENSUS: { label: 'Parcial', className: 'bg-yellow-500/20 text-yellow-400' },
  DIVERGENT: { label: 'Divergente', className: 'bg-red-500/20 text-red-400' },
}

export function SessionList() {
  const navigate = useNavigate()
  const { sessions, isLoading, refresh } = useSessionList()
  
  useEffect(() => {
    refresh()
  }, [refresh])
  
  const handleDelete = async (sessionId, e) => {
    e.stopPropagation()
    if (!confirm('¿Eliminar esta sesión?')) return
    
    const success = await deleteSession(sessionId)
    if (success) {
      refresh()
    }
  }
  
  const formatDate = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString('es-ES', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  
  if (isLoading && sessions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-amber-500" size={24} />
      </div>
    )
  }
  
  return (
    <div className="w-full max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Historial de Sesiones</h2>
          <p className="text-slate-400">Consultas previas al Consejo</p>
        </div>
        
        <button 
          onClick={() => navigate('/')}
          className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-900 font-medium rounded-lg transition-colors"
        >
          Nueva Consulta
        </button>
      </div>
      
      {sessions.length === 0 ? (
        <div className="text-center py-12 bg-slate-900/50 rounded-lg border border-slate-800">
          <MessageSquare className="mx-auto mb-4 text-slate-600" size={48} />
          <p className="text-slate-500">No hay sesiones registradas</p>
          <button 
            onClick={() => navigate('/')}
            className="mt-4 text-amber-500 hover:text-amber-400"
          >
            Crear primera sesión →
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => {
            const status = statusConfig[session.status] || statusConfig.CREATED
            const StatusIcon = status.icon
            const consensus = consensusConfig[session.consensus_level]
            
            return (
              <div
                key={session.id}
                onClick={() => navigate(`/session/${session.id}`)}
                className="group p-4 bg-slate-900 hover:bg-slate-800 rounded-lg border border-slate-800 hover:border-slate-700 transition-all cursor-pointer"
              >
                <div className="flex items-start gap-4">
                  {/* Status icon */}
                  <div className={`p-2 rounded-lg ${status.bg} shrink-0`}>
                    <StatusIcon 
                      size={20} 
                      className={`${status.color} ${session.status === 'RUNNING' ? 'animate-spin' : ''}`} 
                    />
                  </div>
                  
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-medium text-white truncate">
                        {session.title || 'Sin título'}
                      </h3>
                      <div className="flex items-center gap-2 shrink-0">
                        {consensus && (
                          <span className={`px-2 py-0.5 rounded text-xs ${consensus.className}`}>
                            {consensus.label}
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <p className="text-sm text-slate-400 mt-1 line-clamp-1">
                      {session.query}
                    </p>
                    
                    <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <Hash size={12} />
                        {session.id.slice(0, 8)}...
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={12} />
                        {formatDate(session.created_at)}
                      </span>
                      {session.rounds_executed > 0 && (
                        <span>
                          {session.rounds_executed} ronda{session.rounds_executed > 1 ? 's' : ''}
                        </span>
                      )}
                      {session.web_context && (
                        <span className="flex items-center gap-1 text-cyan-400">
                          <Globe size={12} />
                          Web
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => handleDelete(session.id, e)}
                      className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Eliminar"
                    >
                      <Trash2 size={16} />
                    </button>
                    <ArrowRight size={18} className="text-slate-500" />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
      
      {/* Footer */}
      <div className="mt-6 text-center text-sm text-slate-500">
        Mostrando {sessions.length} sesión{sessions.length !== 1 ? 'es' : ''}
      </div>
    </div>
  )
}
