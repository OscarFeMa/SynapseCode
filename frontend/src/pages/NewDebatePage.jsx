import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, ChevronLeft, Zap, Users, Settings, Check } from 'lucide-react'
import { toast } from 'sonner'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const debateTypes = [
  { id: 'sequential', label: 'Secuencial', desc: 'Analisis → Critica → Sintesis → Refinamiento' },
  { id: 'iterative', label: 'Iterativo', desc: 'Multiple rondas con mejora progresiva' },
  { id: 'consensus', label: 'Consenso', desc: 'Busqueda de acuerdo entre agentes' },
  { id: 'ultra', label: 'Ultra Crossing', desc: 'Cruzamientos criticos intensivos' },
]

export function NewDebatePage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    topic: '',
    type: 'sequential',
    rounds: 3,
    consensusThreshold: 70,
    smartRotation: true,
    webSearch: false,
    tribunal: true,
    reductio: false,
  })

  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: form.topic,
          type: form.type,
          rounds: form.rounds,
          consensus_threshold: form.consensusThreshold,
          smart_rotation: form.smartRotation,
          web_search: form.webSearch,
          tribunal: form.tribunal,
          reductio: form.reductio,
        }),
      })
      if (!res.ok) throw new Error('Failed to create session')
      const data = await res.json()
      toast.success('Debate creado exitosamente')
      navigate(`/debates/${data.id}`)
    } catch (e) {
      toast.error('Error al crear el debate')
    } finally {
      setLoading(false)
    }
  }

  const steps = [
    { num: 1, label: 'Tema', icon: Zap },
    { num: 2, label: 'Tipo', icon: Users },
    { num: 3, label: 'Opciones', icon: Settings },
    { num: 4, label: 'Confirmar', icon: Check },
  ]

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl text-[#161616]">Nuevo Debate</h1>
        <p className="text-sm text-[#5C5C5C] mt-1">Configura y lanza un nuevo debate multi-agente</p>
        <div className="w-8 h-0.5 bg-[#23403B] mt-3" />
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {steps.map((s, i) => (
          <div key={s.num} className="flex items-center gap-2">
            <div
              className={`flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors ${
                step === s.num
                  ? 'bg-[#23403B]/[0.06] text-[#23403B] border border-[#23403B]/15'
                  : step > s.num
                  ? 'bg-[#4A7C59]/[0.06] text-[#4A7C59] border border-[#4A7C59]/15'
                  : 'bg-white text-[#8A8780] border border-[rgba(0,0,0,0.06)]'
              }`}
            >
              <s.icon className="w-4 h-4" />
              <span className="hidden sm:inline">{s.label}</span>
            </div>
            {i < steps.length - 1 && <div className="w-8 h-px bg-[#B8B5AE]" />}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-6 shadow-card">
        {/* Step 1: Topic */}
        {step === 1 && (
          <div className="space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-[#161616]">Tema del debate</span>
              <textarea
                value={form.topic}
                onChange={(e) => update('topic', e.target.value)}
                placeholder="Introduce la premisa o tema a debatir..."
                rows={4}
                className="mt-2 w-full px-4 py-3 bg-[#F5F3EE] border border-[rgba(0,0,0,0.08)] rounded text-[#161616] placeholder-[#8A8780] focus:outline-none focus:border-[rgba(0,0,0,0.16)] resize-none"
              />
            </label>
            <div className="flex items-center gap-4">
              <label className="flex-1">
                <span className="text-sm text-[#5C5C5C]">Rondas</span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={form.rounds}
                  onChange={(e) => update('rounds', parseInt(e.target.value))}
                  className="mt-1 w-full px-3 py-2 bg-[#F5F3EE] border border-[rgba(0,0,0,0.08)] rounded text-[#161616] focus:outline-none focus:border-[rgba(0,0,0,0.16)]"
                />
              </label>
              <label className="flex-1">
                <span className="text-sm text-[#5C5C5C]">Umbral consenso: {form.consensusThreshold}%</span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={form.consensusThreshold}
                  onChange={(e) => update('consensusThreshold', parseInt(e.target.value))}
                  className="mt-2 w-full accent-[#23403B]"
                />
              </label>
            </div>
          </div>
        )}

        {/* Step 2: Type */}
        {step === 2 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {debateTypes.map((t) => (
              <button
                key={t.id}
                onClick={() => update('type', t.id)}
                className={`p-4 rounded border text-left transition-all ${
                  form.type === t.id
                    ? 'border-[#23403B]/30 bg-[#23403B]/[0.04]'
                    : 'border-[rgba(0,0,0,0.08)] bg-white hover:border-[rgba(0,0,0,0.14)]'
                }`}
              >
                <div className="text-[#161616] font-medium">{t.label}</div>
                <div className="text-xs text-[#5C5C5C] mt-1">{t.desc}</div>
              </button>
            ))}
          </div>
        )}

        {/* Step 3: Options */}
        {step === 3 && (
          <div className="space-y-3">
            {[
              { key: 'smartRotation', label: 'Smart Rotation', desc: 'Rotacion automatica de modelos por rol' },
              { key: 'webSearch', label: 'Busqueda Web', desc: 'Contexto adicional en tiempo real' },
              { key: 'tribunal', label: 'Tribunal', desc: 'Panel de magistrados para veredicto final' },
              { key: 'reductio', label: 'Reductio ad Absurdum', desc: 'Desafios logicos a puntos de consenso' },
            ].map((opt) => (
              <div
                key={opt.key}
                className="flex items-center justify-between p-4 bg-[#F5F3EE] rounded"
              >
                <div>
                  <div className="text-[#161616] text-sm font-medium">{opt.label}</div>
                  <div className="text-xs text-[#5C5C5C]">{opt.desc}</div>
                </div>
                <button
                  onClick={() => update(opt.key, !form[opt.key])}
                  className={`w-11 h-6 rounded-full transition-colors relative ${
                    form[opt.key] ? 'bg-[#23403B]' : 'bg-[#B8B5AE]'
                  }`}
                >
                  <div
                    className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all shadow ${
                      form[opt.key] ? 'left-6' : 'left-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Step 4: Confirm */}
        {step === 4 && (
          <div className="space-y-3">
            <div className="bg-[#F5F3EE] rounded p-4 font-mono text-sm space-y-1">
              <div className="text-[#8A8780]">// Configuracion del debate</div>
              <div>
                <span className="text-[#23403B]">tipo:</span> <span className="text-[#161616]">"{form.type}"</span>
              </div>
              <div>
                <span className="text-[#23403B]">tema:</span> <span className="text-[#161616]">"{form.topic || '(vacio)'}"</span>
              </div>
              <div>
                <span className="text-[#23403B]">rondas:</span> <span className="text-[#4A7C59]">{form.rounds}</span>
              </div>
              <div>
                <span className="text-[#23403B]">consenso:</span> <span className="text-[#4A7C59]">{form.consensusThreshold}%</span>
              </div>
              <div>
                <span className="text-[#23403B]">smart_rotation:</span>{' '}
                <span className={form.smartRotation ? 'text-[#4A7C59]' : 'text-[#8B3A3A]'}>
                  {form.smartRotation ? 'true' : 'false'}
                </span>
              </div>
              <div>
                <span className="text-[#23403B]">web_search:</span>{' '}
                <span className={form.webSearch ? 'text-[#4A7C59]' : 'text-[#8B3A3A]'}>
                  {form.webSearch ? 'true' : 'false'}
                </span>
              </div>
              <div>
                <span className="text-[#23403B]">tribunal:</span>{' '}
                <span className={form.tribunal ? 'text-[#4A7C59]' : 'text-[#8B3A3A]'}>
                  {form.tribunal ? 'true' : 'false'}
                </span>
              </div>
              <div>
                <span className="text-[#23403B]">reductio:</span>{' '}
                <span className={form.reductio ? 'text-[#4A7C59]' : 'text-[#8B3A3A]'}>
                  {form.reductio ? 'true' : 'false'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-[rgba(0,0,0,0.06)]">
          <button
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
            className="flex items-center gap-2 px-4 py-2 text-sm text-[#5C5C5C] hover:text-[#161616] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Atras
          </button>
          {step < 4 ? (
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={step === 1 && !form.topic.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-[#23403B] hover:bg-[#2D524C] text-[#F5F3EE] text-sm font-medium rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Siguiente
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={loading || !form.topic.trim()}
              className="flex items-center gap-2 px-6 py-2 bg-[#23403B] hover:bg-[#2D524C] text-[#F5F3EE] text-sm font-medium rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-[#F5F3EE] border-t-transparent rounded-full animate-spin" />
                  Creando...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Lanzar Debate
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
