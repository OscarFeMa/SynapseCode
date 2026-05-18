"""
Synapse Council v2.0 - WebSockets
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from backend.api.websocket import handle_websocket, websocket_manager
from backend.config import get_settings

router = APIRouter()


@router.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(default=""),
):
    """WebSocket para streaming en tiempo real de eventos de sesion.
    Requiere token de autenticacion si WS_SECRET_TOKEN esta configurado.
    """
    settings = get_settings()
    ws_secret = getattr(settings, "WS_SECRET_TOKEN", None)

    if ws_secret and token != ws_secret:
        await websocket.accept()
        await websocket.close(code=4003, reason="Invalid token")
        return

    await handle_websocket(websocket, session_id)


@router.get("/api/v1/websocket/stats")
async def websocket_stats():
    """Estadísticas de conexiones WebSocket activas"""
    return websocket_manager.get_all_stats()
