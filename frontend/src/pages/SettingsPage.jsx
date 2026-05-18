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
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl text-[#161616]">Ajustes</h1>
        <p className="text-sm text-[#5C5C5C] mt-1">Configuracion del sistema</p>
        <div className="w-8 h-0.5 bg-[#23403B] mt-3" />
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[rgba(0,0,0,0.08)]">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 transition-colors ${
              tab === t.id
                ? 'border-[#23403B] text-[#23403B] font-medium'
                : 'border-transparent text-[#5C5C5C] hover:text-[#161616]'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* API Keys */}
      {tab === 'api' && (
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-6 shadow-card space-y-4">
          {saved && (
            <div className="p-3 bg-[#4A7C59]/[0.06] border border-[#4A7C59]/15 rounded text-sm text-[#4A7C59]">
              Keys guardadas correctamente
            </div>
          )}
          {Object.entries(keys).map(([service, value]) => (
            <div key={service}>
              <label className="text-sm text-[#5C5C5C] capitalize mb-1 block">{service} API Key</label>
              <div className="relative">
                <input
                  type={showKeys[service] ? 'text' : 'password'}
                  value={value}
                  onChange={(e) => setKeys((k) => ({ ...k, [service]: e.target.value }))}
                  placeholder={`sk-...`}
                  className="w-full px-4 py-2 pr-10 bg-[#F5F3EE] border border-[rgba(0,0,0,0.08)] rounded text-[#161616] placeholder-[#8A8780] focus:outline-none focus:border-[rgba(0,0,0,0.16)]"
                />
                <button
                  onClick={() => toggleShow(service)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8A8780] hover:text-[#161616]"
                >
                  {showKeys[service] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          ))}
          <button
            onClick={handleSaveKeys}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 btn-primary disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Guardando...' : 'Guardar Keys'}
          </button>
        </div>
      )}

      {/* System */}
      {tab === 'system' && (
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-6 shadow-card space-y-4">
          <div className="text-sm text-[#5C5C5C]">
            <p>Configuracion del sistema en desarrollo.</p>
            <p className="mt-2">Endpoints disponibles:</p>
            <ul className="list-disc list-inside mt-1 space-y-1 text-[#8A8780]">
              <li><code className="text-[#23403B] font-mono text-xs">GET /api/system/config</code></li>
              <li><code className="text-[#23403B] font-mono text-xs">GET /api/system/health</code></li>
              <li><code className="text-[#23403B] font-mono text-xs">GET /api/system/metrics/daily</code></li>
            </ul>
          </div>
        </div>
      )}

      {/* Security */}
      {tab === 'security' && (
        <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-6 shadow-card space-y-4">
          <div className="text-sm text-[#5C5C5C]">
            <p>Configuracion de seguridad en desarrollo.</p>
            <p className="mt-2">Items pendientes:</p>
            <ul className="list-disc list-inside mt-1 space-y-1 text-[#8A8780]">
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
