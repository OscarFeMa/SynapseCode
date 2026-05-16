"""
Synapse Council v2.0 - Web Agent Adapter
Cliente Playwright para IAs web gratuitas sin API
Soporta: ChatGPT, Claude, Gemini, DeepSeek, Perplexity, Grok, Mistral, Meta AI, HuggingChat, You.com
Usa playwright-stealth para evitar detección por Cloudflare y similares.
"""

from typing import Any, Dict

from backend.config import get_settings

settings = get_settings()

# Configuración por sitio: url, input_selector, submit_selector, response_selector, response_wait_for
SITE_CONFIGS = {
    "chatgpt": {
        "url": "https://chat.openai.com",
        "input_selector": "#prompt-textarea",
        "submit_selector": "[data-testid='send-button']",
        "response_selector": ".markdown",
        "wait_for": 10000,
        "label": "ChatGPT (OpenAI)",
    },
    "claude": {
        "url": "https://claude.ai",
        "input_selector": "[contenteditable='true']",
        "submit_selector": "button[aria-label='Send Message']",
        "response_selector": ".claude-response",
        "wait_for": 10000,
        "label": "Claude (Anthropic)",
    },
    "gemini": {
        "url": "https://gemini.google.com",
        "input_selector": "[contenteditable='true']",
        "submit_selector": "button[aria-label*='Send']",
        "response_selector": ".response-content",
        "wait_for": 10000,
        "label": "Gemini (Google)",
    },
    "deepseek": {
        "url": "https://chat.deepseek.com",
        "input_selector": "#chat-input",
        "submit_selector": ".chat-send-btn",
        "response_selector": ".ds-markdown",
        "wait_for": 15000,
        "label": "DeepSeek Chat",
    },
    "perplexity": {
        "url": "https://www.perplexity.ai",
        "input_selector": "textarea[placeholder*='Ask']",
        "submit_selector": "button[aria-label*='Submit']",
        "response_selector": ".prose",
        "wait_for": 15000,
        "label": "Perplexity AI",
    },
    "grok": {
        "url": "https://grok.com",
        "input_selector": "textarea",
        "submit_selector": "button[type='submit']",
        "response_selector": ".message-content",
        "wait_for": 15000,
        "label": "Grok (xAI)",
    },
    "mistral": {
        "url": "https://chat.mistral.ai",
        "input_selector": "[contenteditable='true']",
        "submit_selector": "button[aria-label*='Send']",
        "response_selector": ".prose",
        "wait_for": 10000,
        "label": "Mistral Chat",
    },
    "meta": {
        "url": "https://www.meta.ai",
        "input_selector": "textarea",
        "submit_selector": "button[type='submit']",
        "response_selector": "[data-testid='response']",
        "wait_for": 15000,
        "label": "Meta AI",
    },
    "huggingchat": {
        "url": "https://huggingface.co/chat",
        "input_selector": "textarea",
        "submit_selector": "button[type='submit']",
        "response_selector": ".message-bot",
        "wait_for": 20000,
        "label": "HuggingChat",
    },
    "you": {
        "url": "https://you.com",
        "input_selector": "textarea",
        "submit_selector": "button[aria-label*='Search']",
        "response_selector": ".answer",
        "wait_for": 15000,
        "label": "You.com",
    },
}


class WebAgentClient:
    """
    Cliente para Agente Web con Playwright.
    Navegador automatizado para IAs web gratuitas.
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

    async def health_check(self) -> Dict[str, Any]:
        """Verifica disponibilidad de Playwright"""
        if not self.enabled:
            return {"status": "disabled", "message": "Web Agent disabled"}

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser_type = getattr(p, self.browser, p.chromium)
                browser = await browser_type.launch(headless=True)
                await browser.close()

            return {
                "status": "available",
                "browser": self.browser,
                "playwright_installed": True,
                "sites": list(SITE_CONFIGS.keys()),
                "site_labels": {k: v["label"] for k, v in SITE_CONFIGS.items()},
            }
        except ImportError:
            return {
                "status": "unavailable",
                "error": "Playwright not installed. Run: pip install playwright && playwright install",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def list_sites(self) -> Dict[str, str]:
        """Retorna dict de sitios disponibles: {id: label}"""
        return {k: v["label"] for k, v in SITE_CONFIGS.items()}

    async def _apply_stealth(self, page) -> None:
        """Aplica evasiones de detección a la página (playwright-stealth)"""
        try:
            from playwright_stealth import stealth_async

            await stealth_async(page)
        except ImportError:
            pass  # playwright-stealth no instalado, continuar sin stealth

    async def _launch_browser(self):
        """Lanza navegador persistente con configuraciones anti-detección"""
        from playwright.async_api import async_playwright

        p = await async_playwright().__aenter__()

        kwargs = dict(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=BlockInsecurePrivateNetworkRequests",
            ],
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
            timezone_id="Europe/Madrid",
            bypass_csp=True,
        )

        # Usar Chrome del sistema si está configurado (aprovecha sesiones guardadas)
        if settings.WEB_AGENT_BROWSER == "chrome":
            import os as _os

            chrome_path = settings.WEB_AGENT_CHROME_PATH
            if _os.path.exists(chrome_path):
                kwargs["executable_path"] = chrome_path
            if settings.WEB_AGENT_CHROME_PROFILE:
                kwargs["user_data_dir"] = settings.WEB_AGENT_CHROME_PROFILE
            else:
                # Usar el perfil por defecto del usuario
                user = _os.environ.get("USERNAME", "usuario")
                default_profile = f"C:\\Users\\{user}\\AppData\\Local\\Google\\Chrome\\User Data\\Default"
                if _os.path.exists(default_profile.replace("\\Default", "")):
                    kwargs["user_data_dir"] = default_profile
                else:
                    kwargs["user_data_dir"] = self.session_dir
        else:
            kwargs["user_data_dir"] = self.session_dir

        browser = await p.chromium.launch_persistent_context(**kwargs)
        return p, browser

    async def query(self, site: str, prompt: str) -> str:
        """
        Envía un prompt a un sitio de IA vía navegador.
        Args:
            site: Identificador del sitio (chatgpt, claude, gemini, etc.)
            prompt: Texto a enviar
        Returns:
            Respuesta del modelo
        """
        site = site.lower().replace(" ", "_")
        config = SITE_CONFIGS.get(site)
        if not config:
            supported = ", ".join(SITE_CONFIGS.keys())
            raise ValueError(f"Sitio no soportado: '{site}'. Soportados: {supported}")

        p, browser = await self._launch_browser()
        page = await browser.new_page()
        try:
            await self._apply_stealth(page)
            await page.goto(
                config["url"],
                timeout=self.timeout * 1000,
                wait_until="domcontentloaded",
            )
            await page.wait_for_timeout(
                2000
            )  # Esperar 2s para que carguen scripts anti-bot
            await page.wait_for_selector(
                config["input_selector"], timeout=config["wait_for"]
            )
            await page.fill(config["input_selector"], prompt)
            await page.wait_for_timeout(500)

            if config.get("submit_selector"):
                await page.click(config["submit_selector"])

            await page.wait_for_selector(
                config["response_selector"], timeout=self.timeout * 1000
            )
            response = await page.inner_text(config["response_selector"])
            return response
        finally:
            await browser.close()
            await p.__aexit__(None, None, None)

    # Métodos específicos para compatibilidad hacia atrás
    async def query_chatgpt(self, prompt: str) -> str:
        """Envía prompt a ChatGPT"""
        return await self.query("chatgpt", prompt)

    async def query_claude(self, prompt: str) -> str:
        """Envía prompt a Claude"""
        return await self.query("claude", prompt)

    async def query_gemini(self, prompt: str) -> str:
        """Envía prompt a Gemini"""
        return await self.query("gemini", prompt)

    async def query_deepseek(self, prompt: str) -> str:
        """Envía prompt a DeepSeek Chat"""
        return await self.query("deepseek", prompt)

    async def query_perplexity(self, prompt: str) -> str:
        """Envía prompt a Perplexity"""
        return await self.query("perplexity", prompt)

    async def query_grok(self, prompt: str) -> str:
        """Envía prompt a Grok"""
        return await self.query("grok", prompt)

    async def query_mistral(self, prompt: str) -> str:
        """Envía prompt a Mistral Chat"""
        return await self.query("mistral", prompt)

    async def query_meta(self, prompt: str) -> str:
        """Envía prompt a Meta AI"""
        return await self.query("meta", prompt)

    async def query_huggingchat(self, prompt: str) -> str:
        """Envía prompt a HuggingChat"""
        return await self.query("huggingchat", prompt)

    async def query_you(self, prompt: str) -> str:
        """Envía prompt a You.com"""
        return await self.query("you", prompt)
