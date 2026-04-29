import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  LayoutDashboard, 
  MessageSquare, 
  Database, 
  MessageCircle, 
  Settings, 
  Activity,
  Cpu,
  HardDrive,
  Wifi,
  Clock,
  Zap
} from 'lucide-react'

export function Dashboard({ connectionStatus }) {
  const navigate = useNavigate()
  const [metrics, setMetrics] = useState({
    activeDebates: 0,
    totalTokens: 0,
    avgLatency: 0,
    cpuUsage: 0,
    memoryUsage: 0
  })

  useEffect(() => {
    // Fetch metrics from API
    const fetchMetrics = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/system/metrics')
        if (response.ok) {
          const data = await response.json()
          setMetrics(data)
        }
      } catch (e) {
        console.error('Failed to fetch metrics:', e)
      }
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, 5000)

    return () => clearInterval(interval)
  }, [])

  const menuItems = [
    {
      icon: MessageSquare,
      label: 'Chat Directo',
      description: 'Consultas unilaterales a modelos',
      route: '/chat',
      color: 'blue'
    },
    {
      icon: MessageCircle,
      label: 'Gestor de Debates',
      description: 'Crear y monitorear debates multi-agente',
      route: '/debates',
      color: 'green'
    },
    {
      icon: Database,
      label: 'Base de Datos',
      description: 'Historial de debates y análisis',
      route: '/database',
      color: 'purple'
    },
    {
      icon: Settings,
      label: 'Configuración',
      description: 'API keys, modelos y engines',
      route: '/settings',
      color: 'orange'
    }
  ]

  const colorClasses = {
    blue: 'hover:bg-blue-500/20 hover:border-blue-500 group-hover:text-blue-400',
    green: 'hover:bg-green-500/20 hover:border-green-500 group-hover:text-green-400',
    purple: 'hover:bg-purple-500/20 hover:border-purple-500 group-hover:text-purple-400',
    orange: 'hover:bg-orange-500/20 hover:border-orange-500 group-hover:text-orange-400'
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {/* Header */}
      <nav className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-500 rounded-lg flex items-center justify-center">
                <span className="text-slate-900 font-bold text-xl">S</span>
              </div>
              <div>
                <h1 className="font-semibold text-white text-lg">Synapse Council</h1>
                <p className="text-xs text-slate-500">Dashboard v3.0</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm">
                <div className={`w-2 h-2 rounded-full ${connectionStatus.master ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-slate-400">Master</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <div className={`w-2 h-2 rounded-full ${connectionStatus.worker ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-slate-400">Worker</span>
              </div>
              {connectionStatus.transferSpeed > 0 && (
                <div className="flex items-center gap-2 text-sm text-amber-500">
                  <Wifi className="w-4 h-4" />
                  <span>{connectionStatus.transferSpeed.toFixed(2)} MB/s</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <MetricCard
            icon={Activity}
            label="Debates Activos"
            value={metrics.activeDebates}
            color="blue"
          />
          <MetricCard
            icon={Zap}
            label="Tokens Totales"
            value={metrics.totalTokens.toLocaleString()}
            color="amber"
          />
          <MetricCard
            icon={Clock}
            label="Latencia Promedio"
            value={`${metrics.avgLatency}ms`}
            color="green"
          />
          <MetricCard
            icon={Wifi}
            label="Velocidad Transferencia"
            value={`${connectionStatus.transferSpeed.toFixed(2)} MB/s`}
            color="purple"
          />
        </div>

        {/* System Resources */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <ResourceCard
            icon={Cpu}
            label="CPU Master"
            value={`${metrics.cpuUsage}%`}
            color="blue"
          />
          <ResourceCard
            icon={HardDrive}
            label="Memoria Master"
            value={`${metrics.memoryUsage}%`}
            color="green"
          />
        </div>

        {/* Menu Grid */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-4">Herramientas</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {menuItems.map((item) => (
              <button
                key={item.route}
                onClick={() => navigate(item.route)}
                className={`group p-6 bg-slate-800/50 border-2 border-slate-700 rounded-xl text-left transition-all ${colorClasses[item.color]}`}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 bg-slate-900 rounded-lg ${colorClasses[item.color]}`}>
                    <item.icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg text-white mb-1">{item.label}</h3>
                    <p className="text-sm text-slate-400">{item.description}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="p-6 bg-slate-800/30 rounded-xl border border-slate-800">
          <h3 className="font-semibold text-amber-500 mb-4">Estado del Sistema</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-slate-500">Master</p>
              <p className={connectionStatus.master ? 'text-green-400' : 'text-red-400'}>
                {connectionStatus.master ? 'Online' : 'Offline'}
              </p>
            </div>
            <div>
              <p className="text-slate-500">Worker</p>
              <p className={connectionStatus.worker ? 'text-green-400' : 'text-red-400'}>
                {connectionStatus.worker ? 'Online' : 'Offline'}
              </p>
            </div>
            <div>
              <p className="text-slate-500">Enlace</p>
              <p className={connectionStatus.linked ? 'text-green-400' : 'text-red-400'}>
                {connectionStatus.linked ? 'Activo' : 'Inactivo'}
              </p>
            </div>
            <div>
              <p className="text-slate-500">Puerto API</p>
              <p className="text-slate-300">8000</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

function MetricCard({ icon: Icon, label, value, color }) {
  const colorClasses = {
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
    amber: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
    purple: 'bg-purple-500/10 border-purple-500/30 text-purple-400'
  }

  return (
    <div className={`p-4 rounded-xl border ${colorClasses[color]}`}>
      <Icon className="w-5 h-5 mb-2" />
      <p className="text-sm text-slate-400 mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  )
}

function ResourceCard({ icon: Icon, label, value, color }) {
  const colorClasses = {
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400'
  }

  return (
    <div className={`p-4 rounded-xl border ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <Icon className="w-5 h-5" />
        <span className="text-2xl font-bold">{value}</span>
      </div>
      <p className="text-sm text-slate-400">{label}</p>
      <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color === 'blue' ? 'bg-blue-500' : 'bg-green-500'}`}
          style={{ width: `${parseFloat(value)}%` }}
        />
      </div>
    </div>
  )
}
