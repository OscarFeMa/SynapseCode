"""
Synapse Council v2.0 - Web Search Service
Lanza búsquedas web al inicio de debates para obtener información actualizada.
Los resultados se inyectan como contexto en los prompts de los agentes.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

from backend.adapters.web_agent import SITE_CONFIGS, WebAgentClient
from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


@dataclass
class WebSearchResult:
    """Resultado de una búsqueda web"""

    site: str
    site_label: str
    query: str
    response: str
    success: bool = True
    error: Optional[str] = None


@dataclass
class WebContext:
    """Contexto web completo para un debate"""

    topic: str
    searches: List[WebSearchResult] = field(default_factory=list)
    summary: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "searches": [
                {
                    "site": s.site,
                    "site_label": s.site_label,
                    "query": s.query,
                    "response": s.response,
                    "success": s.success,
                    "error": s.error,
                }
                for s in self.searches
            ],
            "summary": self.summary,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebContext":
        ctx = cls(
            topic=data.get("topic", ""),
            summary=data.get("summary", ""),
            timestamp=data.get("timestamp", ""),
        )
        for s in data.get("searches", []):
            ctx.searches.append(
                WebSearchResult(
                    site=s["site"],
                    site_label=s["site_label"],
                    query=s["query"],
                    response=s["response"],
                    success=s.get("success", True),
                    error=s.get("error"),
                )
            )
        return ctx


class WebSearchService:
    """
    Servicio de búsqueda web para debates.
    - Lanza búsquedas en paralelo al inicio del debate
    - Usa WebAgent (Playwright) para consultar IAs web gratuitas
    - Retorna contexto estructurado para inyectar en prompts
    """

    def __init__(self):
        self._web_agent = None

    @property
    def web_agent(self) -> WebAgentClient:
        if self._web_agent is None:
            self._web_agent = WebAgentClient(
                enabled=settings.WEB_AGENT_ENABLED,
                browser=settings.WEB_AGENT_BROWSER,
                headless=settings.WEB_AGENT_HEADLESS,
            )
        return self._web_agent

    async def search_for_debate(
        self,
        topic: str,
        sites: Optional[List[str]] = None,
        timeout_per_site: int = 60,
    ) -> WebContext:
        """
        Lanza búsquedas web para un tema de debate.

        Args:
            topic: Tema del debate
            sites: Lista de sitios a consultar (default: chatgpt, gemini)
            timeout_per_site: Timeout en segundos por sitio

        Returns:
            WebContext con resultados de búsqueda
        """
        from datetime import UTC, datetime

        if sites is None:
            # Default: usar ChatGPT y Gemini como fuentes principales
            sites = ["chatgpt", "gemini"]

        # Filtrar solo sitios configurados y disponibles
        available_sites = [s for s in sites if s in SITE_CONFIGS]
        if not available_sites:
            logger.warning("web_search.no_available_sites", requested=sites)
            return WebContext(
                topic=topic,
                summary="No hay sitios web disponibles para búsqueda.",
                timestamp=datetime.now(UTC).isoformat(),
            )

        logger.info(
            "web_search.starting",
            topic=topic,
            sites=available_sites,
        )

        # Construir query optimizada para cada sitio
        query = f"Provide a concise, factual summary of: {topic}. Include recent developments, key facts, and current consensus. Be objective and cite sources if possible."

        # Lanzar búsquedas en paralelo
        async def search_one(site: str) -> WebSearchResult:
            try:
                response = await asyncio.wait_for(
                    self.web_agent.query(site, query),
                    timeout=timeout_per_site,
                )
                return WebSearchResult(
                    site=site,
                    site_label=SITE_CONFIGS[site]["label"],
                    query=query,
                    response=response,
                    success=True,
                )
            except asyncio.TimeoutError:
                logger.warning("web_search.timeout", site=site)
                return WebSearchResult(
                    site=site,
                    site_label=SITE_CONFIGS[site]["label"],
                    query=query,
                    response="",
                    success=False,
                    error=f"Timeout after {timeout_per_site}s",
                )
            except Exception as e:
                logger.warning("web_search.error", site=site, error=str(e))
                return WebSearchResult(
                    site=site,
                    site_label=SITE_CONFIGS[site]["label"],
                    query=query,
                    response="",
                    success=False,
                    error=str(e),
                )

        tasks = [search_one(site) for site in available_sites]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Procesar resultados
        search_results = []
        for r in results:
            if isinstance(r, Exception):
                search_results.append(
                    WebSearchResult(
                        site="unknown",
                        site_label="Unknown",
                        query=query,
                        response="",
                        success=False,
                        error=str(r),
                    )
                )
            else:
                search_results.append(r)

        # Generar resumen
        successful = [r for r in search_results if r.success]
        failed = [r for r in search_results if not r.success]

        summary_parts = []
        if successful:
            summary_parts.append(
                f"Búsqueda web completada: {len(successful)} de {len(search_results)} sitios respondieron."
            )
            for r in successful:
                summary_parts.append(f"\n### {r.site_label}")
                # Truncar respuesta para no sobrecargar el prompt
                summary_parts.append(r.response[:2000])
        if failed:
            summary_parts.append(
                f"\nSitios no disponibles: {', '.join(r.site_label for r in failed)}"
            )

        web_context = WebContext(
            topic=topic,
            searches=search_results,
            summary="\n".join(summary_parts),
            timestamp=datetime.now(UTC).isoformat(),
        )

        logger.info(
            "web_search.completed",
            topic=topic,
            successful=len(successful),
            failed=len(failed),
        )

        return web_context

    def format_web_context_for_prompt(self, web_context: WebContext) -> str:
        """
        Formatea el contexto web para inyectar en prompts de agentes.
        """
        if not web_context or not web_context.searches:
            return ""

        sections = [
            "## INFORMACIÓN ACTUALIZADA (Búsqueda Web)",
            f"**Tema:** {web_context.topic}",
            f"**Fecha de búsqueda:** {web_context.timestamp}",
            "",
            "Los siguientes resultados provienen de búsquedas web en tiempo real. "
            "Úsalos como contexto adicional para tu análisis, pero mantén tu pensamiento crítico.",
            "",
        ]

        for result in web_context.searches:
            if result.success:
                sections.append(f"### Fuente: {result.site_label}")
                sections.append(result.response[:3000])  # Limitar a 3000 chars por fuente
                sections.append("")
            else:
                sections.append(f"### Fuente: {result.site_label} (No disponible)")
                sections.append(f"Error: {result.error}")
                sections.append("")

        return "\n".join(sections)

    def format_web_context_for_tribunal(self, web_context: WebContext) -> str:
        """
        Formatea el contexto web específicamente para el tribunal.
        Incluye instrucción de verificación.
        """
        if not web_context or not web_context.searches:
            return ""

        sections = [
            "## INFORMACIÓN WEB PARA VERIFICACIÓN",
            f"**Tema:** {web_context.topic}",
            f"**Fecha de búsqueda:** {web_context.timestamp}",
            "",
            "Los siguientes resultados provienen de búsquedas web en tiempo real. "
            "Tu tarea es VERIFICAR la exactitud de esta información usando tu conocimiento. "
            "Indica si la información web es:",
            "- ✅ CONFIRMADA: Coincide con tu conocimiento",
            "- ⚠️ PARCIALMENTE VÁLIDA: Algunos puntos son correctos, otros no",
            "- ❌ REFUTADA: Contiene errores o información desactualizada",
            "",
        ]

        for result in web_context.searches:
            if result.success:
                sections.append(f"### {result.site_label}")
                sections.append(result.response[:2000])
                sections.append("")

        return "\n".join(sections)


# Singleton
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
