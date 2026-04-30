#!/usr/bin/env python3
"""
Script para re-sincronizar TODOS los debates a Supabase
Corrige problemas de sync y fuerza re-upload completo
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.local_db import AsyncSessionLocal
from backend.database.models import SequentialDebate, SequentialDebateTurn
from backend.services.supabase_sync import get_supabase_service
from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2
import structlog

logger = structlog.get_logger()


async def get_all_debates(session: AsyncSession):
    """Obtiene todos los debates completados de SQLite."""
    result = await session.execute(
        select(SequentialDebate)
        .where(SequentialDebate.status == 'completed')
        .order_by(SequentialDebate.created_at.desc())
    )
    return result.scalars().all()


async def get_debate_turns(session: AsyncSession, debate_id: str):
    """Obtiene todos los turns de un debate."""
    result = await session.execute(
        select(SequentialDebateTurn)
        .where(SequentialDebateTurn.debate_id == debate_id)
        .order_by(SequentialDebateTurn.turn_number)
    )
    return result.scalars().all()


async def sync_debate_to_supabase(supabase_service, debate, turns):
    """Sincroniza un debate completo a Supabase."""
    
    debate_id = str(debate.id)
    
    # Preparar datos del debate
    debate_data = {
        'id': debate_id,
        'topic': debate.topic,
        'status': debate.status,
        'mode': debate.mode,
        'total_turns': len(turns),
        'total_tokens_in': sum(t.tokens_in or 0 for t in turns),
        'total_tokens_out': sum(t.tokens_out or 0 for t in turns),
        'total_latency_ms': sum(t.latency_ms or 0 for t in turns),
        'final_verdict': debate.final_verdict,
        'transcript_path': debate.transcript_path,
        'created_at': debate.created_at.isoformat() if debate.created_at else datetime.utcnow().isoformat(),
        'completed_at': debate.completed_at.isoformat() if debate.completed_at else None,
    }
    
    # Preparar turns
    turns_data = []
    for turn in turns:
        turns_data.append({
            'turn_number': turn.turn_number,
            'agent_id': turn.agent_id or 'unknown',
            'agent_name': turn.agent_name,
            'agent_role': turn.agent_role or 'analyst',
            'model': turn.model,
            'provider': turn.provider or 'unknown',
            'node': turn.node or 'LOCAL',
            'engine': turn.engine or 'ollama',
            'prompt_sent': turn.prompt_sent or '',
            'response_received': turn.response_received or '',
            'tokens_in': turn.tokens_in or 0,
            'tokens_out': turn.tokens_out or 0,
            'latency_ms': turn.latency_ms or 0,
            'status': turn.status or 'completed',
            'started_at': turn.started_at.isoformat() if turn.started_at else datetime.utcnow().isoformat(),
            'completed_at': turn.completed_at.isoformat() if turn.completed_at else None,
        })
    
    debate_data['turns'] = turns_data
    
    # Enviar a Supabase
    try:
        result = await supabase_service.sync_debate(debate_data)
        return result
    except Exception as e:
        logger.error("resync.debate_failed", debate_id=debate_id, error=str(e))
        return {"synced": False, "error": str(e)}


async def main():
    """Script principal de re-sincronización."""
    
    print("=" * 70)
    print("🔄 RE-SINCRONIZACIÓN COMPLETA A SUPABASE")
    print("=" * 70)
    
    # 1. Verificar conexión a Supabase
    print("\n📡 Verificando conexión a Supabase...")
    supabase = get_supabase_service()
    
    try:
        test_result = await supabase.test_connection()
        if test_result.get('status') != 'connected':
            print(f"❌ Error de conexión: {test_result}")
            return
        print(f"✅ Conectado a Supabase: {test_result.get('url', 'N/A')}")
    except Exception as e:
        print(f"❌ No se puede conectar a Supabase: {e}")
        return
    
    # 2. Obtener todos los debates locales
    print("\n📁 Leyendo debates de SQLite...")
    
    async with AsyncSessionLocal() as session:
        debates = await get_all_debates(session)
        print(f"   Encontrados {len(debates)} debates completados")
        
        if not debates:
            print("   ⚠️ No hay debates para sincronizar")
            return
        
        # 3. Sincronizar cada debate
        print("\n☁️  Sincronizando a Supabase...")
        print("-" * 70)
        
        synced_count = 0
        failed_count = 0
        
        for i, debate in enumerate(debates, 1):
            debate_id = str(debate.id)
            print(f"\n[{i}/{len(debates)}] Debate: {debate_id[:8]}... | Tema: {debate.topic[:50]}...")
            
            # Obtener turns
            turns = await get_debate_turns(session, debate_id)
            print(f"      └─ {len(turns)} turns locales")
            
            # Sincronizar
            result = await sync_debate_to_supabase(supabase, debate, turns)
            
            if result.get('synced'):
                print(f"      ✅ Sincronizado ({result.get('turns_synced', 0)} turns)")
                synced_count += 1
            else:
                print(f"      ❌ Falló: {result.get('error', 'Unknown')[:100]}")
                failed_count += 1
        
        # 4. Resumen final
        print("\n" + "=" * 70)
        print("📊 RESUMEN DE SINCRONIZACIÓN")
        print("=" * 70)
        print(f"   Total debates:     {len(debates)}")
        print(f"   ✅ Sincronizados:  {synced_count}")
        print(f"   ❌ Fallidos:       {failed_count}")
        
        if failed_count == 0:
            print("\n   🎉 ¡Todos los debates sincronizados exitosamente!")
        else:
            print(f"\n   ⚠️  {failed_count} debates necesitan atención manual")
        
        print("\n   💡 Verifica en Supabase:")
        print(f"      {supabase.url}/project/_/editor")
        print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrumpido por usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
