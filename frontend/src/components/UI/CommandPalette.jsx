import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, LayoutDashboard, MessageSquare, PlusCircle, BarChart3, Scale, Cpu, Database, History, Settings, X } from 'lucide-react'

const commands = [
  { id: 'dashboard', label: 'Ir al Dashboard', icon: LayoutDashboard, path: '/dashboard', shortcut: 'g d' },
  { id: 'debates', label: 'Ver Debates', icon: MessageSquare, path: '/debates', shortcut: 'g b' },
  { id: 'new-debate', label: 'Nuevo Debate', icon: PlusCircle, path: '/debates/new', shortcut: 'n' },
  { id: 'monitor', label: 'Monitor del Sistema', icon: BarChart3, path: '/monitor', shortcut: 'g m' },
  { id: 'tribunal', label: 'Tribunal', icon: Scale, path: '/tribunal', shortcut: 'g t' },
  { id: 'models', label: 'Registro de Modelos', icon: Cpu, path: '/models', shortcut: 'g o' },
  { id: 'cache', label: 'Gestion de Cache', icon: Database, path: '/cache', shortcut: 'g c' },
  { id: 'history', label: 'Historico de Debates', icon: History, path: '/history', shortcut: 'g h' },
  { id: 'settings', label: 'Ajustes', icon: Settings, path: '/settings', shortcut: 'g s' },
]

export function CommandPalette({ isOpen, onClose }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  const filtered = commands.filter((cmd) =>
    cmd.label.toLowerCase().includes(query.toLowerCase())
  )

  const handleSelect = useCallback(
    (cmd) => {
      navigate(cmd.path)
      setQuery('')
      onClose()
    },
    [navigate, onClose]
  )

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
      return () => window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 border-b border-slate-800">
          <Search className="w-4 h-4 text-slate-500 flex-shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar comando o pagina..."
            className="flex-1 bg-transparent py-3 text-sm text-white placeholder-slate-500 outline-none"
            autoFocus
          />
          <kbd className="text-[10px] text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">ESC</kbd>
        </div>

        {/* Results */}
        <div className="max-h-72 overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-slate-500">
              No se encontraron resultados para "{query}"
            </div>
          ) : (
            filtered.map((cmd) => (
              <button
                key={cmd.id}
                onClick={() => handleSelect(cmd)}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-left hover:bg-slate-800 transition-colors"
              >
                <cmd.icon className="w-4 h-4 text-slate-400 flex-shrink-0" />
                <span className="text-sm text-white flex-1">{cmd.label}</span>
                {cmd.shortcut && (
                  <kbd className="text-[10px] text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded font-mono">
                    {cmd.shortcut}
                  </kbd>
                )}
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-slate-800 text-[10px] text-slate-600 flex items-center gap-3">
          <span>
            <kbd className="bg-slate-800 px-1 rounded">Ctrl+K</kbd> para abrir
          </span>
          <span>
            <kbd className="bg-slate-800 px-1 rounded">↑↓</kbd> navegar
          </span>
          <span>
            <kbd className="bg-slate-800 px-1 rounded">Enter</kbd> seleccionar
          </span>
        </div>
      </div>
    </div>
  )
}

export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setIsOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return { isOpen, open: () => setIsOpen(true), close: () => setIsOpen(false) }
}
