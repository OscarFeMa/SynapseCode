"""
Script de auditoría: Supabase vs SQLite
Compara esquemas, datos y reputación entre ambas bases de datos.
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import httpx

SUPABASE_URL = "https://jdbzjapshomatwyasmig.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkYnpqYXBzaG9tYXR3eWFzbWlnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM4ODAzNzMsImV4cCI6MjA3OTQ1NjM3M30.AmHDH1dmJ3qme8VYN1EU3zjf7zZAKESal5NXWhX-KMk"
SQLITE_PATH = Path(__file__).parent.parent / "data" / "synapse.db"


async def audit_supabase():
    """Lee esquema y conteos de Supabase"""
    print("=" * 60)
    print("SUPABASE AUDIT")
    print("=" * 60)

    client = httpx.AsyncClient(
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )

    # Tablas conocidas
    tables = [
        "sequential_debates",
        "sequential_debate_turns",
        "consensus_debates",
        "consensus_rounds",
        "consensus_agent_positions",
        "reductio_absurdum_proofs",
    ]

    results = {}

    for table in tables:
        # Obtener schema
        schema_resp = await client.get(f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=0")
        headers_info = schema_resp.headers.get("x-schema", "unknown")

        # Obtener conteo
        count_resp = await client.get(f"{SUPABASE_URL}/rest/v1/{table}?select=id&limit=1")
        has_data = count_resp.status_code == 200

        # Obtener una muestra para ver columnas
        sample_resp = await client.get(f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1")
        columns = list(sample_resp.json()[0].keys()) if sample_resp.status_code == 200 and sample_resp.json() else []

        # Conteo real (count exact)
        count_resp2 = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table}?select=*",
            headers={"Prefer": "count=exact", "Range": "0-0"},
        )
        content_range = count_resp2.headers.get("content-range", "unknown")

        results[table] = {
            "status": count_resp.status_code,
            "columns": columns,
            "count_header": content_range,
            "has_data": has_data,
        }

        print(f"\n[TABLE] {table}")
        print(f"    Status: {count_resp.status_code}")
        print(f"    Count: {content_range}")
        print(f"    Columns: {', '.join(columns)}")

    # Intentar descubrir tablas adicionales
    print("\n\n[DISCOVER] Buscando tablas adicionales...")
    for extra_table in [
        "model_reputation",
        "agent_reputation",
        "sessions",
        "rounds",
        "agent_calls",
        "debates_aggregate",
        "topics_trending",
        "consensus_patterns",
        "model_performance",
        "daily_metrics_snapshot",
        "prompt_response_cache",
        "supabase_sync_queue",
        "system_events",
        "cross_references",
        "config_profiles",
    ]:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/{extra_table}?select=id&limit=1")
        status = "[OK]" if resp.status_code in [200, 404] else "[NOT FOUND]"
        print(f"    {extra_table}: {status} ({resp.status_code})")

    await client.aclose()
    return results


def audit_sqlite():
    """Lee esquema y conteos de SQLite local"""
    print("\n" + "=" * 60)
    print("SQLITE LOCAL AUDIT")
    print("=" * 60)

    if not SQLITE_PATH.exists():
        print(f"[ERROR] SQLite DB not found at {SQLITE_PATH}")
        return {}

    conn = sqlite3.connect(str(SQLITE_PATH))
    cursor = conn.cursor()

    # Listar tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    results = {}

    for table in tables:
        # Conteo
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]

        # Columnas
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]

        results[table] = {"count": count, "columns": columns}

        print(f"\n[TABLE] {table}")
        print(f"    Rows: {count}")
        print(f"    Columns ({len(columns)}): {', '.join(columns)}")

    conn.close()
    return results


def compare_schemas(supabase, sqlite):
    """Compara esquemas y muestra diferencias"""
    print("\n" + "=" * 60)
    print("SCHEMA COMPARISON")
    print("=" * 60)

    all_tables = set(list(supabase.keys()) + list(sqlite.keys()))

    for table in sorted(all_tables):
        in_supa = table in supabase
        in_sqlite = table in sqlite

        if in_supa and in_sqlite:
            supa_cols = set(supabase[table].get("columns", []))
            sqlite_cols = set(sqlite[table].get("columns", []))

            common = supa_cols & sqlite_cols
            only_supa = supa_cols - sqlite_cols
            only_sqlite = sqlite_cols - supa_cols

            status = "[MATCH]" if not only_supa and not only_sqlite else "[DIFF]"
            print(f"\n{status} {table}")
            print(f"    Supabase: {supabase[table].get('count_header', 'N/A')} rows")
            print(f"    SQLite:   {sqlite[table].get('count', 0)} rows")
            if only_supa:
                print(f"    Only in Supabase: {', '.join(only_supa)}")
            if only_sqlite:
                print(f"    Only in SQLite:   {', '.join(only_sqlite)}")
        elif in_supa:
            print(f"\n[CLOUD] {table} (Supabase only)")
        else:
            print(f"\n[LOCAL] {table} (SQLite only)")


async def main():
    print("[AUDIT] Synapse Database Audit")
    print(f"Supabase: {SUPABASE_URL}")
    print(f"SQLite:   {SQLITE_PATH}")
    print()

    supabase = await audit_supabase()
    sqlite = audit_sqlite()
    compare_schemas(supabase, sqlite)

    # Guardar resultado
    output = {
        "supabase": supabase,
        "sqlite": sqlite,
    }
    output_path = Path(__file__).parent / "audit_result.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[REPORT] Full report saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
