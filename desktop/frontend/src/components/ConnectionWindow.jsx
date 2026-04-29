import { useState, useEffect } from 'react'
import { Link, Wifi, WifiOff, Play, RefreshCw, Loader2, CheckCircle, XCircle } from 'lucide-react'

export function ConnectionWindow({ connectionStatus, onConnected }) {
  const [isLinking, setIsLinking] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [logs, setLogs] = useState([])
  const [workerIp, setWorkerIp] = useState('')
  const [remoteUsername, setRemoteUsername] = useState('MAKEDER\\maked')
  const [remotePassword, setRemotePassword] = useState('')
  const [networkPath, setNetworkPath] = useState('\\\\MAKEDERPC\\Synapse\\backend')
  const [macAddress, setMacAddress] = useState('E0:0A:F6:9E:CB:01')
  const [pythonPath, setPythonPath] = useState('py')

  useEffect(() => {
    if (window.electronAPI) {
      // Listen for worker discovery
      window.electronAPI.onWorkerDiscovered((data) => {
        setLogs(prev => [...prev, `Worker descubierto: ${data.ip}:${data.port}`])
        setWorkerIp(data.ip)
      })

      // Listen for master logs
      window.electronAPI.onMasterLog((data) => {
        setLogs(prev => [...prev, `Master: ${data}`])
      })

      // Listen for worker logs
      window.electronAPI.onWorkerLog((data) => {
        setLogs(prev => [...prev, `Worker: ${data}`])
      })

      // Start discovery
      window.electronAPI.startDiscovery()
    }

    return () => {
      if (window.electronAPI) {
        window.electronAPI.removeAllListeners()
      }
    }
  }, [])

  const handleLink = async () => {
    setIsLinking(true)
    setLogs(prev => [...prev, 'Iniciando descubrimiento de Worker...'])
    
    if (window.electronAPI) {
      // First try MAC address discovery if provided
      if (macAddress) {
        setLogs(prev => [...prev, `Buscando por dirección MAC: ${macAddress}...`])
        const macResult = await window.electronAPI.findByMac(macAddress)
        if (macResult.success) {
          setLogs(prev => [...prev, `Worker encontrado por MAC: ${macResult.ip}`])
          setIsLinking(false)
          return
        } else {
          setLogs(prev => [...prev, `MAC no encontrada, intentando UDP...`])
        }
      }
      
      await window.electronAPI.broadcastDiscovery()
      
      // Broadcast multiple times to ensure discovery
      for (let i = 0; i < 5; i++) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        await window.electronAPI.broadcastDiscovery()
        setLogs(prev => [...prev, `Broadcast discovery ${i + 1}/5...`])
      }
      
      setLogs(prev => [...prev, 'Descubrimiento completado'])
      
      if (!workerIp) {
        setLogs(prev => [...prev, 'Worker no encontrado por UDP, intentando escaneo de red...'])
        const scanResult = await window.electronAPI.scanNetwork()
        if (scanResult.success) {
          setLogs(prev => [...prev, `Worker encontrado por escaneo: ${scanResult.ip}`])
        } else {
          setLogs(prev => [...prev, 'Worker no encontrado en la red'])
        }
      }
      
      setIsLinking(false)
    }
  }

  const handleStart = async () => {
    setIsStarting(true)
    setLogs(prev => [...prev, '⚠ Inicio automático desactivado en versión empaquetada'])
    setLogs(prev => [...prev, '💡 Inicia Master y Worker manualmente:'])
    setLogs(prev => [...prev, '   MASTER: cd d:\\proyectos\\Synapse\\backend && set NODE_ROLE=MASTER && py -m backend.main'])
    setLogs(prev => [...prev, '   WORKER: cd C:\\Synapse\\backend && set NODE_ROLE=WORKER && python -m backend.main'])
    setLogs(prev => [...prev, '💡 Usa "Abrir Escritorio Remoto" para conectarte al Worker'])
    setIsStarting(false)
  }

  const handleOpenRDP = async () => {
    if (window.electronAPI) {
      const rdpPath = 'D:\\proyectos\\Synapse\\Escritorio.rdp'
      await window.electronAPI.openRDP(rdpPath)
      setLogs(prev => [...prev, 'Abriendo escritorio remoto...'])
    }
  }

  const handleRefresh = async () => {
    if (window.electronAPI) {
      const status = await window.electronAPI.checkConnection()
      setLogs(prev => [...prev, `Estado actualizado: Master=${status.master}, Worker=${status.worker}`])
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center">
              <span className="text-slate-900 font-bold text-2xl">S</span>
            </div>
            <h1 className="text-4xl font-bold text-white">
              Synapse <span className="text-amber-500">Council</span>
            </h1>
          </div>
          <p className="text-slate-400">Gestor de Conexión Master/Worker</p>
        </div>

        {/* Connection Status Cards */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Master Status */}
          <div className={`p-6 rounded-xl border-2 transition-all ${
            connectionStatus.master 
              ? 'bg-green-500/10 border-green-500' 
              : 'bg-slate-800/50 border-slate-700'
          }`}>
            <div className="flex items-center gap-3 mb-3">
              {connectionStatus.master ? (
                <CheckCircle className="w-6 h-6 text-green-500" />
              ) : (
                <XCircle className="w-6 h-6 text-slate-500" />
              )}
              <h3 className="font-semibold text-lg">Master</h3>
            </div>
            <p className="text-sm text-slate-400">
              {connectionStatus.master ? 'Online' : 'Offline'}
            </p>
            <p className="text-xs text-slate-500 mt-1">Puerto: 8000</p>
          </div>

          {/* Worker Status */}
          <div className={`p-6 rounded-xl border-2 transition-all ${
            connectionStatus.worker 
              ? 'bg-green-500/10 border-green-500' 
              : 'bg-slate-800/50 border-slate-700'
          }`}>
            <div className="flex items-center gap-3 mb-3">
              {connectionStatus.worker ? (
                <CheckCircle className="w-6 h-6 text-green-500" />
              ) : (
                <XCircle className="w-6 h-6 text-slate-500" />
              )}
              <h3 className="font-semibold text-lg">Worker</h3>
            </div>
            <p className="text-sm text-slate-400">
              {connectionStatus.worker ? 'Online' : 'Offline'}
            </p>
            {workerIp && (
              <p className="text-xs text-slate-500 mt-1">IP: {workerIp}</p>
            )}
          </div>
        </div>

        {/* Link Status */}
        <div className={`p-6 rounded-xl border-2 mb-6 transition-all ${
          connectionStatus.linked 
            ? 'bg-amber-500/10 border-amber-500' 
            : 'bg-slate-800/50 border-slate-700'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {connectionStatus.linked ? (
                <Link className="w-6 h-6 text-amber-500" />
              ) : (
                <WifiOff className="w-6 h-6 text-slate-500" />
              )}
              <div>
                <h3 className="font-semibold text-lg">Estado de Enlace</h3>
                <p className="text-sm text-slate-400">
                  {connectionStatus.linked ? 'Enlazados' : 'No enlazados'}
                </p>
              </div>
            </div>
            {connectionStatus.linked && connectionStatus.transferSpeed > 0 && (
              <div className="text-right">
                <p className="text-sm text-slate-400">Velocidad</p>
                <p className="text-lg font-semibold text-amber-500">
                  {connectionStatus.transferSpeed.toFixed(2)} MB/s
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Remote Configuration */}
        {!connectionStatus.linked && (
          <div className="p-6 rounded-xl border-2 border-slate-700 bg-slate-800/50 mb-6">
            <h3 className="font-semibold text-lg mb-4 text-slate-300">Configuración</h3>
            <div className="space-y-3">
              <div>
                <label className="text-sm text-slate-400 block mb-1">Ruta de Python</label>
                <input
                  type="text"
                  value={pythonPath}
                  onChange={(e) => setPythonPath(e.target.value)}
                  placeholder="python"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
                <p className="text-xs text-slate-500 mt-1">Ruta completa si python no está en PATH (ej: C:\Python311\python.exe)</p>
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-1">Dirección MAC del Worker</label>
                <input
                  type="text"
                  value={macAddress}
                  onChange={(e) => setMacAddress(e.target.value)}
                  placeholder="E0:0A:F6:9E:CB:01"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
                <p className="text-xs text-slate-500 mt-1">Usa MAC para encontrar IP dinámica automáticamente</p>
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-1">Usuario Windows</label>
                <input
                  type="text"
                  value={remoteUsername}
                  onChange={(e) => setRemoteUsername(e.target.value)}
                  placeholder="WORKER_PC\\usuario"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-1">Contraseña</label>
                <input
                  type="password"
                  value={remotePassword}
                  onChange={(e) => setRemotePassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-1">Ruta de Red (Backend)</label>
                <input
                  type="text"
                  value={networkPath}
                  onChange={(e) => setNetworkPath(e.target.value)}
                  placeholder="\\\\WORKER_PC\\Synapse\\backend"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4 mb-6">
          {!connectionStatus.linked && (
            <>
              <button
                onClick={handleLink}
                disabled={isLinking || isStarting}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-900 disabled:cursor-not-allowed border border-slate-700 rounded-lg transition-colors"
              >
                {isLinking ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>Enlazando...</span>
                  </>
                ) : (
                  <>
                    <Wifi className="w-5 h-5" />
                    <span>Enlazar Master/Worker</span>
                  </>
                )}
              </button>

              <button
                onClick={handleStart}
                disabled={isStarting || isLinking}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-amber-500 hover:bg-amber-600 disabled:bg-slate-700 disabled:cursor-not-allowed text-slate-900 font-semibold rounded-lg transition-colors"
              >
                {isStarting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Iniciando...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    <span>Arrancar Master/Worker</span>
                  </>
                )}
              </button>
            </>
          )}

          {connectionStatus.linked && (
            <button
              onClick={() => onConnected()}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-amber-500 hover:bg-amber-600 text-slate-900 font-semibold rounded-lg transition-colors"
            >
              <span className="text-xl font-bold">SynapseIA</span>
              <span className="text-sm">→ Abrir Dashboard</span>
            </button>
          )}
        </div>

        {/* RDP Button */}
        {!connectionStatus.linked && (
          <button
            onClick={handleOpenRDP}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-slate-400 hover:text-slate-200 transition-colors mb-4"
          >
            <span className="text-sm">Abrir Escritorio Remoto (RDP)</span>
          </button>
        )}

        {/* Refresh Button */}
        <button
          onClick={handleRefresh}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          <span className="text-sm">Actualizar estado</span>
        </button>

        {/* Logs */}
        {logs.length > 0 && (
          <div className="mt-6 p-4 bg-slate-900/50 rounded-lg border border-slate-800">
            <h4 className="text-sm font-semibold text-slate-400 mb-2">Logs</h4>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {logs.map((log, i) => (
                <p key={i} className="text-xs text-slate-500 font-mono">
                  {log}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
