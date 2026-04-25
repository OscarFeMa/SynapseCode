"""
Synapse Council v2.0 - WebSockets
"""
from fastapi import APIRouter, WebSocket
from backend.api.websocket import handle_websocket, websocket_manager

router = APIRouter()

@router.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket para streaming en tiempo real de eventos de sesión."""
    await handle_websocket(websocket, session_id)

@router.get("/api/v1/websocket/stats")
async def websocket_stats():
    """Estadísticas de conexiones WebSocket activas"""
    return websocket_manager.get_all_stats()
