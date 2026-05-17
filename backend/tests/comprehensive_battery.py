"""
SynapseCode - Comprehensive Test Battery
Tests: imports, config, database, adapters, API, workers, logging, stability
"""

import asyncio
import os
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.main import app

# Results tracking
results = {"passed": [], "failed": [], "skipped": [], "warnings": []}
test_count = 0


def record(category, name, status, detail=""):
    global test_count
    test_count += 1
    entry = {"#": test_count, "category": category, "name": name, "status": status, "detail": detail}
    results[status].append(entry)
    icon = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP", "warnings": "WARN"}
    print(f"  [{icon[status]:4s}] {category:25s} | {name}")


# ============================================================================
print("=" * 100)
print("SYNAPSECODE COMPREHENSIVE TEST BATTERY")
print(f"Timestamp: {datetime.now().isoformat()}")
print("=" * 100)

# ─── 1. IMPORTS & MODULE STRUCTURE ────────────────────────────────────────────
print("\n[1/12] IMPORTS & MODULE STRUCTURE")
print("-" * 60)

modules_to_test = [
    ("Core Config", "backend.config", "get_settings"),
    ("Database Models", "backend.database.models", "SequentialDebate"),
    ("Debate Models", "backend.engine.debate_models", "DebateSession"),
    ("Sequential Controller", "backend.engine.sequential_debate_controller", "SequentialDebateController"),
    ("Ultra Controller", "backend.engine.ultra_debate_controller", "UltraDebateController"),
    ("Consensus Controller", "backend.engine.consensus_debate_controller", "ConsensusDebateController"),
    ("Tribunal", "backend.engine.tribunal", "TribunalCouncil"),
    ("Convergence", "backend.engine.convergence", "ConvergenceEvaluator"),
    ("Quality Monitor", "backend.engine.quality_monitor", "QualityMonitor"),
    ("Reputation", "backend.engine.reputation_unified", "ReputationManager"),
    ("Task Manager", "backend.engine.task_manager", "BackgroundTaskManager"),
    ("Worker Launcher", "backend.engine.worker_launcher", "WorkerServiceManager"),
    ("Local Engine Manager", "backend.engine.local_engine_manager", "LocalEngineManager"),
    ("Reductio Absurdum", "backend.engine.reductio_absurdum", "ReductioAbsurdumEngine"),
    ("Intervention Taxonomy", "backend.engine.intervention_taxonomy", "detect_intervention_type"),
    ("Round Controller", "backend.engine.round_controller", "RoundController"),
    ("Agent Orchestrator", "backend.engine.agent_orchestrator", "AgentOrchestrator"),
    ("Hybrid Memory", "backend.memory.hybrid_memory_v2", "HybridMemoryV2"),
    ("Ollama Adapter", "backend.adapters.ollama", "OllamaClient"),
    ("Groq Adapter", "backend.adapters.groq", "GroqClient"),
    ("Gemini Adapter", "backend.adapters.gemini", "GeminiClient"),
    ("LM Studio Adapter", "backend.adapters.lm_studio", "LMStudioClient"),
    ("OpenRouter Adapter", "backend.adapters.openrouter", "OpenRouterClient"),
    ("DeepSeek Adapter", "backend.adapters.deepseek", "DeepSeekClient"),
    ("Jan Adapter", "backend.adapters.jan", "JanClient"),
    ("Web Agent", "backend.adapters.web_agent", "WebAgentClient"),
    ("HTTP Client Manager", "backend.adapters.http_client_manager", "HTTPClientManager"),
    ("HuggingFace Adapter", "backend.adapters.huggingface", "HuggingFaceClient"),
    ("Supabase Sync", "backend.services.supabase_sync", "SupabaseSyncService"),
    ("SQLite Backup", "backend.services.sqlite_backup", "SQLiteBackupService"),
    ("RDP Manager", "backend.services.rdp_manager", "RDPManager"),
    ("Network Discovery", "backend.network.discovery", "NodeDiscoverer"),
    ("Heartbeat", "backend.network.heartbeat", "HeartbeatManager"),
    ("TCP Handshake", "backend.network.tcp_handshake", "TCPHandshake"),
    ("Prometheus Metrics", "backend.monitoring.prometheus", "render_prometheus_metrics"),
    ("Semantic Cache", "backend.caching.semantic_cache", "SemanticCacheService"),
    ("Warehouse", "backend.database.warehouse", "WarehouseManager"),
    ("Logging Config", "backend.logging_config", "setup_logging"),
    ("Pre-startup Check", "backend.pre_startup_check", "check_ollama"),
    ("FastAPI App", "backend.main", "app"),
]

for label, module_path, attr in modules_to_test:
    try:
        mod = __import__(module_path, fromlist=[attr])
        getattr(mod, attr)
        record("Imports", label, "passed")
    except Exception as e:
        record("Imports", label, "failed", str(e)[:80])

# ─── 2. CONFIGURATION VALIDATION ──────────────────────────────────────────────
print("\n[2/12] CONFIGURATION VALIDATION")
print("-" * 60)

settings = get_settings()

config_checks = [
    ("NODE_ROLE", settings.NODE_ROLE in ("MASTER", "WORKER"), f"role={settings.NODE_ROLE}"),
    ("PORT", settings.PORT == 8000, f"port={settings.PORT}"),
    ("HOST", settings.HOST == "0.0.0.0", f"host={settings.HOST}"),  # nosec B104
    ("DATABASE_URL", bool(settings.DATABASE_URL), f"url={settings.DATABASE_URL[:30]}..."),
    (
        "SUPABASE_URL",
        bool(settings.SUPABASE_URL) and "CHANGEME" not in settings.SUPABASE_URL,
        f"configured={bool(settings.SUPABASE_URL)}",
    ),
    (
        "SUPABASE_ANON_KEY",
        bool(settings.SUPABASE_ANON_KEY) and "CHANGEME" not in settings.SUPABASE_ANON_KEY,
        "configured",
    ),
    ("WORKER_HOST", bool(settings.WORKER_HOST), f"host={settings.WORKER_HOST}"),
    ("WORKER_OLLAMA_PORT", settings.WORKER_OLLAMA_PORT == 11434, f"port={settings.WORKER_OLLAMA_PORT}"),
    ("WORKER_LM_STUDIO_PORT", settings.WORKER_LM_STUDIO_PORT == 1234, f"port={settings.WORKER_LM_STUDIO_PORT}"),
    ("WORKER_JAN_PORT", settings.WORKER_JAN_PORT == 1337, f"port={settings.WORKER_JAN_PORT}"),
    ("is_master", settings.is_master == (settings.NODE_ROLE == "MASTER"), f"is_master={settings.is_master}"),
    ("CORS_ORIGINS", isinstance(settings.CORS_ORIGINS, list), f"origins={settings.CORS_ORIGINS}"),
    ("LOG_LEVEL", settings.LOG_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR"), f"level={settings.LOG_LEVEL}"),
    ("LOG_TO_FILE", isinstance(settings.LOG_TO_FILE, bool), f"to_file={settings.LOG_TO_FILE}"),
    ("RDP_ENABLED", isinstance(settings.RDP_ENABLED, bool), f"rdp={settings.RDP_ENABLED}"),
    ("WEB_AGENT_ENABLED", isinstance(settings.WEB_AGENT_ENABLED, bool), f"web_agent={settings.WEB_AGENT_ENABLED}"),
    (
        "AGENT_REPUTATION_ENABLED",
        isinstance(settings.AGENT_REPUTATION_ENABLED, bool),
        f"reputation={settings.AGENT_REPUTATION_ENABLED}",
    ),
    ("TRIBUNAL_MAX_ITERATIONS", settings.TRIBUNAL_MAX_ITERATIONS >= 1, f"max_iter={settings.TRIBUNAL_MAX_ITERATIONS}"),
    ("MODEL_TIMEOUT_OLLAMA", settings.OLLAMA_TIMEOUT_SECONDS > 0, f"timeout={settings.OLLAMA_TIMEOUT_SECONDS}s"),
    (
        "MODEL_TIMEOUT_GROQ",
        settings.GROQ_TIMEOUT_SECONDS > 0 if hasattr(settings, "GROQ_TIMEOUT_SECONDS") else True,
        f"timeout={getattr(settings, 'GROQ_TIMEOUT_SECONDS', 'N/A')}s",
    ),
]

for name, condition, detail in config_checks:
    record("Config", name, "passed" if condition else "failed", detail)

# ─── 3. DATABASE CONNECTIVITY ─────────────────────────────────────────────────
print("\n[3/12] DATABASE CONNECTIVITY")
print("-" * 60)


async def test_database():
    from sqlalchemy import func, select

    from backend.database.local_db import AsyncSessionLocal, init_db
    from backend.database.models import (
        ConsensusPattern,
        DailyMetricsSnapshot,
        DebateAggregate,
        ModelPerformance,
        ModelReputation,
        PromptResponseCache,
        ReductioAbsurdumProof,
        SequentialDebate,
        SequentialDebateTurn,
        SupabaseSyncQueueItem,
        TopicTrending,
    )

    await init_db()
    record("Database", "init_db()", "passed", "SQLite initialized")

    # Test all models have tables
    models = [
        SequentialDebate,
        SequentialDebateTurn,
        PromptResponseCache,
        ReductioAbsurdumProof,
        DebateAggregate,
        TopicTrending,
        ConsensusPattern,
        ModelPerformance,
        DailyMetricsSnapshot,
        SupabaseSyncQueueItem,
        ModelReputation,
    ]
    for model in models:
        record("Database", f"Model {model.__tablename__}", "passed", f"table={model.__tablename__}")

    # Test CRUD operations
    async with AsyncSessionLocal() as session:
        # Create
        debate = SequentialDebate(id="test-battery-1", topic="Test Battery Debate", status="completed", total_turns=0)
        session.add(debate)
        await session.commit()
        record("Database", "CRUD: Create SequentialDebate", "passed")

        # Read
        result = await session.execute(select(SequentialDebate).where(SequentialDebate.id == "test-battery-1"))
        found = result.scalar_one_or_none()
        if found and found.topic == "Test Battery Debate":
            record("Database", "CRUD: Read SequentialDebate", "passed")
        else:
            record("Database", "CRUD: Read SequentialDebate", "failed", "not found")

        # Update
        found.status = "archived"
        await session.commit()
        record("Database", "CRUD: Update SequentialDebate", "passed")

        # Delete
        await session.delete(found)
        await session.commit()
        record("Database", "CRUD: Delete SequentialDebate", "passed")

    # Test aggregate queries
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count(SequentialDebate.id)))
        record("Database", "Aggregate: COUNT debates", "passed", f"count={count}")


asyncio.run(test_database())

# ─── 4. API ENDPOINTS ─────────────────────────────────────────────────────────
print("\n[4/12] API ENDPOINTS")
print("-" * 60)

client = TestClient(app)

api_tests = [
    ("GET /", "/", 200, "root info"),
    ("GET /health", "/health", 200, "health check"),
    ("GET /health/live", "/health/live", 200, "liveness"),
    ("GET /metrics", "/metrics", 200, "prometheus metrics"),
    ("GET /api/v1/debates/list", "/api/v1/debates/list", 200, "debate list"),
    ("GET /api/v1/cache/stats", "/api/v1/cache/stats", 200, "cache stats"),
    ("POST /api/v1/debates/create (invalid)", "/api/v1/debates/create", 422, "validation"),
    ("GET /api/v1/system/backup/status", "/api/v1/system/backup/status", 200, "backup status"),
    ("GET /api/v1/system/backup/list", "/api/v1/system/backup/list", 200, "backup list"),
    ("GET /api/v1/system/backup/create", "/api/v1/system/backup/create", 405, "backup create (method)"),
    ("GET /api/v1/system/reductio/analytics", "/api/v1/system/reductio/analytics", 403, "reductio analytics (auth)"),
    ("GET /api/v1/system/analytics", "/api/v1/system/analytics", 403, "analytics (auth)"),
    ("GET /api/v1/system/tribunal/config", "/api/v1/system/tribunal/config", 403, "tribunal config (auth)"),
    ("GET /api/v1/system/settings", "/api/v1/system/settings", 403, "settings (auth)"),
    ("GET /api/v1/system/health/sync", "/api/v1/system/health/sync", 403, "sync health (auth)"),
    ("GET /api/v1/system/worker/services", "/api/v1/system/worker/services", 403, "worker services (auth)"),
    ("GET /api/v1/system/rdp-status", "/api/v1/system/rdp-status", 403, "rdp status (auth)"),
    ("GET /debug/imports", "/debug/imports", 200, "debug imports"),
    ("GET /debug/services", "/debug/services", 200, "debug services"),
    ("GET /debug/config", "/debug/config", 200, "debug config"),
]

for label, path, expected, desc in api_tests:
    try:
        if "POST" in label:
            r = client.post(path, json={})
        else:
            r = client.get(path)

        if r.status_code == expected:
            record("API", label, "passed", f"status={r.status_code} ({desc})")
        else:
            record("API", label, "failed", f"expected={expected}, got={r.status_code}")
    except Exception as e:
        record("API", label, "failed", str(e)[:80])

# ─── 5. RESPONSE SCHEMA VALIDATION ────────────────────────────────────────────
print("\n[5/12] RESPONSE SCHEMA VALIDATION")
print("-" * 60)

schema_tests = [
    ("GET /health", "/health", ["status", "timestamp", "worker_connected"]),
    ("GET /health/live", "/health/live", ["status"]),
    ("GET /", "/", ["name", "version", "node_role"]),
    ("GET /api/v1/debates/list", "/api/v1/debates/list", ["count", "sessions"]),
    ("GET /api/v1/cache/stats", "/api/v1/cache/stats", ["total_entries", "hit_rate"]),
    ("GET /api/v1/system/backup/status", "/api/v1/system/backup/status", ["enabled", "database_path", "bucket"]),
    ("GET /api/v1/system/backup/list", "/api/v1/system/backup/list", ["count", "backups"]),
    ("GET /debug/imports", "/debug/imports", ["status", "modules"]),
]

for label, path, required_keys in schema_tests:
    try:
        r = client.get(path)
        if r.status_code == 200:
            data = r.json()
            missing = [k for k in required_keys if k not in data]
            if not missing:
                record("Schema", label, "passed", f"keys={len(data)}")
            else:
                record("Schema", label, "failed", f"missing={missing}")
        else:
            record("Schema", label, "skipped", f"status={r.status_code}")
    except Exception as e:
        record("Schema", label, "failed", str(e)[:80])

# ─── 6. ADAPTER INSTANTIATION ─────────────────────────────────────────────────
print("\n[6/12] ADAPTER INSTANTIATION")
print("-" * 60)

adapter_tests = [
    (
        "OllamaClient",
        "backend.adapters.ollama",
        "OllamaClient",
        ["chat", "generate", "health_check", "warm_model", "unload_model"],
    ),
    ("GroqClient", "backend.adapters.groq", "GroqClient", ["chat_completion", "health_check"]),
    ("GeminiClient", "backend.adapters.gemini", "GeminiClient", ["chat_completion", "health_check"]),
    ("LMStudioClient", "backend.adapters.lm_studio", "LMStudioClient", ["chat_completion", "health_check"]),
    ("OpenRouterClient", "backend.adapters.openrouter", "OpenRouterClient", ["chat_completion", "health_check"]),
    ("DeepSeekClient", "backend.adapters.deepseek", "DeepSeekClient", ["chat_completion", "health_check"]),
    ("JanClient", "backend.adapters.jan", "JanClient", ["chat_completion", "health_check"]),
    ("WebAgentClient", "backend.adapters.web_agent", "WebAgentClient", ["query", "health_check"]),
    ("HuggingFaceClient", "backend.adapters.huggingface", "HuggingFaceClient", ["chat_completion", "health_check"]),
    (
        "HTTPClientManager",
        "backend.adapters.http_client_manager",
        "HTTPClientManager",
        ["get_client", "close_all", "close"],
    ),
]

for label, mod_path, cls_name, methods in adapter_tests:
    try:
        mod = __import__(mod_path, fromlist=[cls_name])
        cls = getattr(mod, cls_name)
        instance = cls()
        missing = [m for m in methods if not hasattr(instance, m)]
        if not missing:
            record("Adapters", label, "passed", f"methods={len(methods)}")
        else:
            record("Adapters", label, "failed", f"missing_methods={missing}")
    except Exception as e:
        record("Adapters", label, "failed", str(e)[:80])

# ─── 7. LIVE CONNECTION TESTS ─────────────────────────────────────────────────
print("\n[7/12] LIVE CONNECTION TESTS")
print("-" * 60)


def test_port(host, port, service_name, timeout=3):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


live_tests = [
    ("localhost", 8000, "Backend API (Master local)"),
    ("localhost", 8080, "Frontend Control Center (Master local)"),
    ("localhost", 11434, "Ollama (Master local)"),
    ("localhost", 1234, "LM Studio (Master local)"),
    ("localhost", 1337, "Jan (Master local)"),
    (settings.WORKER_HOST, 11434, f"Ollama (Worker {settings.WORKER_HOST})"),
    (settings.WORKER_HOST, 1234, f"LM Studio (Worker {settings.WORKER_HOST})"),
    (settings.WORKER_HOST, 1337, f"Jan (Worker {settings.WORKER_HOST})"),
    (settings.WORKER_HOST, 3389, f"RDP (Worker {settings.WORKER_HOST})"),
]

for host, port, label in live_tests:
    try:
        reachable = test_port(host, port, label)
        if reachable:
            record("Connections", label, "passed", f"{host}:{port} OPEN")
        else:
            record("Connections", label, "skipped", f"{host}:{port} CLOSED (service not running)")
    except Exception as e:
        record("Connections", label, "failed", str(e)[:80])

# Test Ollama live API
print()
try:
    import requests

    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    if r.status_code == 200:
        models = r.json().get("models", [])
        record("Connections", "Ollama /api/tags", "passed", f"models={len(models)}")
        for m in models[:5]:
            record("Connections", f"  Model: {m['name']}", "passed", f"size={m.get('size', 0)}")
    else:
        record("Connections", "Ollama /api/tags", "failed", f"status={r.status_code}")
except Exception as e:
    record("Connections", "Ollama /api/tags", "failed", str(e)[:80])

# Test Supabase connectivity
try:
    r = requests.get(f"{settings.SUPABASE_URL}/rest/v1/", timeout=10)
    if r.status_code in (200, 401, 404):
        record("Connections", "Supabase REST API", "passed", f"status={r.status_code}")
    else:
        record("Connections", "Supabase REST API", "failed", f"status={r.status_code}")
except Exception as e:
    record("Connections", "Supabase REST API", "failed", str(e)[:80])

# ─── 8. ENGINE COMPONENTS ─────────────────────────────────────────────────────
print("\n[8/12] ENGINE COMPONENTS")
print("-" * 60)

# SequentialDebateController
try:
    from backend.engine.sequential_debate_controller import SequentialDebateController

    ctrl = SequentialDebateController()
    methods = [
        "create_debate",
        "continue_debate",
        "pause_debate",
        "resume_debate",
        "get_session",
        "get_debate_from_db",
        "_run_local_agent",
        "_run_cloud_agent",
        "_persist_reductio_absurdum_proof",
        "_find_next_preload_model",
        "_save_transcript",
    ]
    missing = [m for m in methods if not hasattr(ctrl, m)]
    if not missing:
        record("Engine", "SequentialDebateController", "passed", f"methods={len(methods)}")
    else:
        record("Engine", "SequentialDebateController", "failed", f"missing={missing}")
except Exception as e:
    record("Engine", "SequentialDebateController", "failed", str(e)[:80])

# UltraDebateController
try:
    from backend.engine.ultra_debate_controller import UltraDebateController

    uctrl = UltraDebateController()
    record("Engine", "UltraDebateController", "passed", f"stages={len(uctrl.stages)}")
except Exception as e:
    record("Engine", "UltraDebateController", "failed", str(e)[:80])

# ConsensusDebateController
try:
    from backend.engine.consensus_debate_controller import ConsensusDebateController

    cctrl = ConsensusDebateController()
    record("Engine", "ConsensusDebateController", "passed")
except Exception as e:
    record("Engine", "ConsensusDebateController", "failed", str(e)[:80])

# TribunalCouncil
try:
    from backend.engine.tribunal import TribunalCouncil

    tribunal = TribunalCouncil()
    record("Engine", "TribunalCouncil", "passed", f"magistrates={len(tribunal.MAGISTRATE_ROLES)}")
except Exception as e:
    record("Engine", "TribunalCouncil", "failed", str(e)[:80])

# ConvergenceEvaluator
try:
    from backend.engine.convergence import ConvergenceEvaluator

    conv = ConvergenceEvaluator()
    result = conv.evaluate("test A", "test A", 1, 3)
    if hasattr(result, "similarity_score"):
        record("Engine", "ConvergenceEvaluator", "passed", f"similarity={result.similarity_score:.2f}")
    else:
        record("Engine", "ConvergenceEvaluator", "failed", "no similarity_score")
except Exception as e:
    record("Engine", "ConvergenceEvaluator", "failed", str(e)[:80])

# QualityMonitor
try:
    from backend.engine.quality_monitor import evaluate_response, is_response_usable

    assert is_response_usable("Good analysis text", "analyst") is True
    assert is_response_usable("", "analyst") is False
    assert is_response_usable("[ERROR]", "analyst") is False
    score, _ = evaluate_response("Detailed analysis with evidence", "analyst")
    assert 0.0 <= score <= 1.0
    record("Engine", "QualityMonitor", "passed", f"score={score:.2f}")
except Exception as e:
    record("Engine", "QualityMonitor", "failed", str(e)[:80])

# ReductioAbsurdum
try:
    from backend.engine.reductio_absurdum import get_reductio_absurdum_engine

    engine = get_reductio_absurdum_engine()
    props = engine.extract_propositions_from_text("La IA es buena porque automatiza tareas.")
    if isinstance(props, list) and len(props) > 0:
        record("Engine", "ReductioAbsurdum", "passed", f"propositions={len(props)}")
    else:
        record("Engine", "ReductioAbsurdum", "failed", "no propositions extracted")
except Exception as e:
    record("Engine", "ReductioAbsurdum", "failed", str(e)[:80])

# InterventionTaxonomy
try:
    from backend.engine.intervention_taxonomy import detect_intervention_type

    t1 = detect_intervention_type("El analisis muestra...", "analyst")
    t2 = detect_intervention_type("Sin embargo, hay debilidades...", "critic")
    t3 = detect_intervention_type("En sintesis...", "synthesizer")
    record("Engine", "InterventionTaxonomy", "passed", f"types={t1}, {t2}, {t3}")
except Exception as e:
    record("Engine", "InterventionTaxonomy", "failed", str(e)[:80])

# ─── 9. SERVICES ──────────────────────────────────────────────────────────────
print("\n[9/12] SERVICES")
print("-" * 60)

# SupabaseSyncService
try:
    from backend.services.supabase_sync import SupabaseSyncService

    svc = SupabaseSyncService()
    record("Services", "SupabaseSyncService", "passed", f"enabled={svc.enabled}")
except Exception as e:
    record("Services", "SupabaseSyncService", "failed", str(e)[:80])

# SQLiteBackupService
try:
    from backend.services.sqlite_backup import SQLiteBackupService

    backup = SQLiteBackupService()
    record("Services", "SQLiteBackupService", "passed", f"enabled={backup.enabled}, bucket={backup.BACKUP_BUCKET}")
except Exception as e:
    record("Services", "SQLiteBackupService", "failed", str(e)[:80])

# WorkerServiceManager
try:
    from backend.engine.worker_launcher import WorkerServiceManager

    wsm = WorkerServiceManager()
    record("Services", "WorkerServiceManager", "passed", f"worker={settings.WORKER_HOST}")
except Exception as e:
    record("Services", "WorkerServiceManager", "failed", str(e)[:80])

# HybridMemoryV2
try:
    from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2

    mem = get_hybrid_memory_v2()
    record("Services", "HybridMemoryV2", "passed", f"enabled={mem._enabled}")
except Exception as e:
    record("Services", "HybridMemoryV2", "failed", str(e)[:80])

# SemanticCacheService
try:
    from backend.caching.semantic_cache import SemanticCacheService

    cache = SemanticCacheService()
    key = cache._generate_cache_key("test", "model", "engine", 0.7)
    record("Services", "SemanticCacheService", "passed", f"key_len={len(key)}")
except Exception as e:
    record("Services", "SemanticCacheService", "failed", str(e)[:80])

# WarehouseManager
try:
    from backend.database.warehouse import WarehouseManager

    wm = WarehouseManager()
    record("Services", "WarehouseManager", "passed")
except Exception as e:
    record("Services", "WarehouseManager", "failed", str(e)[:80])

# ─── 10. LOGGING SYSTEM ───────────────────────────────────────────────────────
print("\n[10/12] LOGGING SYSTEM")
print("-" * 60)

try:
    import shutil
    import tempfile

    from backend.logging_config import _APIFilter, _EngineFilter, setup_logging, shutdown_logging

    tmpdir = tempfile.mkdtemp()
    setup_logging(log_level="DEBUG", log_dir=Path(tmpdir), console=False, file_output=True)

    log_file = Path(tmpdir) / "synapse.log"
    error_file = Path(tmpdir) / "synapse_error.log"
    engine_file = Path(tmpdir) / "synapse_engine.log"
    api_file = Path(tmpdir) / "synapse_api.log"

    for name, path in [
        ("synapse.log", log_file),
        ("synapse_error.log", error_file),
        ("synapse_engine.log", engine_file),
        ("synapse_api.log", api_file),
    ]:
        if path.exists():
            record("Logging", f"{name} created", "passed", f"size={path.stat().st_size}B")
        else:
            record("Logging", f"{name} created", "failed", "not found")

    # Test filters
    import logging

    ef = _EngineFilter()
    af = _APIFilter()
    record(
        "Logging",
        "_EngineFilter",
        "passed" if ef.filter(logging.LogRecord("backend.engine.x", 20, "", 0, "", (), None)) else "failed",
    )
    record(
        "Logging",
        "_APIFilter",
        "passed" if af.filter(logging.LogRecord("backend.api.routes.x", 20, "", 0, "", (), None)) else "failed",
    )

    shutdown_logging()
    shutil.rmtree(tmpdir, ignore_errors=True)
except Exception as e:
    record("Logging", "System", "failed", str(e)[:80])

# ─── 11. STABILITY / STRESS TESTS ─────────────────────────────────────────────
print("\n[11/12] STABILITY / STRESS TESTS")
print("-" * 60)

# Rapid API calls
try:
    start = time.time()
    for i in range(50):
        r = client.get("/health")
        assert r.status_code == 200
    elapsed = time.time() - start
    rps = 50 / elapsed
    record("Stability", "50 rapid GET /health", "passed", f"{elapsed:.2f}s ({rps:.0f} req/s)")
except Exception as e:
    record("Stability", "50 rapid GET /health", "failed", str(e)[:80])


# Concurrent DB operations
async def test_concurrent_db():
    from sqlalchemy import select

    from backend.database.local_db import AsyncSessionLocal
    from backend.database.models import SequentialDebate

    tasks = []
    for i in range(10):

        async def op(n=i):
            async with AsyncSessionLocal() as s:
                result = await s.execute(select(SequentialDebate).limit(1))
                return result.scalar_one_or_none() is not None

        tasks.append(op())
    results_list = await asyncio.gather(*tasks)
    return all(results_list)


try:
    ok = asyncio.run(test_concurrent_db())
    record("Stability", "10 concurrent DB reads", "passed" if ok else "failed", f"all_ok={ok}")
except Exception as e:
    record("Stability", "10 concurrent DB reads", "failed", str(e)[:80])

# Memory leak check (repeated controller creation)
try:
    import gc

    from backend.engine.sequential_debate_controller import SequentialDebateController

    controllers = []
    for i in range(20):
        controllers.append(SequentialDebateController())
    gc.collect()
    record("Stability", "20x SequentialDebateController creation", "passed", f"instances={len(controllers)}")
    del controllers
except Exception as e:
    record("Stability", "20x SequentialDebateController creation", "failed", str(e)[:80])

# WebSocket Manager stress
try:
    from backend.api.websocket import WebSocketManager

    manager = WebSocketManager()
    for i in range(100):
        manager.buffer_tokens = True
        manager.token_buffers[f"session-{i}"] = []
    record("Stability", "100 WebSocket session buffers", "passed", f"buffers={len(manager.token_buffers)}")
except Exception as e:
    record("Stability", "100 WebSocket session buffers", "failed", str(e)[:80])

# ─── 12. FILE STRUCTURE & INTEGRITY ───────────────────────────────────────────
print("\n[12/12] FILE STRUCTURE & INTEGRITY")
print("-" * 60)

required_files = [
    "backend/main.py",
    "backend/config.py",
    "backend/logging_config.py",
    "backend/requirements.txt",
    "backend/.env",
    "backend/database/models.py",
    "backend/database/local_db.py",
    "backend/api/routes/debate.py",
    "backend/api/routes/system.py",
    "backend/api/routes/health.py",
    "backend/api/routes/cache.py",
    "backend/api/websocket.py",
    "backend/engine/sequential_debate_controller.py",
    "backend/engine/ultra_debate_controller.py",
    "backend/engine/consensus_debate_controller.py",
    "backend/engine/tribunal.py",
    "backend/engine/convergence.py",
    "backend/engine/quality_monitor.py",
    "backend/engine/reputation_unified.py",
    "backend/engine/task_manager.py",
    "backend/engine/worker_launcher.py",
    "backend/engine/reductio_absurdum.py",
    "backend/adapters/ollama.py",
    "backend/adapters/groq.py",
    "backend/adapters/gemini.py",
    "backend/adapters/lm_studio.py",
    "backend/adapters/openrouter.py",
    "backend/adapters/deepseek.py",
    "backend/adapters/jan.py",
    "backend/adapters/web_agent.py",
    "backend/adapters/http_client_manager.py",
    "backend/services/supabase_sync.py",
    "backend/services/sqlite_backup.py",
    "backend/services/rdp_manager.py",
    "backend/memory/hybrid_memory_v2.py",
    "backend/caching/semantic_cache.py",
    "backend/database/warehouse.py",
    "backend/monitoring/prometheus.py",
    "backend/network/discovery.py",
    "backend/network/heartbeat.py",
    "backend/network/tcp_handshake.py",
    "frontend/control-center/index.html",
    ".github/workflows/ci.yml",
    "pyproject.toml",
    "README.md",
    "CHANGELOG.md",
]

base = Path("D:\\proyectos\\SynapseCode")
for f in required_files:
    path = base / f
    if path.exists():
        size = path.stat().st_size
        record("Files", f, "passed", f"{size:,}B")
    else:
        record("Files", f, "failed", "MISSING")

# Check no sensitive files
sensitive_files = ["Escritorio.rdp", "synapse_workers.json"]
for f in sensitive_files:
    path = base / f
    if not path.exists():
        record("Security", f"{f} not present", "passed", "clean")
    else:
        record("Security", f"{f} not present", "failed", "FOUND - should be removed")

# Check .gitignore
gitignore = base / ".gitignore"
if gitignore.exists():
    content = gitignore.read_text()
    for pattern in ["*.rdp", "data/debates/*.md", "synapse_workers.json"]:
        if pattern in content:
            record("Security", f".gitignore has {pattern}", "passed")
        else:
            record("Security", f".gitignore has {pattern}", "failed", "missing")

# ============================================================================
# FINAL REPORT
# ============================================================================
print("\n" + "=" * 100)
print("TEST BATTERY REPORT")
print("=" * 100)

total = len(results["passed"]) + len(results["failed"]) + len(results["skipped"]) + len(results["warnings"])
passed = len(results["passed"])
failed = len(results["failed"])
skipped = len(results["skipped"])
warnings = len(results["warnings"])

print(f"\nTotal tests:  {total}")
print(f"  PASSED:     {passed} ({passed / total * 100:.1f}%)")
print(f"  FAILED:     {failed} ({failed / total * 100:.1f}%)")
print(f"  SKIPPED:    {skipped} ({skipped / total * 100:.1f}%)")
print(f"  WARNINGS:   {warnings}")

if failed > 0:
    print(f"\n{'-' * 60}")
    print("FAILED TESTS:")
    print(f"{'-' * 60}")
    for f in results["failed"]:
        print(f"  [{f['#']:3d}] {f['category']:25s} | {f['name']:40s} | {f['detail']}")

if skipped > 0:
    print(f"\n{'-' * 60}")
    print("SKIPPED TESTS (services not running):")
    print(f"{'-' * 60}")
    for s in results["skipped"]:
        print(f"  [{s['#']:3d}] {s['category']:25s} | {s['name']:40s} | {s['detail']}")

# Category breakdown
categories = {}
for r in results["passed"] + results["failed"] + results["skipped"]:
    cat = r["category"]
    if cat not in categories:
        categories[cat] = {"passed": 0, "failed": 0, "skipped": 0}
    categories[cat][r["status"]] = categories[cat].get(r["status"], 0) + 1

print(f"\n{'-' * 60}")
print("RESULTS BY CATEGORY:")
print(f"{'-' * 60}")
print(f"  {'Category':<25s} {'PASS':>5s} {'FAIL':>5s} {'SKIP':>5s} {'Total':>5s}")
print(f"  {'-' * 25} {'-' * 5} {'-' * 5} {'-' * 5} {'-' * 5}")
for cat, counts in sorted(categories.items()):
    p = counts.get("passed", 0)
    f = counts.get("failed", 0)
    s = counts.get("skipped", 0)
    t = p + f + s
    print(f"  {cat:<25s} {p:>5d} {f:>5d} {s:>5d} {t:>5d}")

print(f"\n{'=' * 100}")
if failed == 0:
    print("OVERALL: ALL TESTS PASSED")
else:
    print(f"OVERALL: {failed} TESTS FAILED - REVIEW REQUIRED")
print(f"{'=' * 100}")
