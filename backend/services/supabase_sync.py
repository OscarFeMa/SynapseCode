"""
Synapse Council v2.0 - Supabase Sync Service
Sincronización de debates con Supabase para persistencia en la nube
"""
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class SupabaseSyncService:
    """
    Servicio de sincronización con Supabase.
    Requiere tablas creadas en Supabase:
    - sequential_debates
    - sequential_debate_turns
    """
    
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_ANON_KEY
        self.enabled = settings.SUPABASE_ENABLED and self.url and self.key
        self.client: Optional[httpx.AsyncClient] = None
        
    def _get_client(self) -> httpx.AsyncClient:
        """Obtiene cliente HTTP persistente"""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                headers={
                    "apikey": self.key,
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                timeout=30.0
            )
        return self.client
    
    async def test_connection(self) -> Dict[str, Any]:
        """Prueba conexión con Supabase"""
        if not self.enabled:
            return {"status": "disabled", "message": "Supabase not configured"}
        
        try:
            client = self._get_client()
            # Intentar obtener datos de la tabla sequential_debates
            response = await client.get(
                f"{self.url}/rest/v1/sequential_debates?select=id&limit=1"
            )
            
            if response.status_code in [200, 404]:  # 404 = tabla existe pero vacía
                return {
                    "status": "connected",
                    "url": self.url,
                    "tables_accessible": True
                }
            else:
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "message": response.text
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def sync_debate(self, debate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincroniza un debate completo con Supabase.
        
        Args:
            debate_data: Dict con toda la información del debate
            
        Returns:
            Dict con resultado de la sincronización
        """
        if not self.enabled:
            return {"synced": False, "reason": "Supabase not enabled"}
        
        debate_id = debate_data.get('id')
        
        try:
            client = self._get_client()
            
            # 1. Insertar/Actualizar debate principal
            debate_record = {
                "id": debate_id,
                "topic": debate_data.get('topic'),
                "mode": debate_data.get('mode', 'standard'),
                "status": debate_data.get('status', 'completed'),
                "total_turns": debate_data.get('total_turns', 0),
                "total_tokens_in": debate_data.get('total_tokens_in', 0),
                "total_tokens_out": debate_data.get('total_tokens_out', 0),
                "total_latency_ms": debate_data.get('total_latency_ms', 0),
                "final_verdict": debate_data.get('final_verdict'),
                "transcript_path": debate_data.get('transcript_path'),
                "created_at": debate_data.get('created_at', datetime.utcnow()).isoformat() if isinstance(debate_data.get('created_at'), datetime) else debate_data.get('created_at'),
                "completed_at": debate_data.get('completed_at', datetime.utcnow()).isoformat() if isinstance(debate_data.get('completed_at'), datetime) else debate_data.get('completed_at'),
                "synced_at": datetime.utcnow().isoformat()
            }
            
            # Upsert debate (insertar o actualizar)
            response = await client.post(
                f"{self.url}/rest/v1/sequential_debates",
                json=debate_record,
                headers={"Prefer": "resolution=merge-duplicates"}
            )
            
            if response.status_code not in [200, 201, 204]:
                logger.error("supabase_sync.debate_failed",
                            debate_id=debate_id,
                            status=response.status_code,
                            error=response.text)
                return {"synced": False, "error": response.text}
            
            # 2. Insertar/Actualizar turns
            turns = debate_data.get('turns', [])
            for turn in turns:
                import uuid
                # Generar UUID determinista para el turno (debate_id + turn_number)
                turn_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{debate_id}_turn_{turn.get('turn_number')}"))
                
                turn_record = {
                    "id": turn_uuid,
                    "debate_id": debate_id,
                    "turn_number": turn.get('turn_number'),
                    "agent_id": turn.get('agent_id', 'unknown'),
                    "agent_name": turn.get('agent_name'),
                    "agent_role": turn.get('agent_role', 'analyst'),  # Valor por defecto para evitar null
                    "model": turn.get('model'),
                    "provider": turn.get('provider') or 'unknown',
                    "node": turn.get('node', 'LOCAL'),
                    "engine": turn.get('engine', 'ollama'),
                    "prompt_sent": turn.get('prompt_sent', '')[:10000],  # Limitar tamaño
                    "response_received": turn.get('response_received', '')[:20000],  # Limitar
                    "tokens_in": turn.get('tokens_in', 0),
                    "tokens_out": turn.get('tokens_out', 0),
                    "latency_ms": turn.get('latency_ms', 0),
                    "status": turn.get('status', 'completed'),
                    "error_message": turn.get('error_message'),
                    "started_at": turn.get('started_at', datetime.utcnow()).isoformat() if isinstance(turn.get('started_at'), datetime) else turn.get('started_at'),
                    "completed_at": turn.get('completed_at', datetime.utcnow()).isoformat() if isinstance(turn.get('completed_at'), datetime) else turn.get('completed_at')
                }
                
                turn_response = await client.post(
                    f"{self.url}/rest/v1/sequential_debate_turns",
                    json=turn_record,
                    headers={"Prefer": "resolution=merge-duplicates"}
                )
                
                if turn_response.status_code not in [200, 201, 204]:
                    logger.warning("supabase_sync.turn_failed",
                                debate_id=debate_id,
                                turn=turn.get('turn_number'),
                                status=turn_response.status_code,
                                error=turn_response.text[:500])
            
            logger.info("supabase_sync.success",
                       debate_id=debate_id,
                       turns_synced=len(turns))
            
            return {
                "synced": True,
                "debate_id": debate_id,
                "turns_synced": len(turns),
                "supabase_url": f"{self.url}/rest/v1/sequential_debates?id=eq.{debate_id}"
            }
            
        except Exception as e:
            logger.error("supabase_sync.exception",
                        debate_id=debate_id,
                        error=str(e))
            return {"synced": False, "error": str(e)}
    
    async def sync_consensus_debate(self, debate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincroniza un debate de consenso con Supabase.
        Requiere tabla 'consensus_debates' en Supabase.
        """
        if not self.enabled:
            return {"synced": False, "reason": "supabase_not_enabled"}
        
        debate_id = debate_data.get('id')
        
        try:
            client = self._get_client()
            
            # Preparar registro de debate de consenso
            debate_record = {
                "id": debate_id,
                "topic": debate_data.get('topic'),
                "status": debate_data.get('status', 'unknown'),
                "total_agents": debate_data.get('total_agents', 0),
                "max_rounds": debate_data.get('max_rounds', 5),
                "consensus_score": debate_data.get('consensus_score'),
                "final_consensus": debate_data.get('final_consensus', '')[:30000] if debate_data.get('final_consensus') else None,
                "bias_analysis": debate_data.get('bias_analysis'),
                "transcript_path": debate_data.get('transcript_path'),
                "total_tokens_in": debate_data.get('total_tokens_in', 0),
                "total_tokens_out": debate_data.get('total_tokens_out', 0),
                "total_latency_ms": debate_data.get('total_latency_ms', 0),
                "created_at": debate_data.get('created_at', datetime.utcnow()).isoformat() if isinstance(debate_data.get('created_at'), datetime) else debate_data.get('created_at'),
                "completed_at": debate_data.get('completed_at', datetime.utcnow()).isoformat() if isinstance(debate_data.get('completed_at'), datetime) else debate_data.get('completed_at'),
                "synced_at": datetime.utcnow().isoformat()
            }
            
            # Upsert debate de consenso
            response = await client.post(
                f"{self.url}/rest/v1/consensus_debates",
                json=debate_record,
                headers={"Prefer": "resolution=merge-duplicates"}
            )
            
            if response.status_code not in [200, 201, 204]:
                logger.error("supabase_sync.consensus_debate_failed",
                            debate_id=debate_id,
                            status=response.status_code,
                            error=response.text)
                return {"synced": False, "error": response.text}
            
            # Sincronizar rondas
            rounds = debate_data.get('rounds', [])
            for round_data in rounds:
                round_record = {
                    "debate_id": debate_id,
                    "round_number": round_data.get('round_number'),
                    "round_type": round_data.get('round_type'),
                    "global_consensus_score": round_data.get('global_consensus_score'),
                    "converged": round_data.get('converged', False),
                    "dissent_topics": round_data.get('dissent_topics', []),
                    "synced_at": datetime.utcnow().isoformat()
                }
                
                round_response = await client.post(
                    f"{self.url}/rest/v1/consensus_rounds",
                    json=round_record,
                    headers={"Prefer": "resolution=merge-duplicates"}
                )
                
                if round_response.status_code not in [200, 201, 204]:
                    logger.warning("supabase_sync.consensus_round_failed",
                                debate_id=debate_id,
                                round=round_data.get('round_number'),
                                status=round_response.status_code)
            
            # Sincronizar posiciones de agentes
            agent_positions = debate_data.get('agent_positions', [])
            for position in agent_positions:
                position_record = {
                    "debate_id": debate_id,
                    "round_number": position.get('round_number'),
                    "agent_id": position.get('agent_id'),
                    "agent_name": position.get('agent_name'),
                    "agent_role": position.get('agent_role'),
                    "position_text": position.get('position_text', '')[:15000],
                    "confidence": position.get('confidence', 0),
                    "consensus_score": position.get('consensus_score', 0),
                    "supporting_points": position.get('supporting_points', []),
                    "objections_raised": position.get('objections_raised', []),
                    "logical_fallacies": position.get('logical_fallacies', []),
                    "synced_at": datetime.utcnow().isoformat()
                }
                
                pos_response = await client.post(
                    f"{self.url}/rest/v1/consensus_agent_positions",
                    json=position_record,
                    headers={"Prefer": "resolution=merge-duplicates"}
                )
                
                if pos_response.status_code not in [200, 201, 204]:
                    logger.warning("supabase_sync.consensus_position_failed",
                                debate_id=debate_id,
                                agent=position.get('agent_name'),
                                status=pos_response.status_code)
            
            logger.info("supabase_sync.consensus_success",
                       debate_id=debate_id,
                       rounds_synced=len(rounds),
                       positions_synced=len(agent_positions))
            
            return {
                "synced": True,
                "debate_id": debate_id,
                "rounds_synced": len(rounds),
                "positions_synced": len(agent_positions),
                "supabase_url": f"{self.url}/rest/v1/consensus_debates?id=eq.{debate_id}"
            }
            
        except Exception as e:
            logger.error("supabase_sync.consensus_exception",
                        debate_id=debate_id,
                        error=str(e))
            return {"synced": False, "error": str(e)}
    
    async def get_debate_from_cloud(self, debate_id: str) -> Optional[Dict[str, Any]]:
        """Recupera un debate desde Supabase"""
        if not self.enabled:
            return None
        
        try:
            client = self._get_client()
            
            # Obtener debate
            response = await client.get(
                f"{self.url}/rest/v1/sequential_debates?id=eq.{debate_id}"
            )
            
            if response.status_code != 200:
                return None
            
            debates = response.json()
            if not debates:
                return None
            
            debate = debates[0]
            
            # Obtener turns
            turns_response = await client.get(
                f"{self.url}/rest/v1/sequential_debate_turns?debate_id=eq.{debate_id}&order=turn_number.asc"
            )
            
            if turns_response.status_code == 200:
                debate['turns'] = turns_response.json()
            else:
                debate['turns'] = []
            
            return debate
            
        except Exception as e:
            logger.error("supabase_sync.get_failed",
                        debate_id=debate_id,
                        error=str(e))
            return None
    
    async def list_debates_from_cloud(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista debates desde Supabase"""
        if not self.enabled:
            return []
        
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.url}/rest/v1/sequential_debates?select=*&order=created_at.desc&limit={limit}"
            )
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception as e:
            logger.error("supabase_sync.list_failed", error=str(e))
            return []
    
    async def close(self):
        """Cierra conexión HTTP"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()


# Singleton instance
_supabase_service: Optional[SupabaseSyncService] = None


def get_supabase_service() -> SupabaseSyncService:
    """Obtiene instancia singleton del servicio"""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseSyncService()
    return _supabase_service
