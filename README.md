# 🧠 SynapseCode v2.8

Plataforma de **razonamiento colectivo híbrido** que orquesta múltiples modelos de IA en debates estructurados por roles, con veredicto del **Tribunal de Magistrados**.

Arquitectura **Master-Worker**: PC Master orquesta, PC Worker (192.168.1.43) ejecuta modelos locales.

---

## 🎯 Características Principales

### Control Center v2.8
- **Panel Web Completo**: 6 pestañas — Command, Launcher, Metrics, Tribunal, Models, History
- **Zero Dependencies**: Vanilla JS puro, sin build, sin node_modules
- **Estado en Tiempo Real**: Polling automático cada 10s
- **Conexión Master ↔ Worker**: Detección automática de IP, heartbeat monitoring
- **Monitor de Servicios**: Ollama, LM Studio, Jan con auto-lanzamiento
- **Panel de Bases de Datos**: SQLite local + Supabase Cloud con sync status
- **Diseño Neural Terminal**: Dark mode, grid de circuito, animaciones CSS

### Búsqueda Web en Tiempo Real
- **DuckDuckGo Search** (`ddgs`): Resultados reales sin API key
- **Trafilatura**: Extracción de contenido completo de artículos
- **Contexto web para debates**: Información actualizada inyectada en prompts
- **Verificación factual del tribunal**: Datos reales para validar argumentos

### Reportes Profesionales
- **HTML interactivo**: Chart.js, tema oscuro, responsive
- **PDF imprimible**: Gráficos SVG inline, tema claro
- **Generación automática**: Post-debate, con métricas y veredicto

### Motor de Debate
- **Debates Secuenciales**: Multi-modelo con roles (Analista, Crítico, Sintetizador, Validador)
- **Debates Iterativos**: Cruzamientos críticos entre agentes, validación, búsqueda de consenso
- **Ultra Crossing**: Debate avanzado con 12+ agentes y múltiples fases
- **Consenso Forzado**: Protocolo de consenso con umbral configurable
- **Continuación/Pausa**: `POST /debates/{id}/continue`, `/pause`, `/resume`
- **Reducción al Absurdo**: Eliminación de sesgos de complacencia
- **Taxonomía de Intervenciones**: Clasificación de actos discursivos

### Tribunal de Magistrados
- **3 Roles Especializados**: Defensor, Fiscal, Árbitro
- **Fallback Chains**: Si un modelo falla, usa el siguiente automáticamente
- **Protocolo de Consenso**: Forzado o libre con umbral configurable

### Sistema de Reputación EMA
- **TSA** (Coherencia): Consistencia lógica del argumento
- **IID** (Info Density): Densidad informativa
- **PVT** (Veracidad): Precisión factual
- **Score Global**: Media ponderada EMA

### Caché Semántica
- Embeddings por similitud de texto
- TTL configurable, umbral de similitud ajustable
- Invalidación y limpieza por modelo/engine

### Data Warehouse
- Agregaciones automáticas: métricas diarias, trending de topics, rendimiento de modelos
- Queryable vía `GET /api/v1/system/analytics`

### Observabilidad
- **Prometheus Metrics**: `/metrics` endpoint
- **Logging Rotatorio**: 4 archivos (general, errores, engine, API), rotación 10MB/5 backups
- **Health Checks**: `/health`, `/health/live`, `/health/ready`, `/health/dependencies`

### Memoria Híbrida v2
- SQLite local + Supabase Cloud sync
- Cola persistente con reintentos y backoff exponencial

### Auto-Recuperación
- **WorkerServiceManager**: Detecta y lanza servicios caídos (WinRM, RDP, PsExec)

### 12 Adaptadores de IA
| Motor | Tipo | Modelos |
|---|---|---|
| **Ollama** | Local (Worker) | llama3, mistral, qwen2.5, deepseek-r1, etc. |
| **LM Studio** | Local (Worker) | gemma, deepseek-coder, qwen3.5 |
| **Jan** | Local (Worker) | Cualquier modelo compatible OpenAI |
| **Groq** | Cloud (Free) | llama-3.1-8b, llama-3.3-70b |
| **Gemini** | Cloud (Free) | gemini-2.5-flash, gemini-2.0-flash |
| **OpenRouter** | Cloud | 200+ modelos |
| **DeepSeek** | Cloud | deepseek-chat, deepseek-reasoner |
| **HuggingFace** | Cloud | Models vía Inference API |
| **Web Agent** | Playwright | 10 sitios de IA con stealth |

### Exportación
- JSON estructurado, Markdown, PDF (HTML imprimible)

---

## 🚀 Inicio Rápido

### Backend
```bash
cd D:\proyectos\SynapseCode

# 1. Crear entorno virtual (primera vez)
python -m venv venv

# 2. Instalar dependencias
.\venv\Scripts\pip install -r backend\requirements.txt

# 3. Configurar .env (copiar .env.example y editar)
copy .env.example .env

# 4. Iniciar backend
run_backend.bat
# o manualmente:
set PYTHONPATH=.
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Control Center
```bash
# Opción 1: Script
open_control_center.bat

# Opción 2: Manual
cd frontend\control-center
python -m http.server 8080
# Abrir http://localhost:8080
```

### Verificar
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/debates/list
```

---

## 📁 Estructura del Proyecto

```
SynapseCode/
├── backend/
│   ├── main.py                     # FastAPI app + lifespan
│   ├── config.py                   # Pydantic Settings + env vars
│   ├── logging_config.py           # Logging rotatorio
│   ├── pre_startup_check.py        # Verificación pre-lanzamiento
│   ├── requirements.txt            # Dependencias Python
│   │
│   ├── adapters/                   # 12 conectores de IA
│   │   ├── base.py                 # Base OpenAI-compatible
│   │   ├── ollama.py               # Ollama (local Worker)
│   │   ├── lm_studio.py            # LM Studio (local Worker)
│   │   ├── jan.py                  # Jan.ai (local Worker, /v1)
│   │   ├── groq.py                 # Groq Cloud
│   │   ├── gemini.py               # Google Gemini
│   │   ├── openrouter.py           # OpenRouter (200+ modelos)
│   │   ├── deepseek.py             # DeepSeek
│   │   ├── huggingface.py          # HuggingFace Inference API
│   │   ├── web_agent.py            # Playwright (10 sitios IA)
│   │   └── http_client_manager.py  # HTTP connection pooling
│   │
│   ├── engine/                     # Motor de debate
│   │   ├── sequential_debate_controller.py  # Debate secuencial
│   │   ├── ultra_debate_controller.py       # Ultra crossing (12+ agentes)
│   │   ├── consensus_debate_controller.py   # Protocolo de consenso
│   │   ├── base_debate_controller.py        # Base controller
│   │   ├── round_controller.py              # Control de rondas
│   │   ├── session_manager.py               # Gestión de sesiones
│   │   ├── agent_orchestrator.py            # Orquestador de agentes
│   │   ├── tribunal.py                      # Tribunal de Magistrados
│   │   ├── tribunal_config.py               # Configuración del Tribunal
│   │   ├── convergence.py                   # Evaluador de convergencia
│   │   ├── quality_monitor.py               # Filtro de calidad
│   │   ├── reputation_unified.py            # Reputación EMA
│   │   ├── reductio_absurdum.py             # Reducción al absurdo
│   │   ├── intervention_taxonomy.py         # Taxonomía de intervenciones
│   │   ├── debate_models.py                 # Modelos de datos
│   │   ├── worker_launcher.py               # Auto-lanzamiento de servicios
│   │   ├── task_manager.py                  # Background tasks con retry
│   │   ├── local_engine_manager.py          # Gestión de engines locales
│   │   └── prompts.py                       # Templates por rol
│   │
│   ├── api/routes/                 # Endpoints REST
│   │   ├── debate.py               # Debates (CRUD, export, continue, pause)
│   │   ├── system.py               # Chat directo, worker, RDP, analytics
│   │   ├── health.py               # Health checks multi-servicio
│   │   ├── cache.py                # Gestión de caché semántica
│   │   ├── sessions.py             # Gestión de sesiones
│   │   ├── runs.py                 # Historial de ejecuciones
│   │   ├── network.py              # Discovery P2P, nodos
│   │   ├── websockets.py           # WebSocket streaming
│   │   └── debug.py                # Diagnóstico
│   │
│   ├── api/
│   │   ├── websocket.py            # WebSocket handler
│   │   └── middleware.py           # Middleware CORS, logging
│   │
│   ├── database/
│   │   ├── local_db.py             # SQLite async engine
│   │   ├── models.py               # SQLAlchemy models (7 tablas)
│   │   ├── warehouse.py            # Data Warehouse aggregations
│   │   ├── supabase_client.py      # Supabase client
│   │   └── migrations/             # SQLite migrations
│   │       └── sqlite_migrations.py
│   │
│   ├── caching/
│   │   └── semantic_cache.py       # Caché semántica con embeddings
│   │
│   ├── memory/
│   │   └── hybrid_memory_v2.py     # Memoria híbrida local+cloud
│   │
│   ├── monitoring/
│   │   └── prometheus.py           # Métricas Prometheus
│   │
│   ├── network/
│   │   ├── discovery.py            # Discovery P2P de nodos
│   │   ├── heartbeat.py            # Heartbeat Master-Worker
│   │   └── tcp_handshake.py        # Handshake TCP
│   │
│   ├── services/
│   │   ├── supabase_sync.py        # Sync a Supabase Cloud
│   │   └── rdp_manager.py          # Gestión RDP al Worker
│   │
│   └── tests/
│       ├── test_comprehensive.py   # 162 tests (21 niveles)
│       ├── test_system.py
│       └── exhaustive_test.py
│
├── frontend/
│   ├── control-center/             # Control Center v2.7 (Vanilla JS)
│   │   └── index.html              # App completa, zero dependencies
│   ├── admin.html                  # Admin dashboard legacy
│   └── src/                        # React frontend (legacy)
│
├── .env.example                    # Template de configuración
├── run_backend.bat                 # Lanzar backend
├── open_control_center.bat         # Lanzar Control Center
├── start_master.bat                # Lanzar todo (backend + frontend)
└── README.md
```

---

## 🔌 API Endpoints

### Debates
| Method | Path | Descripción |
|---|---|---|
| `POST` | `/api/v1/debates/create` | Crear debate secuencial |
| `POST` | `/api/v1/debates/create/iterative` | Crear debate iterativo |
| `POST` | `/api/v1/debates/consensus/create` | Crear debate de consenso |
| `GET` | `/api/v1/debates/list` | Lista debates activos |
| `GET` | `/api/v1/debates/{id}` | Estado completo de un debate |
| `GET` | `/api/v1/debates/{id}/status` | Estado resumido |
| `GET` | `/api/v1/debates/{id}/transcript` | Transcripción completa |
| `GET` | `/api/v1/debates/{id}/report` | Informe estructurado JSON |
| `POST` | `/api/v1/debates/{id}/continue` | Continuar debate completado |
| `POST` | `/api/v1/debates/{id}/pause` | Pausar debate en ejecución |
| `POST` | `/api/v1/debates/{id}/resume` | Reanudar debate pausado |
| `DELETE` | `/api/v1/debates/{id}` | Eliminar debate |
| `GET` | `/api/v1/debates/{id}/export/json` | Exportar JSON |
| `GET` | `/api/v1/debates/{id}/export/markdown` | Exportar Markdown |
| `GET` | `/api/v1/debates/{id}/export/pdf` | Exportar PDF |
| `GET` | `/api/v1/debates/history/list` | Historial de debates |
| `GET` | `/api/v1/debates/history/{id}` | Debate histórico |
| `GET` | `/api/v1/debates/reputation` | Reputaciones de modelos |
| `GET` | `/api/v1/debates/reputation/{model}/{role}` | Reputación específica |

### Cloud (Supabase)
| Method | Path | Descripción |
|---|---|---|
| `GET` | `/api/v1/debates/cloud/status` | Estado de conexión Supabase |
| `GET` | `/api/v1/debates/cloud/list` | Lista debates en cloud |
| `GET` | `/api/v1/debates/cloud/{id}` | Debate desde cloud |
| `POST` | `/api/v1/debates/cloud/sync/{id}` | Sync debate a cloud |

### System
| Method | Path | Descripción |
|---|---|---|
| `GET` | `/api/v1/system/settings` | Configuración actual |
| `POST` | `/api/v1/system/settings` | Actualizar configuración |
| `POST` | `/api/v1/system/chat/direct` | Chat directo a modelo |
| `GET` | `/api/v1/system/metrics` | Métricas del sistema |
| `GET` | `/api/v1/system/analytics` | Analytics del Data Warehouse |
| `GET` | `/api/v1/system/health/sync` | Estado de sync Supabase |
| `GET` | `/api/v1/system/tribunal/config` | Configuración del Tribunal |
| `GET` | `/api/v1/system/health` | Health check del sistema |
| `POST` | `/api/v1/system/wake-worker` | Wake-on-LAN / RDP al Worker |
| `POST` | `/api/v1/system/wake-worker-auto` | Wake automático |
| `GET` | `/api/v1/system/rdp-status` | Estado RDP |
| `GET` | `/api/v1/system/worker/services` | Estado servicios Worker |
| `POST` | `/api/v1/system/worker/services/launch` | Lanzar servicio Worker |

### Cache
| Method | Path | Descripción |
|---|---|---|
| `GET` | `/api/v1/cache/stats` | Estadísticas de caché |
| `POST` | `/api/v1/cache/invalidate` | Invalidar caché |
| `POST` | `/api/v1/cache/cleanup` | Limpiar expirados |
| `GET` | `/api/v1/cache/health` | Health de caché |

### Health
| Method | Path | Descripción |
|---|---|---|
| `GET` | `/health` | Health check completo |
| `GET` | `/health/live` | Liveness check |
| `GET` | `/health/ready` | Readiness check |
| `GET` | `/health/dependencies` | Estado de dependencias |

### WebSocket
| Path | Descripción |
|---|---|
| `/ws/sessions/{id}` | Streaming en tiempo real de debate |

### Network
| Method | Path | Descripción |
|---|---|---|
| `GET` | `/api/v1/network/nodes` | Nodos descubiertos |
| `GET` | `/api/v1/network/status` | Estado de red P2P |

---

## ⚙️ Configuración (.env)

### Servidor
| Variable | Default | Descripción |
|---|---|---|
| `NODE_ROLE` | `MASTER` | Rol del nodo (MASTER/WORKER) |
| `HOST` | `0.0.0.0` | IP de escucha |
| `PORT` | `8000` | Puerto del servidor |

### Worker
| Variable | Default | Descripción |
|---|---|---|
| `WORKER_OLLAMA_PORT` | `11434` | Puerto Ollama en Worker |
| `WORKER_LM_STUDIO_PORT` | `1234` | Puerto LM Studio en Worker |
| `WORKER_JAN_PORT` | `1337` | Puerto Jan en Worker |

### APIs Cloud
| Variable | Descripción |
|---|---|
| `OPENROUTER_API_KEY` | API key de OpenRouter |
| `GEMINI_API_KEY` | API key de Google Gemini |
| `GROQ_API_KEY` | API key de Groq |
| `DEEPSEEK_API_KEY` | API key de DeepSeek |
| `HF_TOKEN` | Token de HuggingFace |

### Supabase
| Variable | Descripción |
|---|---|
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_ANON_KEY` | Clave pública anon |

### Features
| Variable | Default | Descripción |
|---|---|---|
| `WEB_AGENT_ENABLED` | `true` | Habilitar Web Agent |
| `MAX_CONCURRENT_SESSIONS` | `3` | Máximo debates simultáneos |
| `INTERVENTION_TAXONOMY_ENABLED` | `true` | Taxonomía de intervenciones |
| `QUALITY_MONITOR_ENABLED` | `true` | Monitor de calidad |
| `AGENT_REPUTATION_ENABLED` | `true` | Sistema de reputación |
| `HYBRID_MEMORY_V2_ENABLED` | `true` | Memoria híbrida |

### Logging
| Variable | Default | Descripción |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Nivel de logging |
| `LOG_DIR` | `logs` | Directorio de logs |
| `LOG_MAX_BYTES` | `10485760` | Tamaño máximo por archivo (10MB) |
| `LOG_BACKUP_COUNT` | `5` | Número de backups |
| `LOG_TO_FILE` | `true` | Escribir logs a archivo |

### Timeouts
| Variable | Descripción |
|---|---|
| `MODEL_TIMEOUTS` | JSON con patrones de modelo → timeout en segundos |

---

## 🧪 Tests

```bash
cd D:\proyectos\SynapseCode
.\venv\Scripts\python -m pytest backend/tests/test_comprehensive.py -v
```

**162 tests** cubriendo 21 niveles: imports, config, API endpoints, debate flow, tribunal, cache, reputation, timeouts, logging.

---

## 📄 Licencia

MIT

---

*SynapseCode v2.7 · OscarFeMa · Mayo 2026*
