"""
Script de Backfill para Data Warehouse
Procesa todos los debates históricos para poblar el warehouse
"""
import asyncio
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.warehouse import warehouse_manager
from backend.database.local_db import init_db


async def main():
    """Función principal de backfill"""
    print("🔄 Iniciando backfill del Data Warehouse...")
    
    # Inicializar base de datos (crea tablas si no existen)
    print("📦 Inicializando base de datos...")
    await init_db()
    print("✅ Base de datos inicializada")
    
    # Ejecutar backfill
    print("📊 Procesando debates históricos...")
    stats = await warehouse_manager.backfill_historical_data()
    
    print("\n📈 Resultados del backfill:")
    print(f"  - SequentialDebates procesados: {stats['sequential_processed']}")
    print(f"  - Sessions procesadas: {stats['session_processed']}")
    print(f"  - Fallos: {stats['failed']}")
    
    if stats['failed'] == 0:
        print("\n✅ Backfill completado exitosamente")
    else:
        print(f"\n⚠️  Backfill completado con {stats['failed']} fallos")
    
    return stats


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result['failed'] == 0 else 1)
    except KeyboardInterrupt:
        print("\n❌ Backfill interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error durante backfill: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
