import { useState, useEffect } from 'react'
import { Save, Key, Server, Wifi, Shield, Check } from 'lucide-react'

export function Settings() {
  const [settings, setSettings] = useState({
    // API Keys
    openrouterKey: '',
    geminiKey: '',
    groqKey: '',
    deepseekKey: '',
    
    // Engine Configuration
    ollamaUrl: 'http://localhost:11434',
    lmStudioUrl: 'http://localhost:1234',
    janUrl: 'http://localhost:1337',
    
    // Worker Configuration
    workerHost: '',
    workerOllamaPort: 11434,
    workerLmStudioPort: 1234,
    workerJanPort: 1337,
    
    // Discovery
    discoveryPort: 54321,
    discoveryInterval: 5,
    
    // Features
    webAgentEnabled: true,
    supabaseEnabled: true,
    agentReputationEnabled: true
  })

  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/system/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
      }
    } catch (e) {
      console.error('Failed to fetch settings:', e)
    }
  }

  const handleSave = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/system/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })

      if (response.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      }
    } catch (e) {
      console.error('Failed to save settings:', e)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {/* Header */}
      <nav className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-white">Configuración</h1>
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-900 font-semibold rounded-lg transition-colors"
            >
              {saved ? (
                <>
                  <Check className="w-4 h-4" />
                  <span>Guardado</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  <span>Guardar</span>
                </>
              )}
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* API Keys */}
        <Section icon={Key} title="API Keys">
          <div className="space-y-4">
            <SettingField
              label="OpenRouter API Key"
              value={settings.openrouterKey}
              onChange={(v) => setSettings({ ...settings, openrouterKey: v })}
              type="password"
              placeholder="sk-or-..."
            />
            <SettingField
              label="Gemini API Key"
              value={settings.geminiKey}
              onChange={(v) => setSettings({ ...settings, geminiKey: v })}
              type="password"
              placeholder="AIzaSy..."
            />
            <SettingField
              label="Groq API Key"
              value={settings.groqKey}
              onChange={(v) => setSettings({ ...settings, groqKey: v })}
              type="password"
              placeholder="gsk_..."
            />
            <SettingField
              label="DeepSeek API Key"
              value={settings.deepseekKey}
              onChange={(v) => setSettings({ ...settings, deepseekKey: v })}
              type="password"
              placeholder="sk-..."
            />
          </div>
        </Section>

        {/* Engine Configuration */}
        <Section icon={Server} title="Configuración de Engines (Master)">
          <div className="space-y-4">
            <SettingField
              label="Ollama URL"
              value={settings.ollamaUrl}
              onChange={(v) => setSettings({ ...settings, ollamaUrl: v })}
              placeholder="http://localhost:11434"
            />
            <SettingField
              label="LM Studio URL"
              value={settings.lmStudioUrl}
              onChange={(v) => setSettings({ ...settings, lmStudioUrl: v })}
              placeholder="http://localhost:1234"
            />
            <SettingField
              label="Jan URL"
              value={settings.janUrl}
              onChange={(v) => setSettings({ ...settings, janUrl: v })}
              placeholder="http://localhost:1337"
            />
          </div>
        </Section>

        {/* Worker Configuration */}
        <Section icon={Wifi} title="Configuración de Worker">
          <div className="space-y-4">
            <SettingField
              label="Worker Host IP"
              value={settings.workerHost}
              onChange={(v) => setSettings({ ...settings, workerHost: v })}
              placeholder="192.168.1.X"
            />
            <SettingField
              label="Worker Ollama Port"
              value={settings.workerOllamaPort}
              onChange={(v) => setSettings({ ...settings, workerOllamaPort: parseInt(v) })}
              type="number"
            />
            <SettingField
              label="Worker LM Studio Port"
              value={settings.workerLmStudioPort}
              onChange={(v) => setSettings({ ...settings, workerLmStudioPort: parseInt(v) })}
              type="number"
            />
            <SettingField
              label="Worker Jan Port"
              value={settings.workerJanPort}
              onChange={(v) => setSettings({ ...settings, workerJanPort: parseInt(v) })}
              type="number"
            />
          </div>
        </Section>

        {/* Discovery Configuration */}
        <Section icon={Shield} title="Configuración de Descubrimiento">
          <div className="space-y-4">
            <SettingField
              label="Discovery Port"
              value={settings.discoveryPort}
              onChange={(v) => setSettings({ ...settings, discoveryPort: parseInt(v) })}
              type="number"
            />
            <SettingField
              label="Discovery Interval (segundos)"
              value={settings.discoveryInterval}
              onChange={(v) => setSettings({ ...settings, discoveryInterval: parseInt(v) })}
              type="number"
            />
          </div>
        </Section>

        {/* Feature Flags */}
        <Section icon={Shield} title="Features">
          <div className="space-y-4">
            <ToggleField
              label="Web Agent Enabled"
              checked={settings.webAgentEnabled}
              onChange={(v) => setSettings({ ...settings, webAgentEnabled: v })}
            />
            <ToggleField
              label="Supabase Enabled"
              checked={settings.supabaseEnabled}
              onChange={(v) => setSettings({ ...settings, supabaseEnabled: v })}
            />
            <ToggleField
              label="Agent Reputation Enabled"
              checked={settings.agentReputationEnabled}
              onChange={(v) => setSettings({ ...settings, agentReputationEnabled: v })}
            />
          </div>
        </Section>
      </div>
    </div>
  )
}

function Section({ icon: Icon, title, children }) {
  return (
    <div className="p-6 bg-slate-800/50 rounded-xl border border-slate-700">
      <div className="flex items-center gap-3 mb-4">
        <Icon className="w-5 h-5 text-amber-500" />
        <h2 className="text-lg font-semibold text-white">{title}</h2>
      </div>
      {children}
    </div>
  )
}

function SettingField({ label, value, onChange, type = 'text', placeholder }) {
  return (
    <div>
      <label className="block text-sm text-slate-400 mb-2">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none"
      />
    </div>
  )
}

function ToggleField({ label, checked, onChange }) {
  return (
    <div className="flex items-center justify-between">
      <label className="text-sm text-slate-400">{label}</label>
      <button
        onClick={() => onChange(!checked)}
        className={`w-12 h-6 rounded-full transition-colors ${
          checked ? 'bg-amber-500' : 'bg-slate-700'
        }`}
      >
        <div
          className={`w-5 h-5 bg-white rounded-full transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-0.5'
          }`}
        />
      </button>
    </div>
  )
}
