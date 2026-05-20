import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export function SharePage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [debate, setDebate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function loadDebate() {
      try {
        const { data, error } = await supabase
          .from('debates')
          .select('*')
          .eq('session_id', sessionId)
          .single()

        if (error) throw error
        
        if (!data) {
          throw new Error("El debate no existe o es privado.")
        }
        
        // Asume que la tabla debates tiene una columna 'data' o 'history' con el array JSON de los turnos
        setDebate(data)
      } catch (err) {
        console.error("Error cargando debate:", err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    loadDebate()
  }, [sessionId])

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F5F3EE] font-sans">
        <div className="animate-pulse flex flex-col items-center">
          <div className="w-12 h-12 bg-[#23403B] rounded mb-4"></div>
          <p className="text-[#23403B] font-serif text-xl">Accediendo a los archivos del Tribunal...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F5F3EE] font-sans">
        <div className="bg-white p-8 rounded border border-red-200 shadow-sm max-w-md text-center">
          <h2 className="text-2xl font-serif text-[#23403B] mb-2">Registro no encontrado</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button onClick={() => navigate('/')} className="bg-[#23403B] text-white px-4 py-2 rounded">
            Volver a la portada
          </button>
        </div>
      </div>
    )
  }

  // Parse turns from debate record
  // Depends on backend schema, assuming it stores turns in `transcript` or `turns`
  const turns = debate.transcript || debate.turns || []

  return (
    <div className="min-h-screen bg-[#F5F3EE] font-sans">
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="font-serif text-2xl text-[#23403B]">SynapseCode Public Record</h1>
            <p className="text-xs text-gray-500 font-mono">ID: {sessionId} • {new Date(debate.created_at).toLocaleString()}</p>
          </div>
          <div className="bg-[#E8F2EF] text-[#23403B] px-3 py-1 rounded text-sm font-medium border border-[#BCE1D6]">
            Documento Público
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-10 text-center">
          <h2 className="font-serif text-4xl text-[#23403B] mb-4">{debate.topic || "Debate"}</h2>
        </div>

        <div className="space-y-6">
          {turns.length === 0 ? (
            <p className="text-center text-gray-500 italic">No hay intervenciones registradas en este debate.</p>
          ) : (
            turns.map((turn, i) => (
              <div key={i} className="bg-white p-6 rounded border border-gray-200 shadow-sm transition-all hover:shadow-md">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full bg-[#23403B] text-white flex items-center justify-center font-bold">
                    {turn.agent?.role?.[0]?.toUpperCase() || 'A'}
                  </div>
                  <div>
                    <h4 className="font-bold text-[#161616]">{turn.agent?.name || 'Agent'}</h4>
                    <span className="text-xs text-gray-500">{turn.agent?.model || 'Model'}</span>
                  </div>
                </div>
                <div className="prose prose-sm max-w-none text-[#1a1a1a] whitespace-pre-wrap">
                  {turn.response_received || turn.content}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      
      <div className="text-center py-8 text-gray-400 text-sm">
        Generado autónomamente por SynapseCode v3.0
      </div>
    </div>
  )
}
