# Informe de Estado del Proyecto SynapseCode

**Fecha:** 17 de mayo de 2026  
**Versión:** 2.8.0  
**Último commit:** `4446798` — docs: update README, HISTORY and CHANGELOG to v2.8

---

## Resumen Ejecutivo

SynapseCode es una plataforma de **razonamiento colectivo híbrido** que orquesta múltiples modelos de IA en debates estructurados por roles, con veredicto del **Tribunal de Magistrados**. Arquitectura **Master-Worker** sobre red local: Master (localhost:8000) orquesta, Worker (192.168.1.43) ejecuta modelos locales vía Ollama, LM Studio y Jan.

**Estado actual:** ✅ Funcional. CI/CD pasando (lint + tests + security + build). Debates secuenciales con búsqueda web en tiempo real, reportes HTML/PDF automáticos, fallback de modelos, y recuperación CUDA.

---

## Arquitectura

```
[Master: localhost:8000] <--- LAN ---> [Worker: 192.168.1.43]
  FastAPI + Control Center                 Ollama (11434)
  SQLite + Supabase sync                   LM Studio (1235)
  Tribunal + Orchestrator                  Jan (1337)
  Web Search (ddgs + trafilatura)          GPU/CPU inference
```

### Topología de Red
| Nodo | Hostname | IP | Rol |
|------|----------|----|-----|
| Master | sobremesa | localhost | Orquestador, API, UI |
| Worker | makederpc | 192.168.1.43 | Inferencia local |

---

## Componentes Principales

### Backend Python (FastAPI)

| Módulo | Archivo | Función |
|--------|---------|---------|
| **API Routes** | `backend/api/routes/` | REST endpoints + WebSockets |
| **Debate Engine** | `backend/engine/sequential_debate_controller.py` | Debate secuencial multi-modelo |
| **Tribunal** | `backend/engine/tribunal.py` | 3 magistrados (evidencia, riesgo, alineación) |
| **Local Engine Manager** | `backend/engine/local_engine_manager.py` | Gestión Ollama/LM Studio/Jan |
| **Web Search** | `backend/engine/web_search_service.py` | DuckDuckGo + Trafilatura |
| **Report Generator** | `backend/engine/report_generator.py` | HTML (Chart.js) + PDF (xhtml2pdf) |
| **Reputation** | `backend/engine/reputation_unified.py` | EMA scores (TSA, IID, PVT) |
| **Adapters** | `backend/adapters/` | Ollama, OpenRouter, Groq, Gemini, DeepSeek, LM Studio, Jan |

### Control Center (Web UI)

Vanilla JS, zero dependencies, 6 pestañas: Command, Launcher, Metrics, Tribunal, Models, History.

### Base de Datos

- **SQLite local:** `data/synapse.db` — debates, turnos, reputación, caché
- **Supabase Cloud:** Sync asíncrono con cola persistente y reintentos

---

## Funcionalidades de v2.8 (última versión)

### Añadido en esta versión
- ✅ **Búsqueda web real:** DuckDuckGo (`ddgs`) + Trafilatura para contenido completo
- ✅ **Reportes HTML/PDF:** Generación automática post-debate con gráficos y métricas
- ✅ **Fallback local:** Agentes locales fallan → fallback automático a `llama3:8b`
- ✅ **Recuperación CUDA:** Detecta errores GPU, limpia memoria y reintenta
- ✅ **Validación respuestas vacías:** 0 tokens lanza RuntimeError (antes silent fail)
- ✅ **HTTP 500 en streaming:** Detectado y reportado correctamente
- ✅ **warm_model retry:** 2 intentos con delay para errores transitorios
- ✅ **Safety policy:** `.safety-policy.yml` para CI/CD vulnerability checks

### Motor de Debate
- Debates secuenciales multi-modelo con roles (Analista, Crítico, Sintetizador, Validador)
- Debates iterativos con cruzamientos críticos
- Ultra Crossing: 12+ agentes, múltiples fases
- Consenso forzado con umbral configurable
- Reducción al absurdo (eliminación de sesgos de complacencia)
- Pausar/reanudar/continuar debates

### Tribunal de Magistrados
- 3 roles: Defensor (evidencia), Fiscal (riesgo), Árbitro (alineación)
- Fallback chains: local → local reserve → cloud fallback
- Protocolo de consenso forzado o libre

### Sistema de Reputación EMA
- **TSA** (Coherencia): Consistencia lógica
- **IID** (Info Density): Densidad informativa
- **PVT** (Veracidad): Precisión factual
- Score global: Media ponderada EMA

### Observabilidad
- Prometheus Metrics: `/metrics`
- Logging rotatorio: 4 archivos, rotación 10MB/5 backups
- Health checks: `/health`, `/health/live`, `/health/ready`, `/health/dependencies`

---

## Modelos Disponibles en Worker (Ollama)

| Modelo | Tamaño | Estado | Uso |
|--------|--------|--------|-----|
| `llama3:8b` | 4.7 GB | ✅ Estable | Fallback principal, tribunal |
| `llama3.1:8b` | 4.9 GB | ⚠️ 18.4GB RAM req | Debate (fallback si hay memoria) |
| `gemma3:4b` | 3.3 GB | ✅ Estable | Debate rápido |
| `qwen2.5-coder:14b` | 9.0 GB | ⚠️ 14GB RAM req | Debate especializado |
| `qwen2.5-coder:14b-instruct-q5_K_M` | 10.5 GB | ⚠️ Alto consumo | Backup coder |
| `phi3:mini` | 2.2 GB | ⚠️ 50GB RAM req (corrupto?) | No usable actualmente |
| `mistral:7b` | 4.4 GB | ✅ Estable | Tribunal (magistrado riesgo) |
| `gemma:7b` | 5.0 GB | ✅ Disponible | Backup |
| `gemma4:latest` | 9.6 GB | ✅ Disponible | Backup |
| `deepseek-r1:7b` | 4.7 GB | ✅ Disponible | Reasoning |
| `nemotron-mini` | 2.7 GB | ✅ Estable | Debate rápido |
| `tinyllama` | 0.6 GB | ✅ Disponible | Tests |
| `qwen2.5:3b` | 1.9 GB | ✅ Disponible | Rápido |

**Nota:** La GPU del Worker tiene ~13.5 GB disponibles. Modelos que requieren más (phi3:mini, llama3.1:8b, qwen2.5-coder:14b) fallan con HTTP 500 y el sistema hace fallback automático a `llama3:8b`.

---

## CI/CD Pipeline

| Job | Herramienta | Estado |
|-----|-------------|--------|
| **Lint** | Ruff (E,F,W,I) | ✅ Pasando |
| **Format** | Ruff format check | ✅ Pasando |
| **Tests** | pytest (unit + integration + API) | ✅ 162 tests |
| **Security** | Bandit + Safety | ✅ Pasando |
| **Build** | python -m build | ✅ Pasando |

Config: `.github/workflows/ci.yml` + `.safety-policy.yml`

---

## Estructura de Archivos

```
D:\proyectos\Synapse\
├── backend/
│   ├── api/                    # FastAPI routes + middleware
│   ├── adapters/               # Ollama, Groq, Gemini, etc.
│   ├── config.py               # Pydantic settings
│   ├── database/               # SQLAlchemy models + local_db
│   ├── engine/                 # Debate controllers, tribunal, reports
│   ├── memory/                 # Hybrid memory v2
│   ├── monitoring/             # Prometheus metrics
│   ├── services/               # Supabase sync, RDP, worker launcher
│   ├── tests/                  # unit, integration, api tests
│   ├── main.py                 # FastAPI entry point
│   └── requirements.txt        # Python dependencies
├── frontend/                   # React + Vite (Control Center v2)
├── desktop/                    # Electron app (legacy)
├── data/
│   ├── debates/                # Transcripts markdown
│   ├── reports/                # HTML + PDF reports
│   └── synapse.db              # SQLite database
├── logs/                       # Rotating log files
├── .github/workflows/ci.yml    # CI/CD pipeline
├── .safety-policy.yml          # Safety vulnerability policy
├── README.md                   # Documentation
├── CHANGELOG.md                # Version history
├── HISTORY.md                  # Development timeline
└── .env                        # Environment config (gitignored)
```

---

## Problemas Conocidos

| Problema | Severidad | Estado | Workaround |
|----------|-----------|--------|------------|
| `phi3:mini` requiere 50GB RAM | Alta | Conocido | Fallback a llama3:8b |
| `llama3.1:8b` requiere 18.4GB RAM | Media | Conocido | Fallback a llama3:8b |
| `qwen2.5-coder:14b` requiere 14GB RAM | Media | Conocido | Fallback a llama3:8b |
| CUDA runner crash bajo carga | Media | Mitigado | Recovery automático + retry |
| OpenRouter 401 Unauthorized | Baja | Sin fix | Cloud fallback deshabilitado |
| `weasyprint` no funciona en Windows | Baja | Resuelto | Usando xhtml2pdf |

---

## Próximos Pasos

### Prioridad Alta
- [ ] Investigar por qué `phi3:mini` reporta 50GB RAM (posible modelo corrupto)
- [ ] Configurar API key de OpenRouter/Groq/Gemini para cloud fallback del tribunal
- [ ] Optimizar gestión de memoria GPU en Worker (unload agresivo entre turnos)

### Prioridad Media
- [ ] Agregar métricas de uso de GPU/RAM del Worker al dashboard
- [ ] Implementar debate paralelo (múltiples agentes simultáneos)
- [ ] Mejorar parsing JSON en structured reports (a veces no encuentra JSON válido)

### Prioridad Baja
- [ ] Migrar Control Center de vanilla JS a React (frontend/ ya existe)
- [ ] Agregar notificaciones push para debates completados
- [ ] Exportar reports a DOCX (librería docx ya instalada)

---

## Dependencias Principales

### Backend (Python)
```
fastapi, uvicorn, httpx, aiosqlite, sqlalchemy
ollama (via adapters), ddgs, trafilatura, xhtml2pdf
structlog, prometheus-client, playwright
```

### Frontend (React)
```
react, react-router-dom, vite, tailwindcss, lucide-react
```

### CI/CD
```
ruff, pytest, pytest-asyncio, pytest-cov, bandit, safety
```

---

## Conclusión

SynapseCode v2.8 es una plataforma funcional de debate multi-agente con búsqueda web en tiempo real, reportes profesionales, y sistema robusto de fallback. El pipeline CI/CD pasa completamente. Los únicos problemas pendientes son limitaciones de hardware del Worker (GPU con 13.5GB disponibles) que se mitigan con fallback automático a modelos más ligeros.
