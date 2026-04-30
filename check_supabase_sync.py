"""
Script para verificar estado de sincronización con Supabase
"""
import asyncio
import sqlite3
from datetime import datetime

async def check_supabase_status():
    """Verifica debates locales vs sync a Supabase."""
    
    # 1. Contar debates locales
    conn = sqlite3.connect('data/synapse.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_debates,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            COUNT(CASE WHEN created_at >= '2026-04-30' THEN 1 END) as today_debates
        FROM sequential_debates
    """)
    
    total, completed, today = cursor.fetchone()
    
    cursor.execute("""
        SELECT debate_id, COUNT(*) as turn_count
        FROM sequential_debate_turns
        WHERE created_at >= '2026-04-30'
        GROUP BY debate_id
    """)
    
    today_turns = cursor.fetchall()
    
    conn.close()
    
    print("=" * 60)
    print("📊 ESTADO DE SINCRONIZACIÓN SYNAPSE ↔ SUPABASE")
    print("=" * 60)
    print(f"\n📁 BASE DE DATOS LOCAL (SQLite):")
    print(f"   • Total debates: {total}")
    print(f"   • Completados: {completed}")
    print(f"   • Debates hoy (30/04): {today}")
    print(f"   • Turnos hoy: {len(today_turns)} registros")
    
    # 2. Verificar Supabase
    try:
        from backend.services.supabase_sync import get_supabase_service
        
        supabase = get_supabase_service()
        result = await supabase.test_connection()
        
        print(f"\n☁️  SUPABASE (Cloud):")
        print(f"   • Estado: {result.get('status', 'unknown')}")
        print(f"   • URL: {result.get('url', 'N/A')}")
        
        if result.get('status') == 'connected':
            # Intentar contar debates en Supabase
            import httpx
            client = httpx.AsyncClient(
                headers={
                    "apikey": supabase.key,
                    "Authorization": f"Bearer {supabase.key}"
                }
            )
            
            # Contar debates
            response = await client.get(
                f"{supabase.url}/rest/v1/sequential_debates?select=id&limit=1000"
            )
            
            if response.status_code == 200:
                supabase_debates = len(response.json())
                print(f"   • Debates en Supabase: {supabase_debates}")
                
                # Contar turns
                turns_response = await client.get(
                    f"{supabase.url}/rest/v1/sequential_debate_turns?select=id&limit=1000"
                )
                
                if turns_response.status_code == 200:
                    supabase_turns = len(turns_response.json())
                    print(f"   • Turns en Supabase: {supabase_turns}")
                else:
                    print(f"   • Error contando turns: {turns_response.status_code}")
                    print(f"     {turns_response.text[:200]}")
            else:
                print(f"   • Error: {response.status_code}")
            
            await client.aclose()
        else:
            print(f"   • Error de conexión: {result.get('message', 'Unknown')}")
    
    except Exception as e:
        print(f"\n❌ Error verificando Supabase: {e}")
    
    print("\n" + "=" * 60)
    print("💡 CONCLUSIÓN:")
    
    if today == 10:
        print("   ✅ Los 10 debates del maratón están en SQLite local")
    else:
        print(f"   ⚠️ Solo {today} debates de hoy en local (esperados: 10)")
    
    print("\n   Para arreglar sync de turns a Supabase:")
    print("   1. Actualizar schema: ALTER TABLE sequential_debate_turns")
    print("      ALTER COLUMN provider DROP NOT NULL;")
    print("   2. O añadir default en código: provider='unknown'")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check_supabase_status())
