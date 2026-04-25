#!/usr/bin/env python3
"""
Test de WebSocket Fase 3 - Synapse Council v2.0
Prueba streaming en tiempo real de eventos de sesión
"""
import asyncio
import json
import sys
import time
import argparse

sys.path.insert(0, 'backend')

import httpx
import websockets


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{Colors.ENDC}"


async def test_websocket_streaming(rounds: int = 1):
    """Test WebSocket streaming con una sesión real"""
    print("\n" + "="*70)
    print(colorize("🧪 TEST WEBSOCKET - FASE 3: Streaming en Tiempo Real", Colors.HEADER))
    print("="*70)
    
    base_url = "http://localhost:8000"
    ws_url = "ws://localhost:8000/ws/sessions"
    
    # 1. Crear sesión
    print(colorize("\n[1/4] Creando sesión de debate...", Colors.OKBLUE))
    query = "¿Cuáles son los beneficios de implementar un sistema de IA deliberativa en una empresa?"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/api/v1/sessions",
            json={
                "query": query,
                "title": f"Test WebSocket ({rounds} ronda(s))",
                "max_rounds": rounds
            }
        )
        
        if response.status_code != 200:
            print(colorize(f"❌ Error creando sesión: {response.status_code}", Colors.FAIL))
            return
        
        result = response.json()
        session_id = result['session_id']
        print(colorize(f"✅ Sesión creada: {session_id}", Colors.OKGREEN))
    
    # 2. Conectar WebSocket
    print(colorize("\n[2/4] Conectando WebSocket...", Colors.OKBLUE))
    
    event_counts = {
        'total': 0,
        'agent_token': 0,
        'agent_completed': 0,
        'phase_started': 0,
        'round_completed': 0,
        'tribunal_objection': 0,
        'tribunal_verdict': 0,
    }
    
    # Estado para mostrar progreso
    current_agent = None
    current_phase = None
    tokens_buffer = ""
    
    async def handle_events(websocket):
        """Handler para eventos WebSocket"""
        nonlocal current_agent, current_phase, tokens_buffer
        
        try:
            async for message in websocket:
                try:
                    event = json.loads(message)
                    event_type = event.get('type')
                    payload = event.get('payload', {})
                    
                    event_counts['total'] += 1
                    
                    # Procesar según tipo de evento
                    if event_type == 'connection_established':
                        print(colorize(f"🔗 Conectado: {payload.get('message')}", Colors.OKGREEN))
                    
                    elif event_type == 'session_started':
                        print(colorize(f"\n🚀 Sesión iniciada: {payload.get('query', '')[:50]}...", Colors.OKCYAN))
                    
                    elif event_type == 'round_start':
                        round_num = payload.get('round_number', 0)
                        total = payload.get('total_rounds', 0)
                        print(colorize(f"\n📍 Ronda {round_num}/{total} iniciada", Colors.OKCYAN + Colors.BOLD))
                    
                    elif event_type == 'phase_started':
                        phase = payload.get('phase', 'UNKNOWN')
                        current_phase = phase
                        print(colorize(f"\n▶️  Fase: {phase}", Colors.WARNING))
                    
                    elif event_type == 'agent_token':
                        event_counts['agent_token'] += 1
                        agent = payload.get('agent', 'unknown')
                        token = payload.get('token', '')
                        
                        if agent != current_agent:
                            if current_agent:
                                print()  # Nueva línea entre agentes
                            current_agent = agent
                            print(colorize(f"\n🤖 {agent}: ", Colors.OKBLUE), end='', flush=True)
                        
                        # Imprimir token (limitado para no saturar)
                        if event_counts['agent_token'] % 10 == 0:
                            print(colorize(".", Colors.OKBLUE), end='', flush=True)
                    
                    elif event_type == 'agent_completed':
                        event_counts['agent_completed'] += 1
                        agent = payload.get('agent', 'unknown')
                        status = payload.get('status', 'unknown')
                        tokens = payload.get('tokens', 0)
                        icon = "✅" if status == "COMPLETED" else "❌"
                        print(colorize(f"\n{icon} {agent} completado ({tokens} tokens)", Colors.OKGREEN))
                        current_agent = None
                    
                    elif event_type == 'tribunal_started':
                        print(colorize("\n🏛️  Tribunal de Magistrados iniciado", Colors.HEADER + Colors.BOLD))
                    
                    elif event_type == 'tribunal_iteration':
                        iteration = payload.get('iteration', 1)
                        max_iter = payload.get('max_iterations', 3)
                        print(colorize(f"   Iteración PCO: {iteration}/{max_iter}", Colors.WARNING))
                    
                    elif event_type == 'tribunal_objection':
                        event_counts['tribunal_objection'] += 1
                        role = payload.get('role', 'unknown')
                        blocking = payload.get('blocking', False)
                        score = payload.get('score', 0)
                        icon = "🚫" if blocking else "⚠️"
                        print(colorize(f"   {icon} {role}: bloqueo={blocking}, score={score}", Colors.WARNING))
                    
                    elif event_type == 'tribunal_verdict':
                        event_counts['tribunal_verdict'] += 1
                        consensus = payload.get('consensus_reached', False)
                        iterations = payload.get('iterations', 0)
                        icon = "✅" if consensus else "⚠️"
                        print(colorize(f"\n{icon} Veredicto emitido (consenso={consensus}, iteraciones={iterations})", Colors.OKGREEN + Colors.BOLD))
                    
                    elif event_type == 'round_completed':
                        event_counts['round_completed'] += 1
                        round_num = payload.get('round_number', 0)
                        print(colorize(f"\n✅ Ronda {round_num} completada", Colors.OKGREEN + Colors.BOLD))
                    
                    elif event_type == 'convergence_evaluated':
                        level = payload.get('consensus_level', 'UNKNOWN')
                        score = payload.get('similarity_score', 0)
                        should_stop = payload.get('should_stop', False)
                        print(colorize(f"   Convergencia: {level} (score={score:.2f}, stop={should_stop})", Colors.OKCYAN))
                    
                    elif event_type == 'session_completed':
                        consensus_level = payload.get('consensus_level', 'UNKNOWN')
                        total_rounds = payload.get('rounds', 0)
                        print(colorize(f"\n🎉 Sesión completada: {consensus_level} en {total_rounds} ronda(s)", Colors.OKGREEN + Colors.BOLD))
                    
                    elif event_type == 'session_error':
                        error = payload.get('error', 'Unknown error')
                        print(colorize(f"\n❌ Error en sesión: {error}", Colors.FAIL))
                    
                    elif event_type == 'pong':
                        pass  # Ignorar heartbeats
                    
                except json.JSONDecodeError:
                    print(colorize(f"⚠️  Mensaje no JSON: {message[:100]}", Colors.WARNING))
                    
        except websockets.exceptions.ConnectionClosed:
            print(colorize("\n🔌 Conexión WebSocket cerrada", Colors.WARNING))
    
    # Conectar y escuchar
    try:
        async with websockets.connect(f"{ws_url}/{session_id}") as websocket:
            # Iniciar handler de eventos en background
            event_task = asyncio.create_task(handle_events(websocket))
            
            # Enviar pings periódicos para mantener conexión
            print(colorize("\n[3/4] Escuchando eventos en tiempo real...", Colors.OKBLUE))
            print(colorize("   (Presiona Ctrl+C para detener)\n", Colors.WARNING))
            
            try:
                while True:
                    await websocket.send(json.dumps({"type": "ping"}))
                    await asyncio.sleep(5)  # Ping cada 5 segundos
                    
                    # Verificar si sesión completó consultando API
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(f"{base_url}/api/v1/sessions/{session_id}")
                        if response.status_code == 200:
                            data = response.json()
                            session = data.get('session', {})
                            if session.get('status') == 'COMPLETED':
                                print(colorize("\n✅ Sesión completada detectada vía API", Colors.OKGREEN))
                                break
                            elif session.get('status') == 'FAILED':
                                print(colorize("\n❌ Sesión fallida detectada vía API", Colors.FAIL))
                                break
                                
            except asyncio.CancelledError:
                pass
            
            # Cancelar task de eventos
            event_task.cancel()
            try:
                await event_task
            except asyncio.CancelledError:
                pass
            
    except Exception as e:
        print(colorize(f"\n❌ Error WebSocket: {e}", Colors.FAIL))
        return
    
    # 4. Resultado final
    print(colorize("\n[4/4] Estadísticas del streaming:", Colors.OKBLUE))
    print(f"   Total eventos recibidos: {event_counts['total']}")
    print(f"   Tokens streaming: {event_counts['agent_token']}")
    print(f"   Agentes completados: {event_counts['agent_completed']}")
    print(f"   Fases completadas: {event_counts['phase_started']}")
    print(f"   Rondas completadas: {event_counts['round_completed']}")
    print(f"   Objeciones del Tribunal: {event_counts['tribunal_objection']}")
    print(f"   Veredictos emitidos: {event_counts['tribunal_verdict']}")
    
    print("\n" + "="*70)
    if event_counts['total'] > 0:
        print(colorize("✅ TEST WEBSOCKET PASADO", Colors.OKGREEN + Colors.BOLD))
        print(f"   Streaming funcionando correctamente!")
        print(f"   Eventos recibidos: {event_counts['total']}")
    else:
        print(colorize("⚠️  TEST WEBSOCKET INCONCLUSO", Colors.WARNING))
        print(f"   No se recibieron eventos (¿la sesión ya terminó?)")
    print("="*70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test WebSocket Synapse Council v2.0')
    parser.add_argument('--rounds', type=int, default=1, help='Número de rondas (1-3)')
    args = parser.parse_args()
    
    try:
        asyncio.run(test_websocket_streaming(rounds=args.rounds))
    except KeyboardInterrupt:
        print(colorize("\n\n⚠️  Test interrumpido por usuario", Colors.WARNING))
    except Exception as e:
        print(colorize(f"\n❌ Error: {e}", Colors.FAIL))
        import traceback
        traceback.print_exc()
