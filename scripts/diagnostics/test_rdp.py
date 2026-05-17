"""
Test directo del RDP Manager
Prueba la conexión RDP al Worker sin necesidad de iniciar el backend completo.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.rdp_manager import RDPManager
from backend.config import get_settings

settings = get_settings()

print("🧪 Test RDP Manager - Synapse Council")
print("=" * 50)
print(f"Hostname: {settings.RDP_WORKER_HOSTNAME}")
print(f"Username: {settings.RDP_WORKER_USERNAME}")
print(f"Password: {'*' * len(settings.RDP_WORKER_PASSWORD)}")
print(f"Rate Limit: {settings.RDP_RATE_LIMIT_SECONDS}s")
print("=" * 50)

# Test 1: Resolver IP
print("\n📡 Test 1: Resolución DNS...")
ip = RDPManager.get_ip_by_hostname(settings.RDP_WORKER_HOSTNAME)
if ip:
    print(f"   ✅ IP resuelta: {ip}")
else:
    print(f"   ❌ No se pudo resolver {settings.RDP_WORKER_HOSTNAME}")
    print("   Abortando prueba RDP...")
    sys.exit(1)

# Test 2: Conexión RDP (esto abrirá mstsc!)
print("\n🖥️  Test 2: Conexión RDP (se abrirá ventana de Escritorio Remoto)...")
print("   ⚠️  Asegúrate de que el PC remoto esté accesible")
input("   Presiona ENTER para continuar o Ctrl+C para cancelar...")

print("\n   🔄 Intentando conexión...")
result = RDPManager.connect_to_worker(
    hostname=settings.RDP_WORKER_HOSTNAME,
    username=settings.RDP_WORKER_USERNAME,
    password=settings.RDP_WORKER_PASSWORD
)

if result["success"]:
    print(f"   ✅ {result['message']}")
    print(f"   🎯 IP: {result.get('ip', 'N/A')}")
    print(f"   ⏱️  Duración: {result.get('duration_ms', 'N/A')}ms")
else:
    print(f"   ❌ Error: {result['message']}")
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ Prueba RDP completada!")
print("\nSi la ventana de Escritorio Remoto se abrió correctamente,")
print("el RDP Manager está funcionando bien.")
