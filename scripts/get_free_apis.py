"""
Asistente para obtener API keys gratuitas de servicios de IA.
Cada servicio es funcional, gratuito y sin necesidad de tarjeta de credito.

Uso:  python scripts/get_free_apis.py
"""
import webbrowser
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FREE_APIS = [
    {
        "id": "groq",
        "name": "Groq Cloud",
        "provider": "Groq Inc.",
        "url": "https://console.groq.com/keys",
        "models": "Llama 3.1 8B/70B, Mixtral 8x7B, Gemma 2, Llama 3.3 70B",
        "limits": "30 req/min, 14400 req/day, SIN tarjeta de credito",
        "env_var": "GROQ_API_KEY",
        "config_key": "GROQ_API_KEY",
        "setup_steps": [
            "1. Haz clic en 'Abrir pagina' para ir a Groq Console",
            "2. Crea una cuenta (GitHub o email)",
            "3. Ve a API Keys y haz clic en 'Create API Key'",
            "4. Copia la key y pegalas en el paso 2 de este script",
        ],
    },
    {
        "id": "gemini",
        "name": "Google Gemini API",
        "provider": "Google (Alphabet)",
        "url": "https://aistudio.google.com/apikey",
        "models": "Gemini 1.5 Flash, Gemini 1.5 Pro, Gemini 2.0 Flash",
        "limits": "60 req/min, SIN tarjeta de credito",
        "env_var": "GEMINI_API_KEY",
        "config_key": "GEMINI_API_KEY",
        "setup_steps": [
            "1. Haz clic en 'Abrir pagina' para ir a Google AI Studio",
            "2. Inicia sesion con tu cuenta Google",
            "3. Haz clic en 'Get API Key'",
            "4. Copia la key y pegalas en el paso 2",
        ],
    },
    {
        "id": "deepseek",
        "name": "DeepSeek API",
        "provider": "DeepSeek (China)",
        "url": "https://platform.deepseek.com/api_keys",
        "models": "DeepSeek-V2, DeepSeek-Coder-V2",
        "limits": "500M tokens gratis al registrarse (sin tarjeta para prueba)",
        "env_var": "DEEPSEEK_API_KEY",
        "config_key": "DEEPSEEK_API_KEY",
        "setup_steps": [
            "1. Registrate en https://platform.deepseek.com",
            "2. Ve a API Keys",
            "3. Copia tu API key",
        ],
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "provider": "OpenRouter (agregador multi-provider)",
        "url": "https://openrouter.ai/keys",
        "models": "200+ modelos: Claude, GPT, Llama, Mistral, DeepSeek, Qwen...",
        "limits": "Modelos gratuitos disponibles (sin costo), otros son pay-as-you-go",
        "env_var": "OPENROUTER_API_KEY",
        "config_key": "OPENROUTER_API_KEY",
        "setup_steps": [
            "1. Registrate en https://openrouter.ai",
            "2. Ve a Keys y crea una nueva",
            "3. Copia la key",
        ],
    },
    {
        "id": "huggingface",
        "name": "Hugging Face Inference API",
        "provider": "Hugging Face (comunidad open-source)",
        "url": "https://huggingface.co/settings/tokens",
        "models": "Miles de modelos open-source gratuitos",
        "limits": "30k requests/mes gratis",
        "env_var": "HF_TOKEN",
        "config_key": "HF_TOKEN",
        "setup_steps": [
            "1. Registrate en https://huggingface.co",
            "2. Ve a Settings -> Access Tokens",
            "3. Crea un token con rol 'read'",
            "4. Copia el token",
        ],
    },
]


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def read_env():
    env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".env"
    env = {}
    if env_path.exists():
        text = env_path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k.strip()] = v.strip()
    return env, env_path


def write_env(env, env_path):
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    for key, value in env.items():
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def show_menu(env):
    clear()
    print("=" * 60)
    print("  Synapse - API Keys Gratuitas para Servicios de IA")
    print("=" * 60)
    print()

    for i, api in enumerate(FREE_APIS, 1):
        key = env.get(api["env_var"], "")
        status = "CONFIGURADA" if key and key not in ("", "sk-or-v1-CHANGEME", "AIzaSy-CHANGEME", "gsk_CHANGEME", "sk-CHANGEME") else "NO CONFIGURADA"
        color = "[OK]" if "CONFIGURADA" in status else "[  ]"
        print(f"  {i}. {api['name']:30s} {color}")
        print(f"     Proveedor: {api['provider']}")
        print(f"     Modelos: {api['models']}")
        print(f"     Limites: {api['limits']}")
        print(f"     Key: {key[:20] + '...' if key and len(key) > 20 else '(vacia)'}")
        print()

    print("  A) Abrir TODAS las paginas para generar API keys")
    print("  0) Salir")
    print()

    choice = input("  Selecciona un servicio para configurar (1-5, A, 0): ").strip()
    return choice


def setup_api(api, env, env_path):
    clear()
    print(f"=== Configurar {api['name']} ===")
    print()

    for step in api["setup_steps"]:
        print(f"  {step}")

    print()
    input("  Presiona ENTER para abrir la pagina de registro... ")
    webbrowser.open(api["url"])

    print()
    new_key = input(f"  Pega tu API key de {api['name']}: ").strip()

    if new_key:
        env[api["env_var"]] = new_key
        write_env(env, env_path)
        print(f"\n  [OK] API key de {api['name']} guardada en .env")
    else:
        print("\n  [INFO] No se guardo ninguna key")

    input("\n  Presiona ENTER para volver al menu...")


if __name__ == "__main__":
    env, env_path = read_env()

    while True:
        choice = show_menu(env)

        if choice == "0":
            print("\nSaliendo...")
            break

        if choice.lower() == "a":
            for api in FREE_APIS:
                webbrowser.open(api["url"])
            print("\n  Paginas abiertas en tu navegador")
            input("  Presiona ENTER para continuar...")
            continue

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(FREE_APIS):
                setup_api(FREE_APIS[idx], env, env_path)
                env, env_path = read_env()  # Recargar
                continue

        print("\n  Opcion no valida")
        input("  Presiona ENTER...")
