import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// API Base URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

// Normalize agent_calls API response into turns array
function normalizeTurns(agentCalls) {
  const turns = []
  let turnNum = 1
  for (const [phase, calls] of Object.entries(agentCalls)) {
    for (const call of calls) {
      turns.push({
        turn_number: turnNum++,
        agent: { name: call.slot, role: phase, model: call.model },
        agent_name: call.slot,
        agent_role: phase,
        status: call.status?.toLowerCase() || 'unknown',
        tokens_in: call.tokens_in || 0,
        tokens_out: call.tokens_out || 0,
        response_received: call.response_preview || '',
        model: call.model,
        latency_ms: call.latency_ms,
      })
    }
  }
  return turns
}

// Session Store
export const useSessionStore = create((set) => ({
  // State
  sessions: [],
  currentSession: null,
  isLoading: false,
  error: null,
  
  // Actions
  setCurrentSession: (session) => set({ currentSession: session }),
  
  createSession: async (query, title = '', maxRounds = 2) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, title, max_rounds: maxRounds })
      })
      
      if (!response.ok) throw new Error('Failed to create session')
      
      const data = await response.json()
      set({ currentSession: { id: data.session_id, status: data.status, query, topic: title || query }, isLoading: false })
      return data.session_id
    } catch (error) {
      set({ error: error.message, isLoading: false })
      return null
    }
  },
  
  fetchSession: async (sessionId) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(`${API_BASE}/sessions/${sessionId}`)
      if (!response.ok) throw new Error('Session not found')
      
      const data = await response.json()
      const s = data.session
      
      // Normalize: map API fields to component-expected fields
      const normalized = {
        ...s,
        topic: s.title || s.query,
        turns: normalizeTurns(data.agent_calls || {}),
        iterations: [],
        tribunal_verdict: s.consensus_level ? {
          evidence_score: 0.5,
          risk_score: 0.5,
          alignment_score: 0.5,
        } : null,
        final_verdict: s.final_summary || '',
        structured_report: null,
        progress: s.max_rounds > 0 ? Math.round((s.rounds_executed / s.max_rounds) * 100) : 0,
        web_context: null,
        web_search: false,
      }
      
      set({ currentSession: normalized, isLoading: false })
      return data
    } catch (error) {
      set({ error: error.message, isLoading: false })
      return null
    }
  },
  
  fetchSessions: async (limit = 50) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(`${API_BASE}/sessions?limit=${limit}`)
      if (!response.ok) throw new Error('Failed to fetch sessions')
      
      const data = await response.json()
      const normalized = (data.sessions || []).map((s) => ({
        ...s,
        topic: s.title || s.query,
        turns: [],
      }))
      set({ sessions: normalized, isLoading: false })
      return normalized
    } catch (error) {
      set({ error: error.message, isLoading: false })
      return []
    }
  },
  
  clearError: () => set({ error: null }),
}))

// WebSocket Store for real-time events
export const useWebSocketStore = create((set, get) => ({
  // State
  socket: null,
  isConnected: false,
  events: [],
  agentTokens: {}, // { agentId: tokens[] }
  currentPhase: null,
  tribunalScores: null,
  
  // Actions
  connect: (sessionId) => {
    const ws = new WebSocket(`${WS_BASE}/ws/sessions/${sessionId}`)
    
    ws.onopen = () => {
      set({ socket: ws, isConnected: true, events: [] })
      console.log('WebSocket connected')
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        get().handleEvent(data)
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    }
    
    ws.onclose = () => {
      set({ socket: null, isConnected: false })
      console.log('WebSocket disconnected')
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      set({ isConnected: false })
    }
    
    // Heartbeat
    const heartbeat = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 5000)
    
    // Store heartbeat interval for cleanup
    set({ heartbeatInterval: heartbeat })
    
    return ws
  },
  
  disconnect: () => {
    const { socket, heartbeatInterval } = get()
    if (heartbeatInterval) clearInterval(heartbeatInterval)
    if (socket) {
      socket.close()
    }
    set({ socket: null, isConnected: false, events: [], agentTokens: {} })
  },
  
  handleEvent: (event) => {
    const { events, agentTokens } = get()
    
    // Add to events log
    set({ events: [...events, event] })
    
    // Handle specific event types
    switch (event.type) {
      case 'phase_started':
        set({ currentPhase: event.payload.phase })
        break
        
      case 'agent_token': {
        const { agent, token } = event.payload
        set({
          agentTokens: {
            ...agentTokens,
            [agent]: (agentTokens[agent] || '') + token
          }
        })
        break
      }
        
      case 'tribunal_verdict':
        set({ tribunalScores: {
          evidence: event.payload.evidence_score,
          risk: event.payload.risk_score,
          consensus: event.payload.consensus_reached
        }})
        break
        
      case 'session_completed': {
        // Auto-fetch final results
        const sessionId = event.session_id
        useSessionStore.getState().fetchSession(sessionId)
        break
      }
    }
  },
  
  clearEvents: () => set({ events: [], agentTokens: {}, currentPhase: null, tribunalScores: null }),
  
  getAgentText: (agentId) => {
    return get().agentTokens[agentId] || ''
  },
}))

// Config Store (persisted)
export const useConfigStore = create(
  persist(
    (set) => ({
      // Default config
      defaultRounds: 2,
      autoConnectWebSocket: true,
      theme: 'dark',
      
      // Actions
      setDefaultRounds: (rounds) => set({ defaultRounds: rounds }),
      setAutoConnect: (value) => set({ autoConnectWebSocket: value }),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'synapse-council-config',
    }
  )
)

// UI Store (ephemeral UI state)
export const useUIStore = create((set) => ({
  // State
  sidebarOpen: true,
  activeTab: 'chat', // 'chat', 'history', 'config'
  showTribunalPanel: true,
  
  // Actions
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),
  toggleTribunalPanel: () => set((state) => ({ showTribunalPanel: !state.showTribunalPanel })),
}))
