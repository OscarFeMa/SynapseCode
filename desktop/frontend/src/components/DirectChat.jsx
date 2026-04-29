import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, Trash2, Save } from 'lucide-react'

export function DirectChat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState('groq')
  const [selectedEngine, setSelectedEngine] = useState('llama-3.3-70b-versatile')
  const messagesEndRef = useRef(null)

  const models = {
    groq: {
      name: 'Groq',
      engines: ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768', 'gemma-7b-it']
    },
    deepseek: {
      name: 'DeepSeek',
      engines: ['deepseek-chat', 'deepseek-coder']
    },
    gemini: {
      name: 'Gemini',
      engines: ['gemini-1.5-pro', 'gemini-1.5-flash']
    },
    ollama: {
      name: 'Ollama Local',
      engines: ['llama3', 'mistral', 'deepseek-coder']
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = { role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/api/v1/system/chat/direct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          model: selectedEngine,
          engine: selectedModel
        })
      })

      if (response.ok) {
        const data = await response.json()
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Error: No se pudo obtener respuesta' }])
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }])
    }

    setIsLoading(false)
  }

  const handleClear = () => {
    setMessages([])
  }

  const handleSave = () => {
    const conversation = {
      model: selectedModel,
      engine: selectedEngine,
      messages,
      timestamp: new Date().toISOString()
    }
    
    // Save to localStorage
    const saved = JSON.parse(localStorage.getItem('synapse-chats') || '[]')
    saved.push(conversation)
    localStorage.setItem('synapse-chats', JSON.stringify(saved))
    
    alert('Conversación guardada')
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {/* Header */}
      <nav className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-white">Chat Directo a Modelos</h1>
            <div className="flex gap-2">
              <button
                onClick={handleClear}
                className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                <span className="text-sm">Limpiar</span>
              </button>
              <button
                onClick={handleSave}
                className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <Save className="w-4 h-4" />
                <span className="text-sm">Guardar</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Model Selection */}
        <div className="mb-6 p-4 bg-slate-800/50 rounded-xl border border-slate-700">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">Proveedor</label>
              <select
                value={selectedModel}
                onChange={(e) => {
                  setSelectedModel(e.target.value)
                  setSelectedEngine(models[e.target.value].engines[0])
                }}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:border-amber-500 focus:outline-none"
              >
                {Object.entries(models).map(([key, value]) => (
                  <option key={key} value={key}>{value.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">Modelo</label>
              <select
                value={selectedEngine}
                onChange={(e) => setSelectedEngine(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:border-amber-500 focus:outline-none"
              >
                {models[selectedModel].engines.map(engine => (
                  <option key={engine} value={engine}>{engine}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="mb-4 p-4 bg-slate-800/30 rounded-xl border border-slate-800 h-[500px] overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-slate-500">
              <p>Inicia una conversación con el modelo seleccionado</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] p-3 rounded-lg ${
                      msg.role === 'user'
                        ? 'bg-amber-500 text-slate-900'
                        : 'bg-slate-700 text-slate-200'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="p-3 bg-slate-700 rounded-lg">
                    <Loader2 className="w-5 h-5 animate-spin" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="Escribe tu mensaje..."
            rows={2}
            className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none resize-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 bg-amber-500 hover:bg-amber-600 disabled:bg-slate-700 disabled:cursor-not-allowed text-slate-900 font-semibold rounded-lg transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
