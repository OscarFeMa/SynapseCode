"""
Synapse Council v2.0 - Web Agent Adapter
Cliente Playwright para IAs gratuitas sin API (ChatGPT, Claude, Gemini)
"""
from typing import Dict, Any, Optional
from backend.config import get_settings

settings = get_settings()


class WebAgentClient:
    """
    Cliente para Agente Web con Playwright
    Navegador automatizado para IAs gratuitas
    """
    
    def __init__(
        self,
        enabled: bool = True,
        browser: str = "chromium",
        headless: bool = True,
    ):
        self.enabled = enabled
        self.browser = browser
        self.headless = headless
        self.timeout = settings.WEB_AGENT_TIMEOUT_SECONDS
        self.session_dir = settings.WEB_AGENT_SESSION_DIR
        self._playwright = None
        self._browser_instance = None
        
    async def health_check(self) -> Dict[str, Any]:
        """Verifica disponibilidad de Playwright"""
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "Web Agent is disabled in configuration"
            }
        
        try:
            from playwright.async_api import async_playwright
            
            # Intentar iniciar playwright brevemente para verificar instalación
            async with async_playwright() as p:
                browser_type = getattr(p, self.browser, p.chromium)
                browser = await browser_type.launch(headless=True)
                await browser.close()
            
            return {
                "status": "available",
                "browser": self.browser,
                "playwright_installed": True,
                "sites": settings.web_agent_sites_list
            }
        except ImportError:
            return {
                "status": "unavailable",
                "error": "Playwright not installed. Run: pip install playwright && playwright install"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def query_chatgpt(self, prompt: str) -> str:
        """
        Envía prompt a ChatGPT vía navegador
        Requiere autenticación previa guardada en session_dir
        """
        if not self.enabled:
            raise RuntimeError("Web Agent is disabled")
        
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=self.headless,
            )
            
            page = await browser.new_page()
            try:
                await page.goto("https://chat.openai.com", timeout=self.timeout * 1000)
                # Esperar input y enviar prompt
                await page.wait_for_selector("#prompt-textarea", timeout=10000)
                await page.fill("#prompt-textarea", prompt)
                await page.click("[data-testid='send-button']")
                
                # Esperar respuesta
                await page.wait_for_selector(".markdown", timeout=self.timeout * 1000)
                response = await page.inner_text(".markdown")
                
                return response
            finally:
                await browser.close()
    
    async def query_claude(self, prompt: str) -> str:
        """Envía prompt a Claude.ai"""
        if not self.enabled:
            raise RuntimeError("Web Agent is disabled")
        
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=self.headless,
            )
            
            page = await browser.new_page()
            try:
                await page.goto("https://claude.ai", timeout=self.timeout * 1000)
                await page.wait_for_selector("[contenteditable='true']", timeout=10000)
                await page.fill("[contenteditable='true']", prompt)
                await page.click("button[aria-label='Send Message']")
                
                await page.wait_for_selector(".claude-response", timeout=self.timeout * 1000)
                response = await page.inner_text(".claude-response")
                
                return response
            finally:
                await browser.close()
