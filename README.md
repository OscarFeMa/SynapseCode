# 🧠 Synapse Code v2.4

Plataforma de **razonamiento colectivo híbrido** que orquesta múltiples modelos de IA en un debate estructurado por roles, con veredicto soberano del **Tribunal de Magistrados**.

Arquitectura **Master-Worker**: PC Master orquesta, PC Worker (MakederPC) ejecuta modelos locales.

---

## 🎯 Características Principales

- **Arquitectura Híbrida**: Master (orquestación) + Worker (Ollama, LM Studio, Jan)
- **Tribunal de Magistrados**: 3 roles especializados con Protocolo de Consenso Forzado y fallback chains configurables
- **Reducción al Absurdo**: Eliminación de sesgos de complacencia via técnica lógica
- **Sistema de Reputación EMA**: Métricas dinámicas por modelo y rol (TSA, IID, PVT)
- **Caché Semántica**: Respuestas cacheadas por similitud de embeddings (-40% latencia)
- **Data Warehouse**: Agregaciones automáticas para análisis histórico de debates
- **Prometheus Metrics**: Observabilidad con `/metrics` endpoint
- **Múltiples Motores**: Ollama, LM Studio, Jan, Groq, Gemini, OpenRouter, DeepSeek
- **Web Agent**: 10 sitios de IA vía Playwright con stealth anti-detección
- **Debates Iterativos**: Multi-agente con cruzamientos críticos y consenso
- **Continuación de Debates**: `POST /debates/{id}/continue` para añadir rondas
- **Streaming en Tiempo Real**: WebSocket con token buffering optimizado
- **Memoria Híbrida**: SQLite local + Supabase sync con queue persistente
- **Auto-Recuperación**: WorkerServiceManager lanza servicios caídos automáticamente
- **Control Center Web**: Panel completo en /admin con dashboard, debates, métricas
- **Exportación**: JSON estructurado, Markdown, PDF de cualquier debate

---

## 🚀 Inicio Rápido

```bash
# 1. Configurar entorno
cd D:\Synapse_2026-05-26
python -m venv venv
venv\Scripts\pip install -r backend\requirements.txt

# 2. Editar .env con tus API keys (opcional, Ollama funciona sin claves)
#    Las APIs gratuitas se configuran desde:
python scripts\get_free_apis.py

# 3. Iniciar servidor
python -c "import sys; sys.path.insert(0, '.'); from backend.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"

# 4. Verificar health check
curl http://localhost:8000/health
```

---

## 🔧 APIs Cloud Configuradas

| Servicio | Estado | Modelo | Límite gratuito |
|----------|--------|--------|----------------|
| **Groq** | ✅ Funcionando | `llama-3.1-8b-instant`, `llama-3.3-70b-versatile` | 30 req/min |
| **Gemini** | ✅ Funcionando | `gemini-2.5-flash`, `gemini-2.0-flash` | 60 req/min |
| **Ollama** (local) | ✅ 12 modelos | `llama3`, `mistral`, `qwen2.5`, `deepseek-r1`, etc. | Gratis |
| **LM Studio** (local) | ✅ 4 modelos | `gemma-4-e4b`, `deepseek-coder`, `qwen3.5-9b` | Gratis |

---

## 📁 Estructura del Proyecto

```
SynapseCode/
├── backend/
│   ├── main.py                 # FastAPI app + lifespan
│   ├── config.py               # Pydantic Settings + env
│   ├── adapters/               # 10 conectores de IA
│   │   ├── groq.py             # Groq Cloud (Llama 3, Mixtral)
│   │   ├── gemini.py           # Google Gemini (Flash, Pro)
│   │   ├── ollama.py           # Ollama (local Worker)
│   │   ├── lm_studio.py        # LM Studio (local Worker)
│   │   ├── openrouter.py       # OpenRouter (200+ modelos)
│   │   ├── deepseek.py         # DeepSeek Chat
│   │   ├── web_agent.py        # Playwright (10 sitios IA)
│   │   ├── jan.py              # Jan.ai
│   │   ├── base.py             # Base OpenAI-compatible
│   │   └── http_client_manager.py  # Pooling HTTP
│   ├── engine/                 # Motor de debate
│   │   ├── sequential_debate_controller.py  # Debate secuencial multi-modelo
│   │   ├── tribunal.py                    # Tribunal de Magistrados
│   │   ├── convergence.py                 # Evaluador de convergencia
│   │   ├── debate_models.py               # Modelos de datos
│   │   ├── quality_monitor.py             # Filtro de calidad
│   │   ├── reputation_unified.py          # Reputación EMA
│   │   ├── worker_launcher.py             # Auto-lanzamiento de servicios
│   │   ├── task_manager.py                # Background tasks con retry
│   │   ├── intervention_taxonomy.py       # Clasificación de actos discursivos
│   │   ├── round_controller.py            # Control de rondas
│   │   ├── session_manager.py             # Gestión de sesiones
│   │   └── prompts.py                     # Templates por rol
│   ├── api/routes/
│   │   ├── debate.py           # Endpoints de debate
│   │   ├── system.py           # Chat directo, worker, RDP
│   │   ├── health.py           # Health check multi-servicio
│   │   ├── runs.py             # Historial de ejecuciones
│   │   └── debug.py            # Diagnóstico
│   └── memory/
│       └── hybrid_memory_v2.py # Memoria híbrida local+cloud
├── scripts/
│   ├── get_free_apis.py        # Asistente de API keys gratuitas
│   ├── worker_autostart.bat    # Auto-inicio de servicios en Worker
│   ├── web_agent_sessions.bat  # Configuración de sesiones web
│   └── setup_web_sessions.py   # Setup de navegador para Web Agent
├── frontend/                   # React + Vite
├── desktop/                    # Electron app
└── docs/
```

---

## 🏛️ Flujo del Debate

```
create_debate_with_id()
  → Por cada turno:
      → build_context_prompt() (filtra con QualityMonitor)
      → _run_local_agent() / _run_cloud_agent()
      → evaluate_response() + submit_reputation_update()
      → convergence_evaluator.evaluate() (early stop)
  → _run_tribunal() (si >= 2 turnos completados)
  → _generate_verdict() o tribunal_verdict
  → _generate_structured_report() (JSON)
  → _save_transcript()
  → hybrid_memory.enqueue_sync() vía task_manager
```

---

## 🌐 Endpoints API

### Debates
| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/debates/create` | Crear debate secuencial |
| `POST` | `/api/v1/debates/create/iterative` | Debate iterativo avanzado |
| `POST` | `/api/v1/debates/{id}/continue` | Continuar debate completado |
| `GET` | `/api/v1/debates/{id}` | Estado completo del debate |
| `GET` | `/api/v1/debates/{id}/status` | Estado resumido |
| `GET` | `/api/v1/debates/{id}/report` | Informe estructurado JSON |
| `GET` | `/api/v1/debates/{id}/transcript` | Transcripción completa |
| `GET` | `/api/v1/debates/{id}/export/json` | Exportar JSON estructurado |
| `GET` | `/api/v1/debates/{id}/export/markdown` | Exportar Markdown |
| `GET` | `/api/v1/debates/{id}/export/pdf` | Exportar HTML imprimible |
| `GET` | `/api/v1/debates/list` | Lista debates activos |
| `GET` | `/api/v1/debates/history/list` | Historial completo desde DB |
| `GET` | `/api/v1/debates/reputation` | Reputaciones de modelos |
| `DELETE` | `/api/v1/debates/{id}` | Eliminar sesión |

### Sistema
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check completo |
| `GET` | `/health/live` | Liveness check |
| `GET` | `/health/ready` | Readiness check |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/v1/system/analytics` | Resumen del Data Warehouse |
| `GET` | `/api/v1/system/tribunal-config` | Configuración del Tribunal |
| `POST` | `/api/v1/system/chat/direct` | Chat directo con cualquier modelo |
| `GET` | `/api/v1/system/worker/services` | Estado servicios Worker |
| `POST` | `/api/v1/system/worker/services/launch` | Lanzar servicio en Worker |
| `POST` | `/api/v1/system/worker/wake` | Wake-on-LAN del Worker |
| `GET` | `/api/v1/system/rdp-status` | Estado RDP |

### Caché
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/cache/stats` | Estadísticas de caché |
| `POST` | `/api/v1/cache/invalidate` | Invalidar caché |
| `POST` | `/api/v1/cache/cleanup` | Limpiar entradas expiradas |

---

## 📊 Servicios Verificados en /health

- ✅ **Base de datos SQLite** — Persistencia local
- ✅ **Ollama** — 12+ modelos open-source (Worker)
- ✅ **LM Studio** — 4 modelos GGUF (Worker)
- ✅ **Groq** — Inferencia ultrarrápida cloud
- ✅ **Gemini** — Google 2.5 Flash
- ✅ **Web Agent** — Playwright con 10 sitios IA
- ✅ **Task Manager** — Background tasks con retry
- ✅ **Memoria Híbrida** — Sync a Supabase con queue persistente
- ✅ **Caché Semántica** — Embeddings + similitud coseno
- ✅ **Prometheus** — Métricas en `/metrics`

---

## 🔄 Estado de Versiones

| Versión | Fecha | Cambios principales |
|---------|-------|-------------------|
| **v2.4** | May 2026 | Continuación de debates, caché semántica, Data Warehouse, Prometheus, Tribunal fallback chains, Reductio Absurdum, tests fijos |
| **v2.3** | May 2026 | Control Center web, exportación limpia, health check inteligente, fixes |
| **v2.2** | May 2026 | APIs cloud (Groq, Gemini), Web Agent 10 sitios, Worker auto-launch, limpieza general |
| **v2.1** | Apr 2026 | Debates iterativos, liberación RAM, maratón 10 debates |
| **v2.0** | Apr 2026 | Tribunal, WebSocket, Frontend React, reputación EMA |
| **v1.0** | Apr 2026 | Fundación: FastAPI, SQLite, motor core |

---

**Autor**: Óscar Fernandez  
**Repositorio**: https://github.com/OscarFeMa/SynapseCode  
**Worker**: `192.168.1.43` (MakederPC) — Ollama + LM Studio + Jan
