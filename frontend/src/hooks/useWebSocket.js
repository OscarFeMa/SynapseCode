import { useEffect, useCallback, useRef } from 'react'
import { useWebSocketStore } from '../store/useStore'

export function useWebSocket(sessionId) {
  const {
    isConnected,
    connect,
    disconnect,
    events,
    agentTokens,
    currentPhase,
    tribunalScores,
    clearEvents,
  } = useWebSocketStore()
  
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 3
  
  // Connect on mount
  useEffect(() => {
    if (sessionId && !isConnected) {
      connect(sessionId)
    }
    
    return () => {
      if (isConnected) {
        disconnect()
      }
    }
  }, [sessionId, connect, disconnect, isConnected])
  
  // Auto-reconnect logic
  useEffect(() => {
    if (!isConnected && sessionId && reconnectAttempts.current < maxReconnectAttempts) {
      const timer = setTimeout(() => {
        reconnectAttempts.current += 1
        connect(sessionId)
      }, 2000)
      
      return () => clearTimeout(timer)
    }
  }, [isConnected, sessionId, connect])
  
  // Reset reconnect counter on successful connection
  useEffect(() => {
    if (isConnected) {
      reconnectAttempts.current = 0
    }
  }, [isConnected])
  
  // Get latest events by type
  const getEventsByType = useCallback((type) => {
    return events.filter(e => e.type === type)
  }, [events])
  
  // Get latest event of specific type
  const getLatestEvent = useCallback((type) => {
    const filtered = events.filter(e => e.type === type)
    return filtered[filtered.length - 1] || null
  }, [events])
  
  // Check if session is complete
  const isSessionComplete = events.some(e => e.type === 'session_completed')
  
  return {
    isConnected,
    events,
    agentTokens,
    currentPhase,
    tribunalScores,
    clearEvents,
    getEventsByType,
    getLatestEvent,
    isSessionComplete,
    reconnectCount: reconnectAttempts.current,
  }
}
