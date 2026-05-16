"""
Synapse Council v2.0 - Sessions API
"""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.websocket import websocket_manager
from backend.database.local_db import AsyncSessionLocal
from backend.database.local_db import get_session as get_db_session
from backend.database.models import Session as SessionModel
from backend.engine.session_manager import SessionManager

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
session_manager = SessionManager()


class CreateSessionRequest(BaseModel):
    query: str
    title: Optional[str] = None
    max_rounds: Optional[int] = 1


class SessionResponse(BaseModel):
    session_id: str
    status: str
    query: str
    message: str


class SessionDetailResponse(BaseModel):
    session: Dict[str, Any]
    rounds: List[Dict[str, Any]]
    agent_calls: Dict[str, List[Dict[str, Any]]]


@router.post("", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Crea una nueva sesión de debate y la ejecuta en background
    """
    try:
        session = await session_manager.create_session(
            query=request.query,
            db_session=db_session,
            title=request.title,
            max_rounds=request.max_rounds,
        )

        async def run_session_async(session_id: str):
            try:
                async with AsyncSessionLocal() as new_session:
                    try:
                        ws_callback = websocket_manager.create_event_callback(session_id)
                        await session_manager.run_session(
                            session_id=session_id,
                            db_session=new_session,
                            on_event=ws_callback,
                        )
                    except Exception as e:
                        logger.error(
                            "background_session_failed",
                            session_id=session_id,
                            error=str(e),
                        )
                        await websocket_manager.send_event(
                            session_id=session_id,
                            event_type="session_error",
                            payload={"error": str(e)},
                        )
            except Exception as outer_e:
                logger.error(
                    "background_task_critical_failure",
                    session_id=session_id,
                    error=str(outer_e),
                )
                # Fallback sin depender de la DB (al menos notificar por websocket)
                await websocket_manager.send_event(
                    session_id=session_id,
                    event_type="session_error",
                    payload={"error": f"Critical failure: {str(outer_e)}"},
                )

        background_tasks.add_task(run_session_async, session.id)

        return SessionResponse(
            session_id=session.id,
            status=session.status,
            query=request.query,
            message=f"Session created and running. Check GET /api/v1/sessions/{session.id} for results.",
        )

    except Exception as e:
        logger.error("create_session_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str, db_session: AsyncSession = Depends(get_db_session)):
    """Obtiene el detalle completo de una sesión"""
    detail = await session_manager.get_session_detail(session_id, db_session)

    if not detail:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionDetailResponse(**detail)


@router.get("")
async def list_sessions(
    status: Optional[str] = None,
    limit: int = 50,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Lista sesiones con filtro opcional por estado"""
    sessions = await session_manager.list_sessions(db_session=db_session, status=status, limit=limit)

    return {"sessions": sessions, "count": len(sessions)}


@router.delete("/{session_id}")
async def delete_session(session_id: str, db_session: AsyncSession = Depends(get_db_session)):
    """Elimina una sesión (solo si está completada o fallida)"""
    result = await db_session.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "RUNNING":
        raise HTTPException(status_code=400, detail="Cannot delete running session")

    await db_session.execute(delete(SessionModel).where(SessionModel.id == session_id))
    await db_session.commit()

    return {"message": f"Session {session_id} deleted"}
