import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ConnectionWindow } from './components/ConnectionWindow'
import { Dashboard } from './components/Dashboard'
import { DirectChat } from './components/DirectChat'
import { DatabaseViewer } from './components/DatabaseViewer'
import { DebateManager } from './components/DebateManager'
import { Settings } from './components/Settings'

function App() {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState({
    master: false,
    worker: false,
    linked: false,
    transferSpeed: 0
  })

  useEffect(() => {
    // Check connection status periodically
    const checkStatus = async () => {
      if (window.electronAPI) {
        const status = await window.electronAPI.checkConnection()
        setConnectionStatus(status)
        setIsConnected(status.linked)
      }
    }

    checkStatus()
    const interval = setInterval(checkStatus, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <Router>
      <Routes>
        <Route 
          path="/" 
          element={
            isConnected ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <ConnectionWindow 
                connectionStatus={connectionStatus}
                onConnected={() => setIsConnected(true)}
              />
            )
          } 
        />
        <Route path="/dashboard" element={<Dashboard connectionStatus={connectionStatus} />} />
        <Route path="/chat" element={<DirectChat />} />
        <Route path="/database" element={<DatabaseViewer />} />
        <Route path="/debates" element={<DebateManager />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
