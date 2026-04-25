import { useState, useCallback, useEffect } from 'react'
import { useSessionStore, useWebSocketStore } from '../store/useStore'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export function useSession(sessionId) {
  const { currentSession, isLoading, error, fetchSession } = useSessionStore()
  const { disconnect } = useWebSocketStore()
  
  // Fetch session data
  useEffect(() => {
    if (sessionId) {
      fetchSession(sessionId)
    }
    
    return () => {
      disconnect()
    }
  }, [sessionId, fetchSession, disconnect])
  
  // Poll for updates if session is running
  useEffect(() => {
    if (!sessionId || !currentSession) return
    
    if (currentSession.status === 'RUNNING') {
      const interval = setInterval(() => {
        fetchSession(sessionId)
      }, 3000)
      
      return () => clearInterval(interval)
    }
  }, [sessionId, currentSession, fetchSession])
  
  return {
    session: currentSession,
    isLoading,
    error,
    refresh: () => fetchSession(sessionId),
  }
}

export function useCreateSession() {
  const { createSession, isLoading, error } = useSessionStore()
  const [createdSessionId, setCreatedSessionId] = useState(null)
  
  const create = useCallback(async (query, title, maxRounds) => {
    const sessionId = await createSession(query, title, maxRounds)
    if (sessionId) {
      setCreatedSessionId(sessionId)
    }
    return sessionId
  }, [createSession])
  
  return {
    create,
    createdSessionId,
    isLoading,
    error,
    reset: () => setCreatedSessionId(null),
  }
}

export function useSessionList() {
  const { sessions, isLoading, error, fetchSessions } = useSessionStore()
  
  const refresh = useCallback(() => {
    return fetchSessions(50)
  }, [fetchSessions])
  
  return {
    sessions,
    isLoading,
    error,
    refresh,
  }
}

export async function deleteSession(sessionId) {
  try {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: 'DELETE',
    })
    
    if (!response.ok) throw new Error('Failed to delete session')
    return true
  } catch (error) {
    console.error('Delete session error:', error)
    return false
  }
}
