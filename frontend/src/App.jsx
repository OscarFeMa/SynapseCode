import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { ChatInput } from './components/Chat/ChatInput'
import { SessionView } from './components/Chat/SessionView'
import { SessionList } from './components/History/SessionList'
import { useWebSocketStore } from './store/useStore'
import { AppLayout } from './components/Layout/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { DebatesPage } from './pages/DebatesPage'
import { NewDebatePage } from './pages/NewDebatePage'
import { MonitorPage } from './pages/MonitorPage'
import { TribunalPage } from './pages/OtherPages'
import { HistoryPage } from './pages/HistoryPage'
import { ModelsPage } from './pages/ModelsPage'
import { CachePage } from './pages/CachePage'
import { SettingsPage } from './pages/SettingsPage'
import { DebateLivePage } from './pages/DebateLivePage'

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
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
                href="/dashboard"
                className="text-sm text-slate-400 hover:text-white transition-colors"
              >
                Dashboard
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
      <main>{children}</main>
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
  return <SessionView />
}

function HistoryPageLegacy() {
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
        {/* Legacy routes - still work */}
        <Route path="/" element={<HomePage />} />
        <Route path="/session/:sessionId" element={<SessionPage />} />
        <Route path="/history" element={<AppLayout><HistoryPage /></AppLayout>} />

        {/* New dashboard routes */}
        <Route
          path="/dashboard"
          element={
            <AppLayout>
              <DashboardPage />
            </AppLayout>
          }
        />
        <Route
          path="/debates"
          element={
            <AppLayout>
              <DebatesPage />
            </AppLayout>
          }
        />
        <Route
          path="/debates/new"
          element={
            <AppLayout>
              <NewDebatePage />
            </AppLayout>
          }
        />
        <Route
          path="/debates/:sessionId"
          element={
            <AppLayout>
              <DebateLivePage />
            </AppLayout>
          }
        />
        <Route
          path="/monitor"
          element={
            <AppLayout>
              <MonitorPage />
            </AppLayout>
          }
        />
        <Route
          path="/tribunal"
          element={
            <AppLayout>
              <TribunalPage />
            </AppLayout>
          }
        />
        <Route
          path="/models"
          element={
            <AppLayout>
              <ModelsPage />
            </AppLayout>
          }
        />
        <Route
          path="/cache"
          element={
            <AppLayout>
              <CachePage />
            </AppLayout>
          }
        />
        <Route
          path="/settings"
          element={
            <AppLayout>
              <SettingsPage />
            </AppLayout>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
