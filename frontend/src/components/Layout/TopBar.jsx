import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Wifi, WifiOff, Bell, Search } from 'lucide-react'
import { useWebSocketStore } from '../../store/useStore'

export function TopBar({ onOpenCommandPalette }) {
  const [time, setTime] = useState(new Date().toLocaleTimeString('es-ES'))
  const connected = useWebSocketStore((s) => s.connected)

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date().toLocaleTimeString('es-ES')), 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="h-14 bg-white border-b border-[rgba(0,0,0,0.08)] flex items-center justify-between px-6 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          {connected ? (
            <Wifi className="w-4 h-4 text-[#4A7C59]" />
          ) : (
            <WifiOff className="w-4 h-4 text-[#8B3A3A]" />
          )}
          <span className={`text-xs font-medium ${connected ? 'text-[#4A7C59]' : 'text-[#8B3A3A]'}`}>
            {connected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2 px-3 py-1.5 bg-[#F5F3EE] border border-[rgba(0,0,0,0.08)] rounded text-xs text-[#5C5C5C] hover:text-[#161616] hover:border-[rgba(0,0,0,0.12)] transition-colors"
        >
          <Search className="w-3.5 h-3.5" />
          <span>Buscar...</span>
          <kbd className="ml-2 text-[10px] bg-white px-1.5 py-0.5 rounded font-mono text-[#8A8780]">Ctrl+K</kbd>
        </button>
        <button className="p-2 text-[#5C5C5C] hover:text-[#161616] transition-colors rounded hover:bg-[#F5F3EE] relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-[#B98B4D] rounded-full" />
        </button>
        <div className="text-xs text-[#8A8780] font-mono tabular-nums">{time}</div>
        <Link
          to="/"
          className="px-3 py-1.5 bg-[#23403B] hover:bg-[#2D524C] text-[#F5F3EE] text-xs font-medium rounded transition-colors"
        >
          Inicio
        </Link>
      </div>
    </header>
  )
}
