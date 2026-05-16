"""
Synapse Council v2.0 - WebSocket Manager
Gestiona conexiones WebSocket y streaming de eventos en tiempo real
"""
import asyncio
import json
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
import structlog

from fastapi import WebSocket, WebSocketDisconnect

from backend.engine.task_manager import task_manager

logger = structlog.get_logger()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class WebSocketEvent:
    """Evento para transmitir por WebSocket"""
    type: str
    session_id: str
    timestamp: str
    payload: Dict[str, Any]
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "payload": self.payload
        }, default=str)


class WebSocketManager:
    """
    Gestor central de conexiones WebSocket.
    Mantiene registro de conexiones activas por sesión.
    """
    
    def __init__(self):
        # session_id -> set de WebSockets conectados
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Callbacks para eventos globales (opcional)
        self.event_callbacks: Dict[str, list] = {}
        # Referencias fuertes para evitar Garbage Collection de tareas asíncronas
        self.background_tasks: Set[asyncio.Task] = set()
        # Buffer de token streaming por sesión/evento/rol
        self.token_buffers: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.token_flush_delay_seconds: float = 0.05
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Acepta y registra nueva conexión WebSocket"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        
        logger.info(
            "websocket.connected",
            session_id=session_id,
            total_connections=len(self.active_connections[session_id]),
        )
        
        # Enviar mensaje de confirmación
        await self.send_event(
            session_id=session_id,
            event_type="connection_established",
            payload={
                "message": "Connected to Synapse Council v2.0",
                "session_id": session_id,
                "timestamp": utc_now_iso()
            },
            target=websocket
        )
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Desregistra conexión WebSocket"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            
            # Limpiar si no quedan conexiones
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        
        logger.info(
            "websocket.disconnected",
            session_id=session_id,
            remaining=len(self.active_connections.get(session_id, set())),
        )
    
    async def send_event(
        self,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
        target: Optional[WebSocket] = None
    ):
        """
        Envía evento a cliente(s).
        Si target es None, envía a todos los conectados a la sesión.
        """
        if target is None and self._should_buffer_token_event(event_type, payload):
            await self._buffer_token_event(session_id, event_type, payload)
            return

        event = WebSocketEvent(
            type=event_type,
            session_id=session_id,
            timestamp=utc_now_iso(),
            payload=payload
        )
        
        message = event.to_json()
        
        if target:
            # Enviar a cliente específico
            try:
                await target.send_text(message)
            except Exception as e:
                logger.warning(
                    "websocket.send_failed",
                    session_id=session_id,
                    error=str(e)
                )
        else:
            # Broadcast a todos en la sesión
            if session_id in self.active_connections:
                disconnected = []
                for conn in self.active_connections[session_id]:
                    try:
                        await conn.send_text(message)
                    except Exception as e:
                        logger.warning(
                            "websocket.broadcast_failed",
                            session_id=session_id,
                            error=str(e)
                        )
                        disconnected.append(conn)
                
                # Limpiar conexiones fallidas
                for conn in disconnected:
                    self.active_connections[session_id].discard(conn)

    def _should_buffer_token_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        return event_type.endswith("_token") and isinstance(payload.get("token"), str)

    async def _buffer_token_event(self, session_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        role = str(payload.get("role", "default"))
        session_buffers = self.token_buffers.setdefault(session_id, {})
        buffer_key = f"{event_type}:{role}"
        buffer_entry = session_buffers.get(buffer_key)

        if buffer_entry is None:
            buffer_entry = {
                "event_type": event_type,
                "role": role,
                "token": "",
                "token_count": 0,
                "task": None,
            }
            session_buffers[buffer_key] = buffer_entry

        buffer_entry["token"] += payload.get("token", "")
        buffer_entry["token_count"] += 1

        if buffer_entry["task"] is None or buffer_entry["task"].done():
            async def delayed_flush():
                try:
                    await asyncio.sleep(self.token_flush_delay_seconds)
                    await self.flush_session(session_id)
                except Exception as e:
                    logger.debug("websocket.token_flush_failed", session_id=session_id, error=str(e))

            task = asyncio.create_task(delayed_flush())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)
            buffer_entry["task"] = task

    async def flush_session(self, session_id: str) -> None:
        session_buffers = self.token_buffers.get(session_id, {})
        if not session_buffers:
            return

        buffered_items = list(session_buffers.items())
        self.token_buffers[session_id] = {}

        for _, buffer_entry in buffered_items:
            task = buffer_entry.get("task")
            if task and not task.done():
                task.cancel()

            await self._send_raw_event(
                session_id=session_id,
                event_type=f"{buffer_entry['event_type']}_batch",
                payload={
                    "role": buffer_entry["role"],
                    "token": buffer_entry["token"],
                    "token_count": buffer_entry["token_count"],
                },
            )

        if not self.token_buffers[session_id]:
            del self.token_buffers[session_id]

    async def _send_raw_event(
        self,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
        target: Optional[WebSocket] = None,
    ) -> None:
        event = WebSocketEvent(
            type=event_type,
            session_id=session_id,
            timestamp=utc_now_iso(),
            payload=payload
        )

        message = event.to_json()

        if target:
            try:
                await target.send_text(message)
            except Exception as e:
                logger.warning(
                    "websocket.send_failed",
                    session_id=session_id,
                    error=str(e)
                )
            return

        if session_id in self.active_connections:
            disconnected = []
            for conn in self.active_connections[session_id]:
                try:
                    await conn.send_text(message)
                except Exception as e:
                    logger.warning(
                        "websocket.broadcast_failed",
                        session_id=session_id,
                        error=str(e)
                    )
                    disconnected.append(conn)

            for conn in disconnected:
                self.active_connections[session_id].discard(conn)
    
    async def broadcast_to_all(self, event_type: str, payload: Dict[str, Any]):
        """Broadcast a TODAS las sesiones (uso con cautela)"""
        for session_id in list(self.active_connections.keys()):
            await self.send_event(session_id, event_type, payload)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Obtiene estadísticas de conexiones para una sesión"""
        connections = self.active_connections.get(session_id, set())
        return {
            "session_id": session_id,
            "active_connections": len(connections),
            "connected": len(connections) > 0
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas globales de WebSockets"""
        return {
            "total_sessions": len(self.active_connections),
            "total_connections": sum(
                len(conns) for conns in self.active_connections.values()
            ),
            "sessions": {
                sid: len(conns)
                for sid, conns in self.active_connections.items()
            }
        }
    
    def create_event_callback(self, session_id: str) -> Callable[[str, Any], None]:
        """
        Crea callback para el Session Manager.
        Retorna función que puede llamarse asíncronamente desde el motor.
        """
        def callback(event_type: str, payload: Dict[str, Any]):
            # Usar task_manager para mejor manejo de errores y métricas
            # Nota: task_manager.submit requiere await, pero este callback es sync
            # Creamos task manualmente pero con mejor gestión de errores
            async def send_with_error_handling():
                try:
                    await self.send_event(session_id, event_type, payload)
                except Exception as e:
                    logger.debug("websocket.send_failed", session_id=session_id, error=str(e))
            
            task = asyncio.create_task(send_with_error_handling())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)
        
        return callback


# Singleton global
websocket_manager = WebSocketManager()


async def handle_websocket(websocket: WebSocket, session_id: str):
    """
    Handler principal para endpoint WebSocket.
    Usar en FastAPI: @app.websocket("/ws/sessions/{session_id}")
    """
    await websocket_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Recibir mensajes del cliente (comandos, heartbeat, etc.) con timeout
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)
            except asyncio.TimeoutError:
                logger.warning("websocket.timeout_closing", session_id=session_id)
                break
            
            try:
                message = json.loads(data)
                msg_type = message.get("type", "unknown")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": utc_now_iso()})
                
                elif msg_type == "get_status":
                    await websocket_manager.flush_session(session_id)
                    stats = websocket_manager.get_session_stats(session_id)
                    await websocket.send_json({"type": "status", "data": stats})
                
                else:
                    # Echo para otros tipos
                    await websocket.send_json({
                        "type": "ack",
                        "received_type": msg_type,
                        "timestamp": utc_now_iso()
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    except WebSocketDisconnect:
        logger.info("websocket.disconnected_clean", session_id=session_id)
    except Exception as e:
        logger.error("websocket.error", session_id=session_id, error=str(e))
    finally:
        await websocket_manager.flush_session(session_id)
        websocket_manager.disconnect(websocket, session_id)
