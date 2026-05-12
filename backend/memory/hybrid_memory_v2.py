"""
Hybrid Memory V2 - Sistema de memoria híbrida con cola async.
SQLite local (primario) + Supabase (background async).
Si Supabase falla, el sistema continúa sin interrupciones.
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import structlog

from backend.services.supabase_sync import get_supabase_service

logger = structlog.get_logger()


class HybridMemoryV2:
    """
    Memoria híbrida con patrón "fire and forget" para Supabase.
    - SQLite: Siempre disponible, sincrónico, garantizado
    - Supabase: Async en background, no bloquea, opcional
    """
    
    def __init__(self):
        self.supabase = get_supabase_service()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._enabled: bool = self.supabase.enabled
        self._stats = {
            'queued': 0,
            'synced': 0,
            'failed': 0
        }
    
    async def start(self) -> None:
        """Inicia el worker de sincronización."""
        if self._enabled and self._task is None:
            self._task = asyncio.create_task(self._worker())
            logger.info("hybrid_memory_v2.started")
    
    async def stop(self, timeout: float = 5.0) -> None:
        """Detiene el worker de forma graceful."""
        if self._task:
            try:
                # Esperar a que se procese la cola actual
                await asyncio.wait_for(self._queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("hybrid_memory_v2.stop_timeout", 
                             pending=self._queue.qsize())
            
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            
            logger.info("hybrid_memory_v2.stopped", stats=self._stats)
    
    async def enqueue_sync(
        self,
        session,
        session_id: str,
        mode: str
    ) -> None:
        """
        Encola datos para sincronización con Supabase.
        Nunca lanza excepción al caller.
        """
        if not self._enabled:
            return  # Supabase no configurado, salir silenciosamente
        
        try:
            data = self._build_data(session, session_id, mode)
            await self._queue.put(('debate', data))
            self._stats['queued'] += 1
        except Exception as e:
            # Silencioso - no crítico
            logger.debug("hybrid_memory_v2.enqueue_failed", error=str(e))
    
    async def _worker(self) -> None:
        """
        Worker que procesa la cola de sincronización.
        Si Supabase falla, solo loguea y continúa.
        """
        while True:
            try:
                # Esperar item con timeout para poder verificar cancellation
                kind, data = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=30.0
                )
                
                try:
                    if kind == 'debate':
                        await self.supabase.sync_debate(data)
                        self._stats['synced'] += 1
                        logger.debug("hybrid_memory_v2.synced",
                                   session_id=data.get('id'))
                except Exception as e:
                    # Silencioso - SQLite ya tiene los datos
                    self._stats['failed'] += 1
                    logger.debug("hybrid_memory_v2.sync_failed",
                               session_id=data.get('id'),
                               error=str(e))
                finally:
                    self._queue.task_done()
                    
            except asyncio.TimeoutError:
                # Normal, continuar loop
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("hybrid_memory_v2.worker_error", error=str(e))
                await asyncio.sleep(1)  # Evitar spam de errores
    
    def _build_data(
        self,
        session,
        session_id: str,
        mode: str
    ) -> Dict[str, Any]:
        """Construye payload para Supabase."""
        return {
            'id': session_id,
            'topic': getattr(session, 'topic', ''),
            'mode': mode,
            'status': getattr(session, 'status', ''),
            'final_verdict': getattr(session, 'final_verdict', None),
            'total_tokens_out': sum(
                getattr(t, 'tokens_out', 0)
                for t in getattr(session, 'turns', [])
            ),
            'total_latency_ms': sum(
                getattr(t, 'latency_ms', 0)
                for t in getattr(session, 'turns', [])
            ),
            'turns': [
                {
                    'id': f"{session_id}_turn_{t.turn_number}",
                    'debate_id': session_id,
                    'turn_number': t.turn_number,
                    'agent_name': getattr(getattr(t, 'agent', None), 'name', 'unknown'),
                    'model': getattr(getattr(t, 'agent', None), 'model', 'unknown'),
                    'intervention_type': getattr(t, 'intervention_type', 'desconocido'),
                    'response_received': getattr(t, 'response_received', '')[:15000],
                    'tokens_out': getattr(t, 'tokens_out', 0),
                    'latency_ms': getattr(t, 'latency_ms', 0),
                }
                for t in getattr(session, 'turns', [])
            ]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de sincronización."""
        return {
            'enabled': self._enabled,
            'queue_size': self._queue.qsize(),
            **self._stats
        }


# Instancia global
hybrid_memory_v2: Optional[HybridMemoryV2] = None


def get_hybrid_memory_v2() -> HybridMemoryV2:
    """Factory para instancia singleton."""
    global hybrid_memory_v2
    if hybrid_memory_v2 is None:
        hybrid_memory_v2 = HybridMemoryV2()
    return hybrid_memory_v2
