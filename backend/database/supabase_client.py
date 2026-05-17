"""
Synapse Council v2.0 - Supabase Client (memoria-oscar)
Cliente para elevación de veredictos importantes a nube.
"""

import asyncio
from typing import Any

import httpx
import structlog

from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class SupabaseClient:
    """
    Cliente para Supabase (memoria-oscar).
    Eleva veredictos finales para memoria a largo plazo.
    """

    def __init__(self):
        self.enabled = settings.SUPABASE_ENABLED and settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_ANON_KEY
        self.project = settings.SUPABASE_PROJECT
        self._health_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 60  # 1 minute cache
        self._rate_limit_remaining = 1000  # Track for rate limiting
        self._rate_limit_reset = 0
        self._semaphore = asyncio.Semaphore(10)  # Limitar concurrencia

    async def elevate_verdict(
        self,
        session_id: str,
        query: str,
        final_summary: str,
        consensus_level: str,
        tribunal_verdict: dict[str, Any],
        rounds_executed: int,
        config_snapshot: dict[str, Any],
        elevation_reason: str,
    ) -> str | None:
        """
        Eleva veredicto a Supabase (tabla veredictos_finales).
        Retorna ID del veredicto elevado o None si falló.
        """
        if not self.enabled:
            logger.info("supabase.elevation_skipped_disabled", session_id=session_id)
            return None

        try:
            payload = {
                "local_session_id": session_id,
                "query": query,
                "final_summary": final_summary,
                "consensus_level": consensus_level,
                "tribunal_verdict": tribunal_verdict,
                "rounds_executed": rounds_executed,
                "config_snapshot": config_snapshot,
                "elevation_reason": elevation_reason,
                "tags": self._extract_tags(query),
                "is_notable": self._is_notable(tribunal_verdict, consensus_level),
            }

            async with self._semaphore:  # Control de concurrencia
                async with httpx.AsyncClient(
                    timeout=30.0,
                    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                ) as client:
                    response = await client.post(
                        f"{self.url}/rest/v1/veredictos_finales",
                        json=payload,
                        headers={
                            "apikey": self.key,
                            "Authorization": f"Bearer {self.key}",
                            "Content-Type": "application/json",
                            "Prefer": "return=representation",
                        },
                    )

                    if response.status_code in [200, 201]:
                        data = response.json()
                        elevated_id = data[0].get("id") if data else None

                        logger.info(
                            "supabase.elevation_success",
                            session_id=session_id,
                            elevated_id=elevated_id,
                            reason=elevation_reason,
                        )

                        return elevated_id
                    else:
                        logger.error(
                            "supabase.elevation_failed",
                            session_id=session_id,
                            status=response.status_code,
                            response=response.text[:200],
                        )
                        return None

        except Exception as e:
            logger.error("supabase.elevation_error", session_id=session_id, error=str(e))
            return None

    def _extract_tags(self, query: str) -> list:
        """Extrae tags temáticos del query"""
        tags = []
        keywords = {
            "tecnología": ["software", "código", "programación", "ia", "ml", "cloud"],
            "negocio": ["empresa", "estrategia", "mercado", "cliente", "ventas"],
            "legal": ["ley", "normativa", "compliance", "gdpr", "regulación"],
            "ética": ["ético", "moral", "privacidad", "sesgo", "fairness"],
            "infraestructura": ["servidor", "infraestructura", "devops", "deploy"],
        }

        query_lower = query.lower()
        for category, words in keywords.items():
            if any(word in query_lower for word in words):
                tags.append(category)

        return tags[:5]  # Máximo 5 tags

    def _is_notable(self, tribunal_verdict: dict[str, Any], consensus_level: str) -> bool:
        """Determina si el veredicto es notable para destacar"""
        # Notable si: consenso no alcanzado, o score muy alto/bajo
        if consensus_level == "DIVERGENT":
            return True

        if tribunal_verdict:
            evidence_score = tribunal_verdict.get("evidence_score", 0)
            risk_score = tribunal_verdict.get("risk_score", 0)

            # Notable si scores extremos
            if evidence_score > 90 or evidence_score < 30:
                return True
            if risk_score > 90 or risk_score < 30:
                return True

        return False

    async def check_health(self) -> dict[str, Any]:
        """Verifica conectividad con Supabase"""
        if not self.enabled:
            return {"status": "disabled", "message": "Supabase not configured"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.url}/rest/v1/",
                    headers={
                        "apikey": self.key,
                        "Authorization": f"Bearer {self.key}",
                    },
                )

                if response.status_code == 200:
                    return {"status": "online", "url": self.url}
                else:
                    return {
                        "status": "error",
                        "status_code": response.status_code,
                        "message": "Supabase API returned error",
                    }
        except Exception as e:
            return {"status": "offline", "error": str(e)}


# Singleton
supabase_client = SupabaseClient()
