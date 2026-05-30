import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
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
    <div className="min-h-screen bg-[#F5F3EE] text-[#161616]">
      <nav className="bg-white border-b border-[rgba(0,0,0,0.08)]">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <a href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-[#23403B] rounded flex items-center justify-center">
                <span className="text-[#F5F3EE] font-serif font-bold text-sm">S</span>
              </div>
              <span className="font-serif text-[#161616]">SynapseCode</span>
              <span className="text-xs text-[#8A8780]">v3.0</span>
            </a>
            <div className="flex items-center gap-4">
              <a
                href="/history"
                className="text-sm text-[#5C5C5C] hover:text-[#161616] transition-colors"
              >
                Historial
              </a>
              <a
                href="/dashboard"
                className="text-sm text-[#5C5C5C] hover:text-[#161616] transition-colors"
              >
                Dashboard
              </a>
              <a
                href="/"
                className="px-3 py-1.5 bg-[#23403B] hover:bg-[#2D524C] text-[#F5F3EE] text-sm font-medium rounded transition-colors"
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
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
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
