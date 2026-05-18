import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, ChevronLeft, Zap, Users, Settings, Check } from 'lucide-react'
import { toast } from 'sonner'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const debateTypes = [
  { id: 'sequential', label: 'Secuencial', desc: 'Analisis → Critica → Sintesis → Refinamiento', icon: '🔄' },
  { id: 'iterative', label: 'Iterativo', desc: 'Multiple rondas con mejora progresiva', icon: '🔁' },
  { id: 'consensus', label: 'Consenso', desc: 'Busqueda de acuerdo entre agentes', icon: '🤝' },
  { id: 'ultra', label: 'Ultra Crossing', desc: 'Cruzamientos criticos intensivos', icon: '⚡' },
]

const roles = [
  { id: 'analyst', label: 'Analista', color: 'text-blue-400' },
  { id: 'critic', label: 'Critico', color: 'text-yellow-400' },
  { id: 'synthesizer', label: 'Sintetizador', color: 'text-purple-400' },
  { id: 'refiner', label: 'Refinador', color: 'text-emerald-400' },
  { id: 'moderator', label: 'Moderador', color: 'text-amber-400' },
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Nuevo Debate</h1>
        <p className="text-sm text-slate-400 mt-1">Configura y lanza un nuevo debate multi-agente</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {steps.map((s, i) => (
          <div key={s.num} className="flex items-center gap-2">
            <div
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                step === s.num
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                  : step > s.num
                  ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                  : 'bg-slate-900 text-slate-500 border border-slate-800'
              }`}
            >
              <s.icon className="w-4 h-4" />
              <span className="hidden sm:inline">{s.label}</span>
            </div>
            {i < steps.length - 1 && <div className="w-8 h-px bg-slate-800" />}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        {/* Step 1: Topic */}
        {step === 1 && (
          <div className="space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-white">Tema del debate</span>
              <textarea
                value={form.topic}
                onChange={(e) => update('topic', e.target.value)}
                placeholder="Introduce la premisa o tema a debatir..."
                rows={4}
                className="mt-2 w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 resize-none"
              />
            </label>
            <div className="flex items-center gap-4">
              <label className="flex-1">
                <span className="text-sm text-slate-400">Rondas</span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={form.rounds}
                  onChange={(e) => update('rounds', parseInt(e.target.value))}
                  className="mt-1 w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                />
              </label>
              <label className="flex-1">
                <span className="text-sm text-slate-400">Umbral consenso: {form.consensusThreshold}%</span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={form.consensusThreshold}
                  onChange={(e) => update('consensusThreshold', parseInt(e.target.value))}
                  className="mt-2 w-full accent-amber-500"
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
                className={`p-4 rounded-xl border text-left transition-all ${
                  form.type === t.id
                    ? 'border-amber-500 bg-amber-500/5'
                    : 'border-slate-700 bg-slate-800 hover:border-slate-600'
                }`}
              >
                <div className="text-2xl mb-2">{t.icon}</div>
                <div className="text-white font-medium">{t.label}</div>
                <div className="text-xs text-slate-400 mt-1">{t.desc}</div>
              </button>
            ))}
          </div>
        )}

        {/* Step 3: Options */}
        {step === 3 && (
          <div className="space-y-4">
            {[
              { key: 'smartRotation', label: 'Smart Rotation', desc: 'Rotacion automatica de modelos por rol' },
              { key: 'webSearch', label: 'Busqueda Web', desc: 'Contexto adicional en tiempo real' },
              { key: 'tribunal', label: 'Tribunal', desc: 'Panel de magistrados para veredicto final' },
              { key: 'reductio', label: 'Reductio ad Absurdum', desc: 'Desafios logicos a puntos de consenso' },
            ].map((opt) => (
              <div
                key={opt.key}
                className="flex items-center justify-between p-4 bg-slate-800 rounded-lg"
              >
                <div>
                  <div className="text-white text-sm font-medium">{opt.label}</div>
                  <div className="text-xs text-slate-400">{opt.desc}</div>
                </div>
                <button
                  onClick={() => update(opt.key, !form[opt.key])}
                  className={`w-12 h-6 rounded-full transition-colors relative ${
                    form[opt.key] ? 'bg-amber-500' : 'bg-slate-700'
                  }`}
                >
                  <div
                    className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition-all ${
                      form[opt.key] ? 'left-6' : 'left-0.5'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Step 4: Confirm */}
        {step === 4 && (
          <div className="space-y-4">
            <div className="bg-slate-800 rounded-lg p-4 font-mono text-sm space-y-1">
              <div className="text-slate-500">// Configuracion del debate</div>
              <div>
                <span className="text-amber-500">tipo:</span> <span className="text-white">"{form.type}"</span>
              </div>
              <div>
                <span className="text-amber-500">tema:</span> <span className="text-white">"{form.topic || '(vacio)'}"</span>
              </div>
              <div>
                <span className="text-amber-500">rondas:</span> <span className="text-emerald-400">{form.rounds}</span>
              </div>
              <div>
                <span className="text-amber-500">consenso:</span> <span className="text-emerald-400">{form.consensusThreshold}%</span>
              </div>
              <div>
                <span className="text-amber-500">smart_rotation:</span>{' '}
                <span className={form.smartRotation ? 'text-emerald-400' : 'text-red-400'}>
                  {form.smartRotation ? 'true' : 'false'}
                </span>
              </div>
              <div>
                <span className="text-amber-500">web_search:</span>{' '}
                <span className={form.webSearch ? 'text-emerald-400' : 'text-red-400'}>
                  {form.webSearch ? 'true' : 'false'}
                </span>
              </div>
              <div>
                <span className="text-amber-500">tribunal:</span>{' '}
                <span className={form.tribunal ? 'text-emerald-400' : 'text-red-400'}>
                  {form.tribunal ? 'true' : 'false'}
                </span>
              </div>
              <div>
                <span className="text-amber-500">reductio:</span>{' '}
                <span className={form.reductio ? 'text-emerald-400' : 'text-red-400'}>
                  {form.reductio ? 'true' : 'false'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-800">
          <button
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
            className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Atras
          </button>
          {step < 4 ? (
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={step === 1 && !form.topic.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-900 text-sm font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Siguiente
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={loading || !form.topic.trim()}
              className="flex items-center gap-2 px-6 py-2 bg-amber-500 hover:bg-amber-600 text-slate-900 text-sm font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
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
