import asyncio
import sys
from datetime import datetime

import httpx

from backend.config import settings


async def check_ollama(url: str, name: str):
    print(f"  - Verificando {name} en {url}...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"    [OK] {name}: ACTIVO")
                print(f"    Modelos disponibles: {len(models)}")
                for m in models[:3]:
                    print(f"       * {m.get('name')}")
                if len(models) > 3:
                    print(f"       ... y {len(models) - 3} mas.")
                return True, len(models)
            else:
                print(f"    [ERROR] {name}: Error {response.status_code}")
                return False, 0
    except Exception as e:
        print(f"    [ERROR] {name}: INACTIVO ({type(e).__name__})")
        return False, 0


async def check_rdp():
    if not settings.RDP_ENABLED:
        print("  - RDP: Deshabilitado en configuración.")
        return True

    print(f"  - Verificando RDP (Worker) en {settings.RDP_WORKER_HOSTNAME}...")
    try:
        # Intento simple de conexión TCP al puerto RDP (3389)
        ip = settings.resolve_worker_ip()
        if not ip:
            print(f"    ❌ RDP: No se pudo resolver hostname '{settings.RDP_WORKER_HOSTNAME}'")
            return False

        loop = asyncio.get_event_loop()
        try:
            # timeout de 3 segundos
            fut = loop.create_connection(lambda: asyncio.Protocol(), ip, 3389)
            transport, _ = await asyncio.wait_for(fut, timeout=3.0)
            transport.close()
            print(f"    [OK] RDP: Conexion exitosa a {ip}:3389")
            return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            print(f"    [ERROR] RDP: Puerto 3389 cerrado en {ip}. ¿Esta el Worker encendido?")
            return False

    except Exception as e:
        print(f"    [ERROR] RDP: Error al verificar ({e!s})")
        return False


async def main():
    print("\n" + "=" * 50)
    print("        SYNAPSE COUNCIL - PRE-STARTUP CHECK")
    print("=" * 50)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. Verificar Master Ollama
    print("[1/3] Verificando Master Ollama (Local)...")
    master_ok, master_models = await check_ollama(settings.OLLAMA_BASE_URL, "Master Ollama")
    print()

    # 2. Verificar Worker Ollama
    print("[2/3] Verificando Worker Ollama...")
    worker_host = settings.get_worker_host()
    if worker_host:
        worker_url = f"http://{worker_host}:{settings.WORKER_OLLAMA_PORT}"
        worker_ok, worker_models = await check_ollama(worker_url, f"Worker Ollama ({worker_host})")
    else:
        print(f"    ❌ Worker: No se pudo determinar la IP (Hostname: {settings.RDP_WORKER_HOSTNAME})")
        worker_ok, worker_models = False, 0
    print()

    # 3. Verificar RDP
    print("[3/3] Verificando Escritorio Remoto (RDP)...")
    rdp_ok = await check_rdp()
    print()

    print("=" * 50)
    print("                  RESUMEN")
    print("=" * 50)

    overall_ok = master_ok and worker_ok and rdp_ok

    if overall_ok:
        print("\n    [OK] TODO CORRECTO. El sistema esta listo.")
        print(f"    Total Modelos: {master_models} (Master) + {worker_models} (Worker)")
    else:
        print("\n    [!] ATENCION: Se detectaron problemas de conectividad.")
        if not master_ok:
            print("    - Master Ollama no responde.")
        if not worker_ok:
            print("    - Worker Ollama no responde.")
        if not rdp_ok:
            print("    - RDP en Worker no disponible.")
        print("\n    ¿Deseas continuar de todos modos? (S/N)")

        # En un script de pre-startup, si falla, podemos salir con error para que el .bat pare
        # Pero a veces el usuario quiere arrancar aunque el worker esté offline
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
