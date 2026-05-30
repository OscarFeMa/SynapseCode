import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { SessionView } from './components/Chat/SessionView'
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

function SessionPage() {
  return <SessionView />
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
