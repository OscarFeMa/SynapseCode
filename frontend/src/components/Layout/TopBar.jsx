import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Wifi, WifiOff, Bell, Search } from 'lucide-react'
import { useWebSocketStore } from '../../store/useStore'

export function TopBar() {
  const [time, setTime] = useState(new Date().toLocaleTimeString('es-ES'))
  const connected = useWebSocketStore((s) => s.connected)

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date().toLocaleTimeString('es-ES')), 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="h-14 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          {connected ? (
            <Wifi className="w-4 h-4 text-emerald-500" />
          ) : (
            <WifiOff className="w-4 h-4 text-red-500" />
          )}
          <span className={`text-xs font-medium ${connected ? 'text-emerald-500' : 'text-red-500'}`}>
            {connected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="p-2 text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-slate-800">
          <Search className="w-4 h-4" />
        </button>
        <button className="p-2 text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-slate-800 relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-amber-500 rounded-full" />
        </button>
        <div className="text-xs text-slate-500 font-mono">{time}</div>
        <Link
          to="/"
          className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-slate-900 text-xs font-medium rounded-lg transition-colors"
        >
          Inicio
        </Link>
      </div>
    </header>
  )
}
