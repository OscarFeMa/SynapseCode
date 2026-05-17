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
            sites: Lista de sitios a consultar (default: wikipedia, duckduckgo)
            timeout_per_site: Timeout en segundos por sitio

        Returns:
            WebContext con resultados de búsqueda
        """
        from datetime import UTC, datetime

        if sites is None:
            # Default: usar DuckDuckGo search (resultados reales, sin API key)
            sites = ["duckduckgo_search"]

        # Filtrar solo sitios configurados y disponibles
        available_sites = [s for s in sites if s in SITE_CONFIGS or s == "duckduckgo_search"]
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
        # DuckDuckGo search funciona mejor con queries cortas y directas
        query_ddg = topic
        # WebAgent queries son más elaborados (para IAs conversacionales)
        query_web_agent = f"Provide a concise, factual summary of: {topic}. Include recent developments, key facts, and current consensus. Be objective and cite sources if possible."

        # Lanzar búsquedas en paralelo
        async def search_one(site: str) -> WebSearchResult:
            # DuckDuckGo search via library (real-time results, no browser)
            if site == "duckduckgo_search":
                return await self._search_duckduckgo(topic, query_ddg)

            # Browser-based search (Playwright)
            if site not in SITE_CONFIGS:
                return WebSearchResult(
                    site=site,
                    site_label=site,
                    query=query_ddg,
                    response="",
                    success=False,
                    error=f"Unknown site: {site}",
                )

            try:
                response = await asyncio.wait_for(
                    self.web_agent.query(site, query_web_agent),
                    timeout=timeout_per_site,
                )
                return WebSearchResult(
                    site=site,
                    site_label=SITE_CONFIGS[site]["label"],
                    query=query_web_agent,
                    response=response,
                    success=True,
                )
            except asyncio.TimeoutError:
                logger.warning("web_search.timeout", site=site)
                return WebSearchResult(
                    site=site,
                    site_label=SITE_CONFIGS[site]["label"],
                    query=query_web_agent,
                    response="",
                    success=False,
                    error=f"Timeout after {timeout_per_site}s",
                )
            except Exception as e:
                logger.warning("web_search.error", site=site, error=str(e))
                return WebSearchResult(
                    site=site,
                    site_label=SITE_CONFIGS[site]["label"],
                    query=query_web_agent,
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
                        query=topic,
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

    async def _search_duckduckgo(
        self,
        topic: str,
        query: str,
    ) -> WebSearchResult:
        """Busqueda en tiempo real via DuckDuckGo + trafilatura para contenido completo"""
        try:
            from ddgs import DDGS

            loop = asyncio.get_event_loop()

            # Paso 1: Buscar URLs en DuckDuckGo
            results = await loop.run_in_executor(
                None,
                lambda: DDGS().text(query, max_results=8),
            )

            if not results:
                return WebSearchResult(
                    site="duckduckgo_search",
                    site_label="DuckDuckGo Search",
                    query=query,
                    response="",
                    success=False,
                    error="No results found",
                )

            # Paso 2: Extraer contenido limpio de las top 3 URLs con trafilatura
            import trafilatura

            urls_to_fetch = []
            for r in results[:8]:
                url = r.get("href", "")
                title = r.get("title", "")
                body = r.get("body", "")
                if url:
                    urls_to_fetch.append({"url": url, "title": title, "snippet": body})

            # Fetch y extraer contenido de las top 3 URLs en paralelo
            async def fetch_url(item: dict) -> dict:
                url = item["url"]
                try:
                    downloaded = await loop.run_in_executor(
                        None,
                        lambda: trafilatura.fetch_url(url),
                    )
                    if downloaded:
                        content = await loop.run_in_executor(
                            None,
                            lambda: trafilatura.extract(
                                downloaded,
                                include_comments=False,
                                include_tables=True,
                            ),
                        )
                        if content and len(content) > 100:
                            return {
                                "url": url,
                                "title": item["title"],
                                "content": content[:2000],
                                "snippet": item["snippet"],
                            }
                except Exception:
                    pass
                # Fallback al snippet si falla la extraccion
                return {
                    "url": url,
                    "title": item["title"],
                    "content": item["snippet"],
                    "snippet": item["snippet"],
                }

            fetch_tasks = [fetch_url(item) for item in urls_to_fetch[:3]]
            fetched = await asyncio.gather(*fetch_tasks)

            # Construir resultado
            parts = []
            for item in fetched:
                title = item.get("title", "Sin titulo")
                content = item.get("content", "")
                url = item.get("url", "")
                if content:
                    parts.append(f"**{title}**\n{content}\nFuente: {url}")

            if parts:
                return WebSearchResult(
                    site="duckduckgo_search",
                    site_label="DuckDuckGo Search",
                    query=query,
                    response="\n\n".join(parts)[:4000],
                    success=True,
                )

            return WebSearchResult(
                site="duckduckgo_search",
                site_label="DuckDuckGo Search",
                query=query,
                response="",
                success=False,
                error="No content could be extracted",
            )

        except Exception as e:
            return WebSearchResult(
                site="duckduckgo_search",
                site_label="DuckDuckGo Search",
                query=query,
                response="",
                success=False,
                error=str(e),
            )

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
