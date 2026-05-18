import { useState } from 'react'
import { Eye, EyeOff, Save, Key, Globe, Shield } from 'lucide-react'
import { toast } from 'sonner'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function SettingsPage() {
  const [tab, setTab] = useState('api')
  const [saving, setSaving] = useState(false)
  const [keys, setKeys] = useState({
    openrouter: '',
    groq: '',
    gemini: '',
    deepseek: '',
  })
  const [showKeys, setShowKeys] = useState({})
  const [saved, setSaved] = useState(false)

  const handleSaveKeys = async () => {
    setSaving(true)
    setSaved(false)
    try {
      for (const [service, key] of Object.entries(keys)) {
        if (key) {
          await fetch(`${API_BASE}/api/system/api-keys/${service}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key }),
          })
        }
      }
      toast.success('API keys guardadas correctamente')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      toast.error('Error al guardar las API keys')
    } finally {
      setSaving(false)
    }
  }

  const toggleShow = (key) => setShowKeys((s) => ({ ...s, [key]: !s[key] }))

  const tabs = [
    { id: 'api', label: 'API Keys', icon: Key },
    { id: 'system', label: 'Sistema', icon: Globe },
    { id: 'security', label: 'Seguridad', icon: Shield },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Ajustes</h1>
        <p className="text-sm text-slate-400 mt-1">Configuracion del sistema</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm border-b-2 transition-colors ${
              tab === t.id
                ? 'border-amber-500 text-amber-500'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* API Keys */}
      {tab === 'api' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          {saved && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-sm text-emerald-400">
              Keys guardadas correctamente
            </div>
          )}
          {Object.entries(keys).map(([service, value]) => (
            <div key={service}>
              <label className="text-sm text-slate-400 capitalize mb-1 block">{service} API Key</label>
              <div className="relative">
                <input
                  type={showKeys[service] ? 'text' : 'password'}
                  value={value}
                  onChange={(e) => setKeys((k) => ({ ...k, [service]: e.target.value }))}
                  placeholder={`sk-...`}
                  className="w-full px-4 py-2 pr-10 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
                <button
                  onClick={() => toggleShow(service)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                >
                  {showKeys[service] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          ))}
          <button
            onClick={handleSaveKeys}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-900 text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Guardando...' : 'Guardar Keys'}
          </button>
        </div>
      )}

      {/* System */}
      {tab === 'system' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="text-sm text-slate-500">
            <p>Configuracion del sistema en desarrollo.</p>
            <p className="mt-2">Endpoints disponibles:</p>
            <ul className="list-disc list-inside mt-1 space-y-1 text-slate-400">
              <li><code className="text-amber-500">GET /api/system/config</code></li>
              <li><code className="text-amber-500">GET /api/system/health</code></li>
              <li><code className="text-amber-500">GET /api/system/metrics/daily</code></li>
            </ul>
          </div>
        </div>
      )}

      {/* Security */}
      {tab === 'security' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="text-sm text-slate-500">
            <p>Configuracion de seguridad en desarrollo.</p>
            <p className="mt-2">Items pendientes:</p>
            <ul className="list-disc list-inside mt-1 space-y-1 text-slate-400">
              <li>Token de administracion</li>
              <li>Rate limiting</li>
              <li>CORS configuration</li>
              <li>SSL/TLS settings</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
