"""
Lanzador de debate masivo v2 - ESTRATEGIAS AGRESIVAS CORTO PLAZO
Usa TODOS los modelos disponibles en Worker
Tema: Metodos agresivos para generar capital rapido con minima inversion
"""
import asyncio
import aiohttp
import json
from datetime import datetime

WORKER_URL = "http://localhost:8000/api/v1"

TOPIC = """Mejores metodos para generar capital de manera rapida con una minima inversion

CONDICION OBLIGATORIA: Este debate DEBE enfocarse en estrategias AGRESIVAS a corto plazo (dias/semanas), metodos mixtos o alternativas concretas de alto rendimiento. NO se aceptan recomendaciones conservadoras como "ahorrar regularmente" o "invertir en bonos". Se buscan metodos de accion inmediata: trading de alta frecuencia, arbitraje, flipping digital, micro-SaaS, dropshipping agresivo, cripto DeFi, apuestas deportivas con modelos estadisticos, reventa de entradas, servicios de urgencia premium, etc. Cada agente DEBE proponer al menos una estrategia concreta con pasos accionables, capital inicial estimado, y retorno esperado en dias/semanas."""

# Contexto del debate anterior (v1 conservador) para que los agentes lo superen
PREVIOUS_VERDICT = """En el debate anterior se recomendo: 1) Planificar y ahorrar regularmente, 2) Invertir en activos de bajo rendimiento (bonos, depositos a plazo), 3) Usar asesores digitales. Estas recomendaciones fueron consideradas DEMASIADO CONSERVADORAS y de largo plazo. Este debate debe ir MAS ALLA y proponer metodos AGRESIVOS de corto plazo."""

# TODOS los modelos disponibles en el Worker
ALL_MODELS = [
    {"model": "llama3:8b", "provider": "meta", "name": "Llama3 8B"},
    {"model": "llama3.1:8b", "provider": "meta", "name": "Llama3.1 8B"},
    {"model": "mistral:7b", "provider": "mistral", "name": "Mistral 7B"},
    {"model": "gemma:7b", "provider": "google", "name": "Gemma 7B"},
    {"model": "gemma3:4b", "provider": "google", "name": "Gemma3 4B"},
    {"model": "gemma4:latest", "provider": "google", "name": "Gemma4"},
    {"model": "qwen2.5:3b", "provider": "alibaba", "name": "Qwen2.5 3B"},
    {"model": "qwen2.5-coder:14b", "provider": "alibaba", "name": "Qwen2.5-Coder 14B"},
    {"model": "deepseek-r1:7b", "provider": "deepseek", "name": "DeepSeek-R1 7B"},
    {"model": "phi3:mini", "provider": "microsoft", "name": "Phi3 Mini"},
    {"model": "nemotron-mini:latest", "provider": "nvidia", "name": "Nemotron Mini"},
    {"model": "tinyllama:latest", "provider": "meta", "name": "TinyLlama"},
]

ROLES = ["analyst", "critic", "synthesizer", "refiner", "validator", "moderator"]

SYSTEM_PROMPTS = {
    "analyst": f"""Analiza el tema propuesto desde una perspectiva AGRESIVA y de ACCION INMEDIATA.
IDENTIFICA metodos de generacion de capital a corto plazo (dias/semanas) con minima inversion inicial.
Contexto: El debate anterior fue demasiado conservador (ahorro, bonos). AHORA se buscan estrategias agresivas.
CADA agente debe proponer al menos una estrategia concreta con: capital inicial estimado, retorno esperado en dias/semanas, y pasos accionables.
Responde en espanol, maximo 500 palabras.""",

    "critic": f"""Examina criticamente las estrategias agresivas propuestas. Identifica riesgos reales, probabilidades de exito, y alternativas mas eficientes.
NO rechaces las estrategias por ser "arriesgadas" - en su lugar, analiza el ratio riesgo/beneficio y propone mitigaciones concretas.
Se riguroso pero constructivo. Responde en espanol, maximo 500 palabras.""",

    "synthesizer": f"""Sintetiza las estrategias agresivas presentadas. Crea un PLAN DE ACCION INTEGRADO que combine los mejores metodos de corto plazo.
Prioriza estrategias con: menor capital inicial, retorno mas rapido, y mayor probabilidad de exito verificable.
Responde en espanol, maximo 500 palabras.""",

    "refiner": f"""Refina el plan de accion integrado. Convierte las estrategias en un CALENDARIO EJECUTABLE dia a dia para las primeras 2-4 semanas.
Incluye: capital necesario por fase, metricas de exito, puntos de salida (stop-loss), y escalamiento.
Responde en espanol, maximo 600 palabras.""",

    "validator": f"""Valida la viabilidad REAL de cada estrategia agresiva propuesta. Verifica:
- Que el capital inicial sea realmente minimo (<$500)
- Que el retorno en dias/semanas sea realista (no promesas falsas)
- Que existan casos de exito documentados
- Que los riesgos sean manejables
Responde en espanol, maximo 400 palabras.""",

    "moderator": f"""Modera el debate, resume las posiciones encontradas y propone un CONSENSO sobre las mejores estrategias agresivas.
Crea un ranking final de metodos ordenados por: velocidad de retorno / riesgo / capital necesario.
Responde en espanol, maximo 500 palabras.""",
}


def build_massive_agents():
    """Crea una configuracion con TODOS los modelos en TODOS los roles"""
    agents = []
    agent_idx = 0

    # Cada modelo pasa por todos los roles
    for model_info in ALL_MODELS:
        for role in ROLES:
            agents.append({
                "id": f"agent_{agent_idx}",
                "name": f"{model_info['name']} ({role.title()})",
                "role": role,
                "node": "LOCAL",
                "engine": "ollama",
                "model": model_info["model"],
                "provider": model_info["provider"],
                "system_prompt": SYSTEM_PROMPTS[role],
                "temperature": 0.8 if role == "analyst" else 0.9 if role == "critic" else 0.7,
                "max_tokens": 1200,
            })
            agent_idx += 1

    return agents


async def launch_massive_debate():
    """Lanza el debate masivo y monitorea el progreso"""
    agents = build_massive_agents()

    print(f"=" * 80)
    print(f"DEBATE MASIVO v2 - ESTRATEGIAS AGRESIVAS CORTO PLAZO")
    print(f"Synapse Council v2.8")
    print(f"=" * 80)
    print(f"Tema: {TOPIC[:120]}...")
    print(f"Modelos: {len(ALL_MODELS)}")
    print(f"Roles: {len(ROLES)}")
    print(f"Total de agentes/turnos: {len(agents)}")
    print(f"Temperatura: 0.8-0.9 (creatividad alta)")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 80)

    async with aiohttp.ClientSession() as session:
        # Crear debate
        payload = {
            "topic": TOPIC,
            "mode": "custom",
            "agents": agents,
            "include_cloud": False,
        }

        print("\n[Lanzando debate masivo v2...]")
        start_time = datetime.now()

        async with session.post(f"{WORKER_URL}/debates/create", json=payload) as resp:
            if resp.status not in (200, 202):
                text = await resp.text()
                print(f"Error al crear debate: {resp.status} - {text}")
                return

            result = await resp.json()
            session_id = result["session_id"]
            print(f"Session ID: {session_id}")
            print(f"Estado: {result['status']}")
            print(f"Turnos totales: {result.get('total_turns', len(agents))}")

        # Monitorear progreso
        print("\n[Monitoreando progreso...]")
        completed = 0
        total = len(agents)
        last_completed = 0

        while True:
            await asyncio.sleep(15)

            async with session.get(f"{WORKER_URL}/debates/{session_id}") as resp:
                if resp.status == 404:
                    print("Debate aun no disponible, esperando...")
                    continue

                data = await resp.json()
                status = data.get("status", "unknown")
                turns = data.get("turns", [])
                completed = len([t for t in turns if t.get("status", "").startswith("completed")])

                # Mostrar nuevos turnos completados
                if completed > last_completed:
                    for turn in turns[last_completed:completed]:
                        if turn.get("status", "").startswith("completed"):
                            agent_name = turn.get("agent_name", "Unknown")
                            model = turn.get("model", "Unknown")
                            tokens = turn.get("tokens_out", 0)
                            latency = turn.get("latency_ms", 0)
                            preview = turn.get("response_preview", "")[:80]
                            print(f"  [{completed}/{total}] {agent_name} ({model}) - {tokens}tok, {latency}ms")
                            print(f"       > {preview}...")
                    last_completed = completed

                if status in ("completed", "failed", "error"):
                    print(f"\n{'=' * 80}")
                    print(f"DEBATE FINALIZADO - Estado: {status}")
                    print(f"{'=' * 80}")

                    elapsed = datetime.now() - start_time
                    print(f"Tiempo total: {elapsed}")
                    print(f"Turnos completados: {completed}/{total}")

                    # Estadisticas
                    total_tokens_in = sum(t.get("tokens_in", 0) for t in turns)
                    total_tokens_out = sum(t.get("tokens_out", 0) for t in turns)
                    total_latency = sum(t.get("latency_ms", 0) for t in turns)

                    print(f"Tokens entrada: {total_tokens_in:,}")
                    print(f"Tokens salida: {total_tokens_out:,}")
                    print(f"Latencia total: {total_latency:,}ms ({total_latency/1000:.1f}s)")
                    print(f"Promedio por turno: {total_latency/max(completed,1):.0f}ms")

                    # Veredicto final
                    verdict = data.get("final_verdict")
                    if verdict:
                        print(f"\n{'=' * 80}")
                        print(f"VEREDICTO FINAL - ESTRATEGIAS AGRESIVAS:")
                        print(f"{'=' * 80}")
                        print(verdict[:3000])
                        if len(verdict) > 3000:
                            print("...")

                    # Exportar
                    print(f"\n[Exportando resultados...]")

                    # JSON
                    async with session.get(f"{WORKER_URL}/debates/{session_id}/export/json") as resp:
                        if resp.status == 200:
                            json_data = await resp.json()
                            with open(f"debate_aggressive_{session_id[:8]}.json", "w", encoding="utf-8") as f:
                                json.dump(json_data, f, indent=2, ensure_ascii=False)
                            print(f"  [OK] JSON exportado: debate_aggressive_{session_id[:8]}.json")

                    # Markdown
                    async with session.get(f"{WORKER_URL}/debates/{session_id}/export/markdown") as resp:
                        if resp.status == 200:
                            md_data = await resp.text()
                            with open(f"debate_aggressive_{session_id[:8]}.md", "w", encoding="utf-8") as f:
                                f.write(md_data)
                            print(f"  [OK] Markdown exportado: debate_aggressive_{session_id[:8]}.md")

                    # DOCX
                    async with session.get(f"{WORKER_URL}/debates/{session_id}/export/docx") as resp:
                        if resp.status == 200:
                            docx_data = await resp.read()
                            with open(f"debate_aggressive_{session_id[:8]}.docx", "wb") as f:
                                f.write(docx_data)
                            print(f"  [OK] DOCX exportado: debate_aggressive_{session_id[:8]}.docx")

                    break

                else:
                    pct = completed*100//total
                    print(f"  Progreso: {completed}/{total} ({pct}%) - Estado: {status}")


if __name__ == "__main__":
    asyncio.run(launch_massive_debate())
