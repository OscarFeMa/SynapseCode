#!/usr/bin/env python3
"""
Test de Humo Fase 1 - Synapse Council v2.0
Ejecuta una sesión de debate real de 1 ronda
"""
import asyncio
import sys
import time
sys.path.insert(0, 'backend')

import httpx


async def test_create_and_run_session(rounds: int = 2):
    """Test completo: crear sesión y ejecutar debate de N rondas"""
    print("\n" + "="*70)
    print(f"🧪 TEST DE HUMO - FASE 2: Tribunal + Múltiples Rondas ({rounds})")
    print("="*70)
    
    base_url = "http://localhost:8000"
    
    # 1. Verificar health check primero
    print("\n[1/5] Verificando health check...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{base_url}/health")
        health = response.json()
        
        if health['status'] != 'healthy':
            print(f"⚠️  Sistema degradado: {health['status']}")
            print("   Continuando de todos modos...")
        else:
            print("✅ Sistema saludable")
    
    # 2. Crear sesión
    print("\n[2/5] Creando sesión de debate...")
    query = "¿Cuáles son las ventajas y desventajas de implementar una semana laboral de 4 días en una empresa tecnológica?"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/api/v1/sessions",
            json={
                "query": query,
                "title": f"Test: Semana laboral 4 días ({rounds} rondas)",
                "max_rounds": rounds
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Error creando sesión: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        session_id = result['session_id']
        print(f"✅ Sesión creada: {session_id}")
        print(f"   Status: {result['status']}")
    
    # 3. Esperar ejecución (polling)
    print("\n[3/5] Esperando ejecución del debate (esto puede tardar varios minutos)...")
    print("   Los 10 agentes están procesando en paralelo...")
    
    max_wait = 300  # 5 minutos máximo
    poll_interval = 5
    waited = 0
    
    while waited < max_wait:
        await asyncio.sleep(poll_interval)
        waited += poll_interval
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/api/v1/sessions/{session_id}")
            
            if response.status_code != 200:
                print(f".", end="", flush=True)
                continue
            
            detail = response.json()
            session = detail['session']
            
            if session['status'] == 'COMPLETED':
                print(f"\n✅ Debate completado en {waited}s!")
                break
            elif session['status'] == 'FAILED':
                print(f"\n❌ Debate fallido")
                break
            else:
                print(f".", end="", flush=True)
    
    # 4. Obtener detalles completos
    print("\n[4/5] Obteniendo detalles de la sesión...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/api/v1/sessions/{session_id}")
        detail = response.json()
        
        session = detail['session']
        rounds = detail['rounds']
        agent_calls = detail['agent_calls']
        
        print(f"\n   📋 Resumen:")
        print(f"   - Query: {session['query'][:60]}...")
        print(f"   - Status: {session['status']}")
        print(f"   - Nivel de consenso: {session['consensus_level']}")
        print(f"   - Rondas ejecutadas: {session['rounds_executed']}")
        print(f"   - Tokens totales: {session['total_tokens_in']} in / {session['total_tokens_out']} out")
        print(f"   - Costo estimado: ${session['estimated_cost_usd']:.4f} USD")
        
        # Mostrar info del Tribunal si existe
        if session.get('tribunal_verdict'):
            tv = session['tribunal_verdict']
            print(f"\n   🏛️ Tribunal de Magistrados:")
            print(f"   - Consenso alcanzado: {'✅ Sí' if tv.get('consensus_reached') else '⚠️ No'}")
            print(f"   - Iteraciones PCO: {tv.get('iterations_required', 0)}")
            print(f"   - Score Evidencias: {tv.get('evidence_score', 0)}/100")
            print(f"   - Score Riesgos: {tv.get('risk_score', 0)}/100")
            print(f"   - Score Alineación: {tv.get('alignment_score', 0)}/100")
        
        print(f"\n   🔄 Rondas:")
        for r in rounds:
            print(f"   - Ronda {r['number']}: {r['status']}")
        
        print(f"\n   🤖 Agent Calls por fase:")
        for phase, calls in agent_calls.items():
            completed = sum(1 for c in calls if c['status'] == 'COMPLETED')
            failed = sum(1 for c in calls if c['status'] == 'FAILED')
            total_tokens = sum(c['tokens_out'] or 0 for c in calls)
            print(f"   - {phase}: {completed} OK, {failed} FAIL, {total_tokens} tokens")
            
            # Mostrar detalle de agentes
            for call in calls[:3]:  # Primeros 3
                print(f"     • {call['slot']} ({call['model'][:20]}): {call['status']}, {call['tokens_out']} tokens")
    
    # 5. Verificar final summary
    print("\n[5/5] Verificando síntesis final...")
    
    if session.get('final_summary'):
        summary = session['final_summary']
        print("✅ Síntesis generada:")
        print("-" * 70)
        # Mostrar primeras líneas
        lines = summary.split('\n')[:10]
        for line in lines:
            print(f"   {line[:80]}")
        if len(summary.split('\n')) > 10:
            print("   ...")
        print("-" * 70)
    else:
        print("⚠️  No se generó síntesis final")
    
    # Resultado final
    print("\n" + "="*70)
    if session['status'] == 'COMPLETED':
        print("✅ TEST FASE 2 PASADO - Tribunal y Múltiples Rondas")
        print(f"   Session ID: {session_id}")
        print(f"   Rondas: {session['rounds_executed']}")
        print(f"   Total tokens: {session['total_tokens_out']}")
        print(f"   Costo: ${session['estimated_cost_usd']:.4f}")
    else:
        print("❌ TEST FASE 2 FALLIDO")
    print("="*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Synapse Council v2.0')
    parser.add_argument('--rounds', type=int, default=2, help='Número de rondas (1-3)')
    args = parser.parse_args()
    
    try:
        asyncio.run(test_create_and_run_session(rounds=args.rounds))
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrumpido por usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
