<div align="center">
  <img src="frontend/web/logo.png" alt="SynapseCode" width="280">

  [🇪🇸 Español](#español) · [🇬🇧 English](#english)

  [![CI](https://github.com/OscarFeMa/SynapseCode/actions/workflows/ci.yml/badge.svg)](https://github.com/OscarFeMa/SynapseCode/actions/workflows/ci.yml)
  [![Tests](https://img.shields.io/badge/tests-177%20passing-brightgreen)]()
  [![Python](https://img.shields.io/badge/python-3.12-blue)]()
  [![License](https://img.shields.io/badge/license-MIT-green)]()
  [![Web](https://img.shields.io/badge/web-synapsecode.org-23403B)]()
</div>

---

<a name="español"></a>
# 🇪🇸 SynapseCode v3.0

Plataforma de **razonamiento colectivo híbrido** que orquesta múltiples modelos de IA en debates estructurados por roles, con veredicto del **Tribunal de Magistrados**.

Arquitectura **Master–Worker**: el PC Master orquesta, el PC Worker ejecuta modelos locales.
**Diseño editorial**: fondo `#F5F3EE` (cream paper), acento `#23403B` (petroleum green), tipografía Instrument Serif + Inter.

---

## Características

| Módulo | Descripción |
|---|---|
| **Motor de Debate** | Secuencial (4–6 agentes), Iterativo, Ultra Crossing (12+ agentes) con fases múltiples y consenso forzado |
| **Tribunal de Magistrados** | 3 roles (Defensor, Fiscal, Árbitro) con cadenas de fallback y protocolo de consenso configurable |
| **Control Center v3** | Dashboard compacto (4 paneles), lanzamiento de debates, historial, exportación multi-formato, Vanilla JS sin dependencias |
| **Asignación Inteligente** | Model Registry (25+ modelos), evaluador con rankings web, Role Matcher automático |
| **Reputación EMA** | TSA (coherencia), IID (densidad informativa), PVT (veracidad) — score global ponderado |
| **Búsqueda Web** | DuckDuckGo + Trafilatura, contexto web inyectado en debates |
| **Reportes Profesionales** | HTML interactivo, PDF, DOCX exportable con gráficos y veredicto |
| **Caché Semántica** | Embeddings por similitud, TTL configurable, invalidación por modelo/engine |
| **Memoria Híbrida v2** | SQLite local + Supabase Cloud sync, cola persistente con reintentos |
| **Data Warehouse** | Agregaciones automáticas, trending de topics, rendimiento de modelos |
| **Observabilidad** | Prometheus `/metrics`, logging rotatorio (10MB/5 backups), health checks multi-nivel |
| **Auto-Recuperación** | WorkerServiceManager detecta y lanza servicios caídos (WinRM, RDP, PsExec) |
| **12 Adaptadores** | Ollama, LM Studio, Jan, Groq, Gemini, OpenRouter, DeepSeek, HuggingFace, Web Agent (Playwright) |

---
## 💖 Apoya el proyecto

[![Sponsor en Liberapay](https://img.shields.io/badge/Sponsor-Liberapay-yellow?logo=liberapay)](https://liberapay.com/OscarFeMa)
## Inicio Rápido

```bash
# 1. Entorno virtual
python -m venv venv

# 2. Dependencias
.\venv\Scripts\pip install -r backend\requirements.txt

# 3. Configurar .env
copy .env.example .env

# 4. Iniciar backend
scripts\windows\run-backend.bat

# 5. Verificar
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/debates/list
```

El panel de administración se sirve automáticamente en `http://localhost:8000/admin`.

---

## Seguridad

- Contacto de seguridad: `security@synapsecode.org`

---

## Estructura del Proyecto

```
SynapseCode/
├── backend/
│   ├── main.py                     # FastAPI app + lifespan
│   ├── config.py                   # Pydantic Settings
│   ├── adapters/                   # 12 conectores de IA
│   ├── engine/                     # Motor de debate (controllers, tribunal, registry)
│   ├── api/
│   │   ├── routes/                 # Endpoints REST (debate, system, health, cache, etc.)
│   │   └── websocket.py            # WebSocket handler
│   ├── database/                   # SQLite, Supabase, migraciones
│   ├── caching/                    # Caché semántica
│   ├── memory/                     # Memoria híbrida v2
│   ├── monitoring/                 # Prometheus metrics
│   ├── network/                    # Discovery P2P, heartbeat, handshake
│   ├── services/                   # RDP, sync, backups, GPU metrics
│   └── tests/                      # 177 tests (pytest)
├── frontend/
│   ├── web/                        # Landing pública (synapsecode.org)
│   ├── control-center/             # Control Center (Vanilla JS)
│   └── src/                        # React SPA
├── scripts/
│   ├── windows/                    # .bat scripts de gestión
│   └── ...                         # Diagnóstico, utilidades Python
├── docker/
│   ├── Dockerfile.master
│   └── Dockerfile.worker
├── database/
│   └── migrations/                 # Esquemas SQL
├── docs/
│   ├── setup/                      # Guías de instalación
│   └── ...                         # Documentación adicional
├── RedSynapse/                     # Versión experimental simplificada
├── .env.example
├── LICENSE
└── README.md
```
## 💖 Apoya el proyecto

[![Sponsor en Liberapay](https://img.shields.io/badge/Sponsor-Liberapay-yellow?logo=liberapay)](https://liberapay.com/OscarFeMa)
---

## Pruebas

```bash
.\venv\Scripts\python -m pytest backend/tests/ -v
```

177 tests. CI/CD obligatorio en cada PR. Linting con Ruff.

---

## Licencia

MIT © 2025–2026 Oscar Fernandez Martin (OscarFeMa)

---

<a name="english"></a>
# 🇬🇧 SynapseCode v3.0

A **hybrid collective reasoning** platform that orchestrates multiple AI models in role-structured debates, with a **Tribunal of Magistrates** verdict.

**Master–Worker architecture**: Master PC orchestrates, Worker PC runs local models.

---

## Features

| Module | Description |
|---|---|
| **Debate Engine** | Sequential (4–6 agents), Iterative, Ultra Crossing (12+ agents) with forced consensus |
| **Tribunal of Magistrates** | 3 roles (Defender, Prosecutor, Arbitrator) with fallback chains and configurable consensus |
| **Control Center v3** | Compact dashboard (4 panels), debate launching, history, multi-format export, zero-dependency Vanilla JS |
| **Intelligent Assignment** | Model Registry (25+ models), web rankings evaluator, automatic Role Matcher |
| **EMA Reputation** | TSA (coherence), IID (information density), PVT (factual accuracy) — weighted global score |
| **Web Search** | DuckDuckGo + Trafilatura, web context injected into debates |
| **Professional Reports** | Interactive HTML, PDF, DOCX with charts and verdict |
| **Semantic Cache** | Embedding-based similarity, configurable TTL, per-model invalidation |
| **Hybrid Memory v2** | Local SQLite + Supabase Cloud sync, persistent queue with retries |
| **Data Warehouse** | Automatic aggregations, topic trending, model performance |
| **Observability** | Prometheus `/metrics`, rotating logs (10MB/5 backups), multi-level health checks |
| **Self-Recovery** | WorkerServiceManager detects and launches failed services (WinRM, RDP, PsExec) |
| **12 Adapters** | Ollama, LM Studio, Jan, Groq, Gemini, OpenRouter, DeepSeek, HuggingFace, Web Agent (Playwright) |

---

## Quick Start

```bash
# 1. Virtual environment
python -m venv venv

# 2. Install dependencies
.\venv\Scripts\pip install -r backend\requirements.txt    # Windows
./venv/bin/pip install -r backend/requirements.txt         # Linux/Mac

# 3. Configure .env
copy .env.example .env       # Windows
cp .env.example .env         # Linux/Mac

# 4. Start backend
scripts\windows\run-backend.bat   # Windows
# or manually:
set PYTHONPATH=.
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1

# 5. Verify
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/debates/list
```

Admin panel served at `http://localhost:8000/admin`.

---

## Security

- Security contact: `security@synapsecode.org`
## 💖 Apoya el proyecto

[![Sponsor en Liberapay](https://img.shields.io/badge/Sponsor-Liberapay-yellow?logo=liberapay)](https://liberapay.com/OscarFeMa)
---

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `NODE_ROLE` | `MASTER` | Node role (MASTER / WORKER) |
| `HOST` | `0.0.0.0` | Listen IP |
| `PORT` | `8000` | Server port |
| `WORKER_OLLAMA_PORT` | `11434` | Ollama port on Worker |
| `WORKER_LM_STUDIO_PORT` | `1234` | LM Studio port on Worker |
| `WORKER_JAN_PORT` | `1337` | Jan port on Worker |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GROQ_API_KEY` | — | Groq API key |
| `DEEPSEEK_API_KEY` | — | DeepSeek API key |
| `HF_TOKEN` | — | HuggingFace token |
| `SUPABASE_URL` | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | — | Supabase anon key |
| `WEB_AGENT_ENABLED` | `true` | Enable Web Agent |
| `MAX_CONCURRENT_SESSIONS` | `3` | Max concurrent debates |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_DIR` | `logs` | Logs directory |

Full reference in [.env.example](.env.example).

---

## Tests

```bash
.\venv\Scripts\python -m pytest backend/tests/ -v    # Windows
./venv/bin/python -m pytest backend/tests/ -v         # Linux/Mac
```

177 tests. CI/CD mandatory on every PR. Linting with Ruff.

---

## License

MIT © 2025–2026 Oscar Fernandez Martin (OscarFeMa)

---
## 💖 Apoya el proyecto

[![Sponsor en Liberapay](https://img.shields.io/badge/Sponsor-Liberapay-yellow?logo=liberapay)](https://liberapay.com/OscarFeMa)
*SynapseCode v3.0 · [synapsecode.org](https://synapsecode.org)*
