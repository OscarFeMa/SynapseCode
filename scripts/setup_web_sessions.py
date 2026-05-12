"""
Web Agent Session Setup - Guarda sesiones de navegador para sitios de IA.
Ejecuta: python scripts/setup_web_sessions.py

Inicia sesion manualmente en los sitios que quieras usar.
Las cookies quedan guardadas en data/browser_sessions/ para uso futuro.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SITES = {
    "1": ("chat.openai.com", "ChatGPT (OpenAI)"),
    "2": ("claude.ai", "Claude (Anthropic)"),
    "3": ("gemini.google.com", "Gemini (Google)"),
    "4": ("chat.deepseek.com", "DeepSeek Chat"),
    "5": ("www.perplexity.ai", "Perplexity AI"),
    "6": ("grok.com", "Grok (xAI)"),
    "7": ("chat.mistral.ai", "Mistral Chat"),
    "8": ("www.meta.ai", "Meta AI"),
    "9": ("huggingface.co/chat", "HuggingChat"),
    "10": ("you.com", "You.com"),
}

SESSION_DIR = "./data/browser_sessions"
os.makedirs(SESSION_DIR, exist_ok=True)

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def show_menu():
    clear_screen()
    print("=" * 55)
    print("  Synapse Web Agent - Configuracion de Sesiones")
    print("=" * 55)
    print()
    print("  El navegador se abrira automaticamente.")
    print("  Si aparece Cloudflare o un captcha, resuelvelo manualmente.")
    print("  DESPUES de iniciar sesion, CIERRA el navegador.")
    print("  Luego presiona ENTER en esta ventana para guardar.")
    print()
    print("  Sitios disponibles:")
    for k, (url, name) in SITES.items():
        idx = k if int(k) < 10 else k
        print(f"    {idx:>2}) {name}")
    print("   T) Todos")
    print("   0) Salir")
    print()

def open_site(url, name):
    print(f"\n--- {name} ---")
    print(f"Abriendo {url}...")
    print(f"  Si ves Cloudflare, resuelve el captcha manualmente.")
    print(f"  Luego inicia sesion y CIERRA el navegador.")
    print()

    from playwright.sync_api import sync_playwright
    try:
        from playwright_stealth import stealth_sync
        has_stealth = True
    except ImportError:
        has_stealth = False

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-web-security",
            ],
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            bypass_csp=True,
        )
        page = browser.new_page()
        if has_stealth:
            stealth_sync(page)
        page.goto(f"https://{url}", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        input(f"  >> Presiona ENTER cuando hayas iniciado sesion y cerrado el navegador... ")

        try:
            browser.close()
        except:
            pass

    print(f"  >> Sesion de {name} guardada correctamente")
    time.sleep(1)


if __name__ == "__main__":
    while True:
        show_menu()
        choice = input("  Selecciona una opcion: ").strip().lower()

        if choice == "0":
            print("\nSaliendo...")
            break

        if choice == "t":
            for k, (url, name) in SITES.items():
                open_site(url, name)
            print(f"\nTodas las sesiones guardadas en: {os.path.abspath(SESSION_DIR)}")
            input("\nPresiona ENTER para volver al menu...")
        elif choice in SITES:
            url, name = SITES[choice]
            open_site(url, name)
            input("\nPresiona ENTER para volver al menu...")
        else:
            print("\nOpcion no valida")
            time.sleep(1)
