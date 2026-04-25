"""
Test manual para el sistema de descubrimiento UDP (P2P).
Levanta dos instancias del discoverer (como MASTER y WORKER) y verifica que se encuentren.
"""
import asyncio
import os
import sys

# Añadir el root al sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.config import get_settings
from backend.network.discovery import NodeDiscoverer

async def run_simulated_node(role: str, delay: int = 0):
    """Simula un nodo con un rol específico"""
    await asyncio.sleep(delay)
    
    settings = get_settings()
    settings.NODE_ROLE = role
    settings.PORT = 8000 if role == "MASTER" else 8001
    
    discoverer = NodeDiscoverer()
    # Forzar un ID para la simulación
    discoverer.node_id = f"{role.lower()}-sim"
    
    print(f"[{role}] Iniciando descubrimiento...")
    await discoverer.start()
    
    try:
        for _ in range(5):
            await asyncio.sleep(2)
            peers = discoverer.get_active_peers()
            if peers:
                print(f"[{role}] Nodos descubiertos: {peers}")
            else:
                print(f"[{role}] Buscando nodos...")
                
            if role == "MASTER" and peers and peers[0]["role"] == "WORKER":
                print(f"[{role}] ¡WORKER DESCUBIERTO EXITOSAMENTE! IP: {peers[0]['ip']}")
                break
    finally:
        await discoverer.stop()

async def main():
    print("Iniciando simulación de red P2P...")
    print("El Master y el Worker se ejecutarán en paralelo en la misma red local.")
    
    # Ejecutar Master y Worker simultáneamente (el worker arranca 1 segundo después)
    await asyncio.gather(
        run_simulated_node("MASTER", 0),
        run_simulated_node("WORKER", 1)
    )
    
    print("Prueba completada.")

if __name__ == "__main__":
    # En Windows, usar ProactorEventLoop a veces es necesario para UDP,
    # pero el predeterminado en Python 3.8+ ya funciona bien.
    asyncio.run(main())
