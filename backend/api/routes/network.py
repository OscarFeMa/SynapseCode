"""
Synapse Council v2.0 - Network API
Endpoints para gestión del descubrimiento P2P
"""

from typing import Any

from fastapi import APIRouter

from backend.network.discovery import node_discoverer

router = APIRouter(prefix="/api/v1/network", tags=["network"])


@router.get("/peers")
async def get_peers() -> dict[str, Any]:
    """Obtiene la lista de nodos activos descubiertos en la red local"""
    return {
        "status": "active" if node_discoverer.is_running else "inactive",
        "node_id": node_discoverer.node_id,
        "peers": node_discoverer.get_active_peers(),
        "total_peers": len(node_discoverer.peers),
    }
