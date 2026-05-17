"""
Descarga datos de reputación y modelos desde Supabase para análisis.
"""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

import httpx

SUPABASE_URL = "https://jdbzjapshomatwyasmig.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkYnpqYXBzaG9tYXR3eWFzbWlnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM4ODAzNzMsImV4cCI6MjA3OTQ1NjM3M30.AmHDH1dmJ3qme8VYN1EU3zjf7zZAKESal5NXWhX-KMk"


async def download_supabase_data():
    client = httpx.AsyncClient(
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    )

    print("[DOWNLOAD] Downloading sequential_debates...")
    debates_resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/sequential_debates?select=*&order=created_at.desc&limit=1000"
    )
    debates = debates_resp.json() if debates_resp.status_code == 200 else []
    print(f"    Got {len(debates)} debates")

    print("[DOWNLOAD] Downloading sequential_debate_turns...")
    turns_resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/sequential_debate_turns?select=*&order=turn_number.asc&limit=10000"
    )
    turns = turns_resp.json() if turns_resp.status_code == 200 else []
    print(f"    Got {len(turns)} turns")

    print("[DOWNLOAD] Downloading consensus_debates...")
    consensus_resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/consensus_debates?select=*&order=created_at.desc&limit=1000"
    )
    consensus = consensus_resp.json() if consensus_resp.status_code == 200 else []
    print(f"    Got {len(consensus)} consensus debates")

    await client.aclose()

    # Analisis de modelos y roles
    print("\n[ANALYSIS] Model usage in Supabase turns:")
    model_counts = Counter(t.get("model", "unknown") for t in turns)
    for model, count in model_counts.most_common(20):
        print(f"    {model}: {count} turns")

    print("\n[ANALYSIS] Role distribution:")
    role_counts = Counter(t.get("agent_role", "unknown") for t in turns)
    for role, count in role_counts.most_common():
        print(f"    {role}: {count}")

    print("\n[ANALYSIS] Provider distribution:")
    provider_counts = Counter(t.get("provider", "unknown") for t in turns)
    for prov, count in provider_counts.most_common():
        print(f"    {prov}: {count}")

    print("\n[ANALYSIS] Engine distribution:")
    engine_counts = Counter(t.get("engine", "unknown") for t in turns)
    for eng, count in engine_counts.most_common():
        print(f"    {eng}: {count}")

    print("\n[ANALYSIS] Debate status distribution:")
    status_counts = Counter(d.get("status", "unknown") for d in debates)
    for status, count in status_counts.most_common():
        print(f"    {status}: {count}")

    print("\n[ANALYSIS] Debate mode distribution:")
    mode_counts = Counter(d.get("mode", "unknown") for d in debates)
    for mode, count in mode_counts.most_common():
        print(f"    {mode}: {count}")

    # Guardar datos
    output = {
        "debates": debates,
        "turns": turns,
        "consensus": consensus,
        "model_counts": dict(model_counts),
        "role_counts": dict(role_counts),
        "provider_counts": dict(provider_counts),
        "engine_counts": dict(engine_counts),
    }
    output_path = Path(__file__).parent / "supabase_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)
    print(f"\n[SAVE] Data saved to: {output_path}")
    print(f"    File size: {output_path.stat().st_size / 1024:.1f} KB")

    return output


async def main():
    await download_supabase_data()


if __name__ == "__main__":
    asyncio.run(main())
