import { useEffect, useCallback, useRef, useMemo } from 'react'
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
  
  // Auto-reconnect with exponential backoff + jitter
  useEffect(() => {
    if (!isConnected && sessionId && reconnectAttempts.current < maxReconnectAttempts) {
      // 2s, 4s, 8s, 16s... max 30s + random jitter (0-1000ms)
      const baseDelay = Math.pow(2, reconnectAttempts.current) * 1000
      const jitter = Math.random() * 1000
      const delay = Math.min(baseDelay + jitter, 30000)

      const timer = setTimeout(() => {
        reconnectAttempts.current += 1
        connect(sessionId)
      }, delay)

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
  
  // Memoized event queries to prevent unnecessary re-renders
  const sessionCompleted = useMemo(
    () => events.some(e => e.type === 'session_completed'),
    [events]
  )

  const eventsByType = useMemo(
    () => events.reduce((acc, e) => {
      if (!acc[e.type]) acc[e.type] = []
      acc[e.type].push(e)
      return acc
    }, {}),
    [events]
  )

  return {
    isConnected,
    events,
    agentTokens,
    currentPhase,
    tribunalScores,
    clearEvents,
    getEventsByType,
    getLatestEvent,
    isSessionComplete: sessionCompleted,
    eventsByType,
    reconnectCount: reconnectAttempts.current,
  }
}
