#!/usr/bin/env python3
"""
Test de Humo Fase 0 - Synapse Council v2.0
Verifica que todos los componentes están operativos
"""
import asyncio
import sys
sys.path.insert(0, 'backend')

import httpx


async def test_health():
    """Test de health check local"""
    print("\n" + "="*60)
    print("🧪 TEST DE HUMO - FASE 0")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("http://localhost:8000/health")
            data = response.json()
            
            print(f"\n📊 Estado Global: {data['status']}")
            print(f"🖥️  Rol del Nodo: {data['node_role']}")
            print(f"⏱️  Duración: {data['check_duration_ms']}ms")
            print(f"📅 Timestamp: {data['timestamp']}")
            
            print("\n" + "-"*60)
            print("🔍 SERVICIOS:")
            print("-"*60)
            
            services = data['services']
            
            # Database
            db = services['database']
            icon = "✅" if db['status'] == 'healthy' else "❌"
            print(f"{icon} Base de datos: {db['status']}")
            
            # Ollama
            ollama = services['ollama']
            icon = "✅" if ollama.get('status') == 'online' else "⚠️"
            print(f"{icon} Ollama: {ollama.get('status', 'unknown')}")
            if ollama.get('models_available'):
                print(f"   └─ {ollama['models_available']} modelos disponibles")
            if ollama.get('error'):
                print(f"   └─ Error: {ollama['error']}")
            
            # LM Studio
            lm = services['lm_studio']
            icon = "✅" if lm.get('status') == 'online' else "⚠️"
            print(f"{icon} LM Studio: {lm.get('status', 'unknown')}")
            if lm.get('error'):
                print(f"   └─ {lm['error']}")
            
            # Jan
            jan = services['jan']
            icon = "✅" if jan.get('status') == 'online' else "⚠️"
            print(f"{icon} Jan.ai: {jan.get('status', 'unknown')}")
            if jan.get('error'):
                print(f"   └─ {jan['error']}")
            
            # OpenRouter
            orouter = services['openrouter']
            icon = "✅" if orouter.get('status') == 'online' else "⚠️"
            print(f"{icon} OpenRouter: {orouter.get('status', 'unknown')}")
            if orouter.get('key_valid'):
                print(f"   └─ API Key válida")
            if orouter.get('error'):
                print(f"   └─ {orouter['error']}")
            
            # Web Agent
            web = services['web_agent']
            icon = "✅" if web.get('status') == 'available' else "⚠️"
            print(f"{icon} Web Agent: {web.get('status', 'unknown')}")
            if web.get('playwright_installed'):
                print(f"   └─ Playwright: instalado")
                print(f"   └─ Browser: {web.get('browser', 'unknown')}")
            if web.get('error'):
                print(f"   └─ {web['error']}")
            
            print("\n" + "="*60)
            if data['status'] == 'healthy':
                print("✅ TEST PASADO - Sistema operativo")
            else:
                print("⚠️ TEST DEGRADADO - Algunos servicios no disponibles")
            print("="*60)
            
    except httpx.ConnectError:
        print("\n❌ ERROR: No se pudo conectar a http://localhost:8000")
        print("   Asegúrate de que el servidor esté corriendo:")
        print("   python backend/main.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_health())
