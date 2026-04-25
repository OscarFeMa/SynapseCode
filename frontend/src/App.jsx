import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { ChatInput } from './components/Chat/ChatInput'
import { SessionView } from './components/Chat/SessionView'
import { SessionList } from './components/History/SessionList'
import { useWebSocketStore } from './store/useStore'

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {/* Navbar */}
      <nav className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <a href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-amber-500 rounded-lg flex items-center justify-center">
                <span className="text-slate-900 font-bold text-lg">S</span>
              </div>
              <span className="font-semibold text-white">Synapse Council</span>
              <span className="text-xs text-slate-500">v2.0</span>
            </a>
            
            <div className="flex items-center gap-4">
              <a 
                href="/history" 
                className="text-sm text-slate-400 hover:text-white transition-colors"
              >
                Historial
              </a>
              <a 
                href="/" 
                className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-slate-900 text-sm font-medium rounded-lg transition-colors"
              >
                Nueva Consulta
              </a>
            </div>
          </div>
        </div>
      </nav>
      
      {/* Main content */}
      <main>
        {children}
      </main>
    </div>
  )
}

function HomePage() {
  const navigate = useNavigate()
  const clearEvents = useWebSocketStore((state) => state.clearEvents)
  
  const handleSessionCreated = (sessionId) => {
    clearEvents()
    navigate(`/session/${sessionId}`)
  }
  
  return (
    <Layout>
      <div className="py-12">
        <ChatInput onSessionCreated={handleSessionCreated} />
      </div>
    </Layout>
  )
}

function SessionPage() {
  return (
    <SessionView />
  )
}

function HistoryPage() {
  return (
    <Layout>
      <SessionList />
    </Layout>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/session/:sessionId" element={<SessionPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
