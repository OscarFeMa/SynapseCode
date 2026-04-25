"""Test directo de OpenRouter"""
import asyncio
import sys
sys.path.insert(0, 'C:\\Users\\usuario\\Desktop\\Synapse_Master')

from backend.adapters.openrouter import OpenRouterClient

async def test():
    print("🔌 Conectando a OpenRouter...")
    client = OpenRouterClient()
    
    print("📡 Health check...")
    health = await client.health_check()
    print(f"Health: {health}")
    
    if health.get("status") == "online":
        print("\n🚀 Generando con Claude 3.5 Haiku...")
        messages = [
            {"role": "user", "content": "Escribe una breve reflexión sobre el impacto de la IA en la educación. Máximo 100 palabras."}
        ]
        
        token_count = 0
        response_text = []
        
        try:
            async for token in client.chat_completion(
                model="anthropic/claude-3.5-haiku",
                messages=messages,
                temperature=0.7,
                max_tokens=200,
                stream=True
            ):
                print(token, end="", flush=True)
                token_count += 1
                response_text.append(token)
            
            print(f"\n\n✅ Completado: {token_count} tokens generados")
            print(f"Respuesta completa: {''.join(response_text)[:200]}...")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ OpenRouter offline")

if __name__ == "__main__":
    asyncio.run(test())
