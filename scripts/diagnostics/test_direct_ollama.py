"""Test directo del adaptador Ollama"""
import asyncio
import sys
sys.path.insert(0, 'C:\\Users\\usuario\\Desktop\\Synapse_Master')

from backend.adapters.ollama import OllamaClient

async def test():
    print("🔌 Conectando a Worker (192.168.1.43:11434)...")
    client = OllamaClient(base_url="http://192.168.1.43:11434")
    
    print("📡 Health check...")
    health = await client.health_check()
    print(f"Health: {health}")
    
    if health.get("status") == "online":
        print("\n🚀 Generando con tinyllama...")
        token_count = 0
        async for token in client.generate(model="tinyllama:latest", prompt="Hola", system="Responde brevemente"):
            print(token, end="", flush=True)
            token_count += 1
        print(f"\n✅ Completado: {token_count} tokens generados")
    else:
        print("❌ Ollama offline en Worker")

if __name__ == "__main__":
    asyncio.run(test())
