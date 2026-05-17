"""
Migración de bases de datos: Supabase → SQLite unificado

Pasos:
1. Backup de SQLite actual
2. Descargar datos de Supabase
3. Alinear esquema SQLite con Supabase (añadir synced_at)
4. Importar debates y turns desde Supabase
5. Recalcular reputación EMA desde datos históricos
6. Limpiar tablas vacías/obsoletas
"""

import asyncio
import json
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import httpx

SUPABASE_URL = "https://jdbzjapshomatwyasmig.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkYnpqYXBzaG9tYXR3eWFzbWlnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM4ODAzNzMsImV4cCI6MjA3OTQ1NjM3M30.AmHDH1dmJ3qme8VYN1EU3zjf7zZAKESal5NXWhX-KMk"
SQLITE_PATH = Path(__file__).parent.parent / "data" / "synapse.db"
BACKUP_PATH = Path(__file__).parent.parent / "data" / "synapse.db.backup"


def log(msg):
    print(f"[MIGRATE] {msg}")


def backup_database():
    if SQLITE_PATH.exists():
        shutil.copy2(SQLITE_PATH, BACKUP_PATH)
        log(f"Backup created: {BACKUP_PATH}")
    else:
        log(f"No SQLite DB found at {SQLITE_PATH}")


async def download_from_supabase():
    client = httpx.AsyncClient(
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    )

    log("Downloading sequential_debates...")
    resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/sequential_debates?select=*&order=created_at.desc&limit=1000"
    )
    debates = resp.json() if resp.status_code == 200 else []
    log(f"  Downloaded {len(debates)} debates")

    log("Downloading sequential_debate_turns...")
    resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/sequential_debate_turns?select=*&order=turn_number.asc&limit=10000"
    )
    turns = resp.json() if resp.status_code == 200 else []
    log(f"  Downloaded {len(turns)} turns")

    log("Downloading consensus_debates...")
    resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/consensus_debates?select=*&order=created_at.desc&limit=100"
    )
    consensus = resp.json() if resp.status_code == 200 else []
    log(f"  Downloaded {len(consensus)} consensus debates")

    log("Downloading consensus_rounds...")
    resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/consensus_rounds?select=*&limit=1000"
    )
    consensus_rounds = resp.json() if resp.status_code == 200 else []
    log(f"  Downloaded {len(consensus_rounds)} consensus rounds")

    log("Downloading consensus_agent_positions...")
    resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/consensus_agent_positions?select=*&limit=1000"
    )
    consensus_positions = resp.json() if resp.status_code == 200 else []
    log(f"  Downloaded {len(consensus_positions)} consensus positions")

    await client.aclose()

    return {
        "debates": debates,
        "turns": turns,
        "consensus_debates": consensus,
        "consensus_rounds": consensus_rounds,
        "consensus_positions": consensus_positions,
    }


def align_schema(conn):
    log("Aligning schema...")
    cursor = conn.cursor()

    # Añadir synced_at a sequential_debates si no existe
    cursor.execute("PRAGMA table_info(sequential_debates)")
    cols = [row[1] for row in cursor.fetchall()]
    if "synced_at" not in cols:
        cursor.execute("ALTER TABLE sequential_debates ADD COLUMN synced_at TEXT")
        log("  Added synced_at to sequential_debates")

    # Añadir synced_at a sequential_debate_turns si no existe
    cursor.execute("PRAGMA table_info(sequential_debate_turns)")
    cols = [row[1] for row in cursor.fetchall()]
    if "synced_at" not in cols:
        cursor.execute("ALTER TABLE sequential_debate_turns ADD COLUMN synced_at TEXT")
        log("  Added synced_at to sequential_debate_turns")

    # Añadir synced_at a consensus_debates si no existe
    cursor.execute("PRAGMA table_info(consensus_debates)")
    cols = [row[1] for row in cursor.fetchall()]
    if "synced_at" not in cols:
        cursor.execute("ALTER TABLE consensus_debates ADD COLUMN synced_at TEXT")
        log("  Added synced_at to consensus_debates")

    # Añadir synced_at a consensus_rounds si no existe
    cursor.execute("PRAGMA table_info(consensus_rounds)")
    cols = [row[1] for row in cursor.fetchall()]
    if "synced_at" not in cols:
        cursor.execute("ALTER TABLE consensus_rounds ADD COLUMN synced_at TEXT")
        log("  Added synced_at to consensus_rounds")

    # Añadir synced_at y round_number a consensus_agent_positions
    cursor.execute("PRAGMA table_info(consensus_agent_positions)")
    cols = [row[1] for row in cursor.fetchall()]
    if "synced_at" not in cols:
        cursor.execute("ALTER TABLE consensus_agent_positions ADD COLUMN synced_at TEXT")
        log("  Added synced_at to consensus_agent_positions")
    if "round_number" not in cols:
        cursor.execute("ALTER TABLE consensus_agent_positions ADD COLUMN round_number INTEGER DEFAULT 0")
        log("  Added round_number to consensus_agent_positions")

    # Hacer round_id nullable en consensus_agent_positions (Supabase usa round_number)
    # SQLite no soporta ALTER COLUMN, asi que recreamos la tabla
    cursor.execute("PRAGMA table_info(consensus_agent_positions)")
    col_info = {row[1]: row for row in cursor.fetchall()}
    if col_info.get("round_id", {}).__getitem__(3) == 1:  # notnull = 1
        log("  Making consensus_agent_positions.round_id nullable...")
        cursor.execute("BEGIN")
        cursor.execute("ALTER TABLE consensus_agent_positions RENAME TO consensus_agent_positions_old")
        cursor.execute(
            """CREATE TABLE consensus_agent_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debate_id VARCHAR(36) NOT NULL,
                round_id INTEGER,
                round_number INTEGER DEFAULT 0,
                agent_id VARCHAR(50) NOT NULL,
                agent_name VARCHAR(100) NOT NULL,
                agent_role VARCHAR(20) NOT NULL,
                position_text TEXT NOT NULL,
                confidence FLOAT NOT NULL,
                consensus_score FLOAT NOT NULL,
                supporting_points JSON,
                objections_raised JSON,
                logical_fallacies JSON,
                created_at DATETIME NOT NULL,
                synced_at TEXT
            )"""
        )
        cursor.execute(
            """INSERT INTO consensus_agent_positions
               SELECT id, debate_id, round_id, COALESCE(round_number, 0), agent_id,
                      agent_name, agent_role, position_text, confidence, consensus_score,
                      supporting_points, objections_raised, logical_fallacies,
                      created_at, synced_at
               FROM consensus_agent_positions_old"""
        )
        cursor.execute("DROP TABLE consensus_agent_positions_old")
        cursor.execute("COMMIT")
        log("  consensus_agent_positions.round_id is now nullable")

    conn.commit()


def _safe_timestamp(val, fallback=None):
    if val:
        return val
    if fallback:
        return fallback
    return datetime.now(UTC).isoformat()


def import_debates(conn, debates):
    log(f"Importing {len(debates)} debates...")
    cursor = conn.cursor()
    imported = 0
    skipped = 0

    for d in debates:
        created = _safe_timestamp(d.get("created_at"), d.get("synced_at"))
        completed = _safe_timestamp(d.get("completed_at"), d.get("synced_at"))

        cursor.execute("SELECT id FROM sequential_debates WHERE id = ?", (d["id"],))
        if cursor.fetchone():
            cursor.execute(
                """UPDATE sequential_debates SET
                   topic=?, mode=?, status=?, total_turns=?, total_tokens_in=?,
                   total_tokens_out=?, total_latency_ms=?, final_verdict=?,
                   transcript_path=?, created_at=?, completed_at=?, synced_at=?
                   WHERE id=?""",
                (
                    d.get("topic"),
                    d.get("mode"),
                    d.get("status"),
                    d.get("total_turns", 0),
                    d.get("total_tokens_in", 0),
                    d.get("total_tokens_out", 0),
                    d.get("total_latency_ms", 0),
                    d.get("final_verdict"),
                    d.get("transcript_path"),
                    created,
                    completed,
                    d.get("synced_at"),
                    d["id"],
                ),
            )
            skipped += 1
        else:
            cursor.execute(
                """INSERT INTO sequential_debates
                   (id, topic, mode, status, total_turns, total_tokens_in, total_tokens_out,
                    total_latency_ms, final_verdict, transcript_path, created_at, completed_at,
                    paused_at, pause_reason, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    d["id"],
                    d.get("topic"),
                    d.get("mode", "standard"),
                    d.get("status", "completed"),
                    d.get("total_turns", 0),
                    d.get("total_tokens_in", 0),
                    d.get("total_tokens_out", 0),
                    d.get("total_latency_ms", 0),
                    d.get("final_verdict"),
                    d.get("transcript_path"),
                    created,
                    completed,
                    None,
                    None,
                    d.get("synced_at"),
                ),
            )
            imported += 1

    conn.commit()
    log(f"  Imported: {imported}, Updated: {skipped}")


def import_turns(conn, turns):
    log(f"Importing {len(turns)} turns...")
    cursor = conn.cursor()
    imported = 0
    skipped = 0

    for t in turns:
        started = _safe_timestamp(t.get("started_at"), t.get("synced_at"))
        completed = _safe_timestamp(t.get("completed_at"), t.get("synced_at"))

        cursor.execute("SELECT id FROM sequential_debate_turns WHERE id = ?", (t["id"],))
        if cursor.fetchone():
            cursor.execute(
                """UPDATE sequential_debate_turns SET
                   debate_id=?, turn_number=?, agent_id=?, agent_name=?, agent_role=?,
                   model=?, provider=?, node=?, engine=?, prompt_sent=?, response_received=?,
                   tokens_in=?, tokens_out=?, latency_ms=?, status=?, error_message=?,
                   started_at=?, completed_at=?, synced_at=?
                   WHERE id=?""",
                (
                    t.get("debate_id"),
                    t.get("turn_number"),
                    t.get("agent_id"),
                    t.get("agent_name"),
                    t.get("agent_role"),
                    t.get("model"),
                    t.get("provider"),
                    t.get("node"),
                    t.get("engine"),
                    t.get("prompt_sent", "")[:10000],
                    t.get("response_received", "")[:20000],
                    t.get("tokens_in", 0),
                    t.get("tokens_out", 0),
                    t.get("latency_ms", 0),
                    t.get("status"),
                    t.get("error_message"),
                    started,
                    completed,
                    t.get("synced_at"),
                    t["id"],
                ),
            )
            skipped += 1
        else:
            cursor.execute(
                """INSERT INTO sequential_debate_turns
                   (id, debate_id, turn_number, agent_id, agent_name, agent_role,
                    model, provider, node, engine, prompt_sent, response_received,
                    tokens_in, tokens_out, latency_ms, status, error_message,
                    started_at, completed_at, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    t["id"],
                    t.get("debate_id"),
                    t.get("turn_number"),
                    t.get("agent_id"),
                    t.get("agent_name"),
                    t.get("agent_role"),
                    t.get("model"),
                    t.get("provider"),
                    t.get("node"),
                    t.get("engine"),
                    t.get("prompt_sent", "")[:10000],
                    t.get("response_received", "")[:20000],
                    t.get("tokens_in", 0),
                    t.get("tokens_out", 0),
                    t.get("latency_ms", 0),
                    t.get("status"),
                    t.get("error_message"),
                    started,
                    completed,
                    t.get("synced_at"),
                ),
            )
            imported += 1

    conn.commit()
    log(f"  Imported: {imported}, Updated: {skipped}")


def import_consensus(conn, consensus_data):
    log("Importing consensus data...")
    cursor = conn.cursor()

    for d in consensus_data.get("consensus_debates", []):
        cursor.execute("SELECT id FROM consensus_debates WHERE id = ?", (d["id"],))
        if not cursor.fetchone():
            cursor.execute(
                """INSERT INTO consensus_debates
                   (id, topic, status, total_agents, max_rounds, consensus_score,
                    final_consensus, bias_analysis, transcript_path, total_tokens_in,
                    total_tokens_out, total_latency_ms, created_at, completed_at, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    d["id"],
                    d.get("topic"),
                    d.get("status"),
                    d.get("total_agents", 0),
                    d.get("max_rounds", 5),
                    d.get("consensus_score"),
                    d.get("final_consensus"),
                    json.dumps(d.get("bias_analysis")) if d.get("bias_analysis") else None,
                    d.get("transcript_path"),
                    d.get("total_tokens_in", 0),
                    d.get("total_tokens_out", 0),
                    d.get("total_latency_ms", 0),
                    _safe_timestamp(d.get("created_at"), d.get("synced_at")),
                    _safe_timestamp(d.get("completed_at"), d.get("synced_at")),
                    d.get("synced_at"),
                ),
            )

    for r in consensus_data.get("consensus_rounds", []):
        cursor.execute(
            "SELECT id FROM consensus_rounds WHERE id = ?",
            (r["id"],),
        )
        if not cursor.fetchone():
            cursor.execute(
                """INSERT INTO consensus_rounds
                   (id, debate_id, round_number, round_type, global_consensus_score,
                    converged, dissent_topics, created_at, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["id"],
                    r.get("debate_id"),
                    r.get("round_number"),
                    r.get("round_type"),
                    r.get("global_consensus_score"),
                    r.get("converged", False),
                    json.dumps(r.get("dissent_topics")) if r.get("dissent_topics") else None,
                    _safe_timestamp(r.get("created_at"), r.get("synced_at")),
                    r.get("synced_at"),
                ),
            )

    for p in consensus_data.get("consensus_positions", []):
        cursor.execute(
            "SELECT id FROM consensus_agent_positions WHERE id = ?",
            (p["id"],),
        )
        if not cursor.fetchone():
            # Find round_id from round_number if available
            round_number = p.get("round_number", 0)
            round_id = None
            if round_number and p.get("debate_id"):
                cursor.execute(
                    "SELECT id FROM consensus_rounds WHERE debate_id = ? AND round_number = ?",
                    (p["debate_id"], round_number),
                )
                row = cursor.fetchone()
                if row:
                    round_id = row[0]

            cursor.execute(
                """INSERT INTO consensus_agent_positions
                   (id, debate_id, round_id, round_number, agent_id, agent_name, agent_role,
                    position_text, confidence, consensus_score, supporting_points,
                    objections_raised, logical_fallacies, created_at, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    p["id"],
                    p.get("debate_id"),
                    round_id,
                    round_number,
                    p.get("agent_id"),
                    p.get("agent_name"),
                    p.get("agent_role"),
                    p.get("position_text", ""),
                    p.get("confidence", 0),
                    p.get("consensus_score", 0),
                    json.dumps(p.get("supporting_points")) if p.get("supporting_points") else None,
                    json.dumps(p.get("objections_raised")) if p.get("objections_raised") else None,
                    json.dumps(p.get("logical_fallacies")) if p.get("logical_fallacies") else None,
                    _safe_timestamp(p.get("created_at"), p.get("synced_at")),
                    p.get("synced_at"),
                ),
            )

    conn.commit()
    log("  Consensus data imported")


def calculate_reputation(conn, turns):
    log("Calculating model reputation from historical turns...")
    cursor = conn.cursor()

    # Group turns by model+role
    model_turns = defaultdict(list)
    for t in turns:
        key = (t.get("model", "unknown"), t.get("agent_role", "analyst"))
        model_turns[key].append(t)

    # Also group by model+provider for model_reputation table
    model_provider_turns = defaultdict(list)
    for t in turns:
        key = (t.get("model", "unknown"), t.get("provider", "unknown"))
        model_provider_turns[key].append(t)

    # Calculate TSA (Argument Survival Rate) per model+role
    # Simplified: if status=completed, argument survived
    log("  Calculating TSA, IID, PVT, Efficiency scores...")

    for (model, role), mturns in model_turns.items():
        total = len(mturns)
        completed = sum(1 for t in mturns if t.get("status") == "completed")
        tsa = completed / total if total > 0 else 0.5

        # IID (Dialectic Independence) - simplified: diversity of responses
        responses = [t.get("response_received", "")[:200] for t in mturns]
        unique_responses = len(set(responses))
        iid = unique_responses / total if total > 0 else 0.5

        # PVT (Technical Precision) - based on response length and completion
        avg_len = sum(len(r) for r in responses) / len(responses) if responses else 0
        pvt = min(1.0, avg_len / 500) if avg_len > 0 else 0.5

        # Efficiency - tokens out per ms
        total_tokens = sum(t.get("tokens_out", 0) for t in mturns)
        total_ms = sum(t.get("latency_ms", 1) for t in mturns)
        efficiency = min(1.0, (total_tokens / total_ms) * 10) if total_ms > 0 else 0.5

        # Composite reputation
        reputation = 0.35 * tsa + 0.25 * iid + 0.25 * pvt + 0.15 * efficiency

        # Update or insert model_reputation
        cursor.execute(
            "SELECT id FROM model_reputation WHERE model = ? AND role = ?",
            (model, role),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """UPDATE model_reputation SET
                   tsa_score=?, iid_score=?, pvt_score=?, efficiency_score=?,
                   reputation_score=?, total_debates=?, total_turns=?, updated_at=?
                   WHERE model=? AND role=?""",
                (
                    round(tsa, 4),
                    round(iid, 4),
                    round(pvt, 4),
                    round(efficiency, 4),
                    round(reputation, 4),
                    len(set(t.get("debate_id") for t in mturns)),
                    total,
                    datetime.now(UTC).isoformat(),
                    model,
                    role,
                ),
            )
        else:
            cursor.execute(
                """INSERT INTO model_reputation
                   (model, provider, role, tsa_score, iid_score, pvt_score, efficiency_score,
                    reputation_score, total_debates, total_turns, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model,
                    mturns[0].get("provider", "unknown"),
                    role,
                    round(tsa, 4),
                    round(iid, 4),
                    round(pvt, 4),
                    round(efficiency, 4),
                    round(reputation, 4),
                    len(set(t.get("debate_id") for t in mturns)),
                    total,
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )

        log(f"    {model}@{role}: TSA={tsa:.3f}, IID={iid:.3f}, PVT={pvt:.3f}, Eff={efficiency:.3f}, Rep={reputation:.3f}")

    # Also update model_performance table
    for (model, provider), mturns in model_provider_turns.items():
        total = len(mturns)
        completed = sum(1 for t in mturns if t.get("status") == "completed")
        success_rate = completed / total if total > 0 else 0

        avg_tokens = sum(t.get("tokens_out", 0) for t in mturns) / total if total > 0 else 0
        avg_latency = sum(t.get("latency_ms", 0) for t in mturns) / total if total > 0 else 0

        # Get most common role for this model
        role_counts = Counter(t.get("agent_role", "analyst") for t in mturns)
        primary_role = role_counts.most_common(1)[0][0] if role_counts else "analyst"

        # Get engine
        engine_counts = Counter(t.get("engine", "ollama") for t in mturns)
        primary_engine = engine_counts.most_common(1)[0][0] if engine_counts else "ollama"

        cursor.execute(
            "SELECT id FROM model_performance WHERE model_name = ? AND agent_role = ?",
            (model, primary_role),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """UPDATE model_performance SET
                   provider=?, engine=?, total_turns=?, avg_tokens_out=?, avg_latency_ms=?,
                   success_rate=?, last_updated=?
                   WHERE model_name=? AND agent_role=?""",
                (
                    provider,
                    primary_engine,
                    total,
                    round(avg_tokens, 2),
                    round(avg_latency, 2),
                    round(success_rate, 4),
                    datetime.now(UTC).isoformat(),
                    model,
                    primary_role,
                ),
            )
        else:
            cursor.execute(
                """INSERT INTO model_performance
                   (model_name, provider, engine, agent_role, total_turns, avg_tokens_out,
                    avg_latency_ms, avg_quality_score, tsa_score_avg, iid_score_avg,
                    pvt_score_avg, efficiency_score_avg, success_rate, last_updated)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model,
                    provider,
                    primary_engine,
                    primary_role,
                    total,
                    round(avg_tokens, 2),
                    round(avg_latency, 2),
                    0.5,  # avg_quality_score (needs quality scoring)
                    0.5,  # tsa_score_avg
                    0.5,  # iid_score_avg
                    0.5,  # pvt_score_avg
                    0.5,  # efficiency_score_avg
                    round(success_rate, 4),
                    datetime.now(UTC).isoformat(),
                ),
            )

    conn.commit()
    log("  Reputation calculated and saved")


def clean_empty_tables(conn):
    log("Cleaning empty/obsolete tables...")
    cursor = conn.cursor()

    empty_tables = []
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count == 0:
            empty_tables.append(table)

    # Tables safe to drop (analytics/duplicates with no data)
    droppable = {
        "config_profiles",
        "consensus_patterns",
        "daily_metrics_snapshot",
        "debates_aggregate",
        "prompt_response_cache",
        "supabase_sync_queue",
        "topics_trending",
    }

    to_drop = [t for t in empty_tables if t in droppable]
    for table in to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        log(f"  Dropped empty table: {table}")

    conn.commit()


def print_summary(conn):
    log("=== FINAL DATABASE SUMMARY ===")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        log(f"  {table}: {count} rows")

    # Show reputation scores
    log("\n=== MODEL REPUTATION (sorted by score) ===")
    cursor.execute(
        "SELECT model, provider, role, tsa_score, iid_score, pvt_score, efficiency_score, reputation_score, total_turns FROM model_reputation ORDER BY reputation_score DESC"
    )
    for row in cursor.fetchall():
        log(f"  {row[0]}@{row[2]}: Rep={row[7]:.3f} TSA={row[3]:.3f} IID={row[4]:.3f} PVT={row[5]:.3f} Eff={row[6]:.3f} Turns={row[8]}")


async def main():
    log("Starting database migration...")

    # Step 1: Backup
    backup_database()

    # Step 2: Download from Supabase
    data = await download_from_supabase()

    # Step 3: Connect to SQLite and align schema
    conn = sqlite3.connect(str(SQLITE_PATH))
    align_schema(conn)

    # Step 4: Import data
    import_debates(conn, data["debates"])
    import_turns(conn, data["turns"])
    import_consensus(conn, data)

    # Step 5: Calculate reputation
    calculate_reputation(conn, data["turns"])

    # Step 6: Clean empty tables
    clean_empty_tables(conn)

    # Step 7: Print summary
    print_summary(conn)

    conn.close()
    log("Migration complete!")


if __name__ == "__main__":
    asyncio.run(main())
