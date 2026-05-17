"""
Synapse Council - Unified Runs API
Read-only compatibility layer across classic sessions and sequential debates.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.routes.debate import debate_controller, ultra_controller
from backend.database.local_db import get_session as get_db_session
from backend.engine.session_manager import SessionManager

router = APIRouter(prefix="/runs", tags=["Runs"])
session_manager = SessionManager()


def _normalize_sequential_summary(debate: dict[str, Any], source: str = "database") -> dict[str, Any]:
    return {
        "id": debate.get("id") or debate.get("session_id"),
        "type": "sequential_debate",
        "source": source,
        "title": debate.get("topic"),
        "query": debate.get("topic"),
        "status": debate.get("status"),
        "mode": debate.get("mode", "standard"),
        "steps_executed": debate.get("total_turns", 0),
        "total_tokens_in": debate.get("total_tokens_in", 0),
        "total_tokens_out": debate.get("total_tokens_out", 0),
        "created_at": debate.get("created_at"),
        "completed_at": debate.get("completed_at"),
    }


def _normalize_classic_summary(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": session.get("id"),
        "type": "classic_session",
        "source": "database",
        "title": session.get("title"),
        "query": session.get("query"),
        "status": session.get("status"),
        "mode": "classic",
        "steps_executed": session.get("rounds_executed", 0),
        "consensus_level": session.get("consensus_level"),
        "created_at": session.get("created_at"),
        "completed_at": session.get("completed_at"),
    }


def _normalize_active_session(session: Any, run_type: str) -> dict[str, Any]:
    turns = getattr(session, "turns", []) or []
    completed_turns = [turn for turn in turns if getattr(turn, "status", None) == "completed"]
    return {
        "id": getattr(session, "id", None),
        "type": run_type,
        "source": "memory",
        "title": getattr(session, "topic", None),
        "query": getattr(session, "topic", None),
        "status": getattr(session, "status", None),
        "mode": getattr(session, "mode", run_type),
        "steps_executed": len(completed_turns),
        "total_tokens_in": sum(getattr(turn, "tokens_in", 0) for turn in turns),
        "total_tokens_out": sum(getattr(turn, "tokens_out", 0) for turn in turns),
        "created_at": getattr(session, "created_at", None),
        "completed_at": getattr(session, "completed_at", None),
    }


@router.get("")
async def list_runs(
    limit: int = 50,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Lista ejecuciones de debate con un contrato comun minimo."""
    runs: list[dict[str, Any]] = []

    for session in debate_controller.list_sessions():
        runs.append(_normalize_active_session(session, "sequential_debate"))

    for session in ultra_controller.active_sessions.values():
        runs.append(_normalize_active_session(session, "ultra_debate"))

    sequential = await debate_controller.list_debates_from_db(limit=limit)
    runs.extend(_normalize_sequential_summary(debate) for debate in sequential)

    classic = await session_manager.list_sessions(db_session=db_session, limit=limit)
    runs.extend(_normalize_classic_summary(session) for session in classic)

    runs.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {"runs": runs[:limit], "count": min(len(runs), limit)}


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Obtiene una ejecucion por ID desde memoria o base de datos."""
    active = debate_controller.get_session(run_id)
    if active:
        return {
            "run": _normalize_active_session(active, "sequential_debate"),
            "detail": active,
        }

    ultra = ultra_controller.active_sessions.get(run_id)
    if ultra:
        return {
            "run": _normalize_active_session(ultra, "ultra_debate"),
            "detail": ultra,
        }

    sequential = await debate_controller.get_debate_from_db(run_id)
    if sequential:
        return {
            "run": _normalize_sequential_summary(sequential),
            "detail": sequential,
        }

    classic = await session_manager.get_session_detail(run_id, db_session)
    if classic:
        return {
            "run": _normalize_classic_summary(classic["session"]),
            "detail": classic,
        }

    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
