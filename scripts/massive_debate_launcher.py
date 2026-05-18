"""
Lanzador de debate masivo - usa TODOS los modelos disponibles en Worker
Tema: Mejores metodos para generar capital de manera rapida con minima inversion
"""
import asyncio
import aiohttp
import json
from datetime import datetime

WORKER_URL = "http://localhost:8000/api/v1"

TOPIC = "Mejores metodos para generar capital de manera rapida con una minima inversion"

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
    "analyst": "Analiza el tema propuesto desde una perspectiva tecnica y estructurada. Identifica los puntos clave, supuestos y posibles enfoques. Responde en espanol, maximo 500 palabras.",
    "critic": "Examina criticamente el analisis anterior. Identifica debilidades logicas, supuestos no verificados y alternativas no consideradas. Se constructivo pero riguroso. Responde en espanol, maximo 500 palabras.",
    "synthesizer": "Sintetiza los argumentos presentados hasta ahora. Encuentra puntos de acuerdo y desacuerdo. Propone un marco integrador. Responde en espanol, maximo 500 palabras.",
    "refiner": "Refina y mejora la sintesis anterior. Considera perspectivas adicionales y elabora una conclusion bien fundamentada. Responde en espanol, maximo 600 palabras.",
    "validator": "Valida la solidez logica de todos los argumentos presentados. Verifica consistencia interna y externa. Responde en espanol, maximo 400 palabras.",
    "moderator": "Modera el debate, resume las posiciones encontradas y propone areas de consenso. Responde en espanol, maximo 500 palabras.",
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
                "temperature": 0.7 if role == "analyst" else 0.8 if role == "critic" else 0.6,
                "max_tokens": 1000,
            })
            agent_idx += 1

    return agents


async def launch_massive_debate():
    """Lanza el debate masivo y monitorea el progreso"""
    agents = build_massive_agents()

    print(f"=" * 80)
    print(f"DEBATE MASIVO - Synapse Council v2.8")
    print(f"=" * 80)
    print(f"Tema: {TOPIC}")
    print(f"Modelos: {len(ALL_MODELS)}")
    print(f"Roles: {len(ROLES)}")
    print(f"Total de agentes/turnos: {len(agents)}")
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

        print("\n[Lanzando debate masivo...]")
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

                # Mostrar ultimo turno completado
                if turns:
                    last_turn = turns[-1]
                    if last_turn.get("status", "").startswith("completed"):
                        agent_name = last_turn.get("agent_name", "Unknown")
                        model = last_turn.get("model", "Unknown")
                        tokens = last_turn.get("tokens_out", 0)
                        latency = last_turn.get("latency_ms", 0)
                        print(f"  [OK] Turn {completed}/{total}: {agent_name} ({model}) - {tokens} tokens, {latency}ms")

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
                        print(f"VEREDICTO FINAL:")
                        print(f"{'=' * 80}")
                        print(verdict[:2000])
                        if len(verdict) > 2000:
                            print("...")

                    # Exportar
                    print(f"\n[Exportando resultados...]")

                    # JSON
                    async with session.get(f"{WORKER_URL}/debates/{session_id}/export/json") as resp:
                        if resp.status == 200:
                            json_data = await resp.json()
                            with open(f"debate_massive_{session_id[:8]}.json", "w", encoding="utf-8") as f:
                                json.dump(json_data, f, indent=2, ensure_ascii=False)
                            print(f"  [OK] JSON exportado: debate_massive_{session_id[:8]}.json")

                    # Markdown
                    async with session.get(f"{WORKER_URL}/debates/{session_id}/export/markdown") as resp:
                        if resp.status == 200:
                            md_data = await resp.text()
                            with open(f"debate_massive_{session_id[:8]}.md", "w", encoding="utf-8") as f:
                                f.write(md_data)
                            print(f"  [OK] Markdown exportado: debate_massive_{session_id[:8]}.md")

                    # DOCX
                    async with session.get(f"{WORKER_URL}/debates/{session_id}/export/docx") as resp:
                        if resp.status == 200:
                            docx_data = await resp.read()
                            with open(f"debate_massive_{session_id[:8]}.docx", "wb") as f:
                                f.write(docx_data)
                            print(f"  [OK] DOCX exportado: debate_massive_{session_id[:8]}.docx")

                    break

                else:
                    print(f"  Progreso: {completed}/{total} ({completed*100//total}%) - Estado: {status}")


if __name__ == "__main__":
    asyncio.run(launch_massive_debate())
