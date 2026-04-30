# 🧠 Synapse Council v2.0

Plataforma de **razonamiento colectivo híbrido** que orquesta múltiples modelos de IA en un debate estructurado por roles, con veredicto soberano del **Tribunal de Magistrados**.

---

## 🎯 Características Principales

- **Arquitectura Híbrida**: PC A (Master) + PC B (Worker) para soberanía neuronal
- **Tribunal de Magistrados**: 3 roles especializados con Protocolo de Consenso Forzado (PCO)
- **Sistema de Reputación EMA**: Métricas dinámicas por agente y dominio
- **Múltiples Motores**: Ollama, LM Studio, Jan.ai, OpenRouter, Web Agent (Playwright)
- **Hasta 3 Rondas**: Con cruce híbrido Local↔Nube
- **Streaming en Tiempo Real**: WebSocket con tokens en vivo
- **Memoria a Largo Plazo**: Supabase (`memoria-oscar`)
- **Trazabilidad Absoluta**: SQLite local con registro granular

---

## 📁 Estructura

```
synapse-council/
├── backend/
│   ├── main.py              # FastAPI + WebSocket + API endpoints
│   ├── config.py            # Pydantic Settings
│   ├── requirements.txt     # Dependencias Python
│   ├── database/
│   │   ├── models.py        # 7 tablas SQLAlchemy
│   │   └── local_db.py      # SQLite async
│   ├── adapters/            # Clientes de IA
│   │   ├── ollama.py        # Ollama (PC B)
│   │   ├── lm_studio.py     # LM Studio (PC B)
│   │   ├── jan.py           # Jan.ai (PC B)
│   │   ├── openrouter.py    # APIs comerciales
│   │   └── web_agent.py     # Playwright (ChatGPT, Claude)
│   ├── engine/              # Motor de debate (Fase 1-2)
│   │   ├── local_engine_manager.py   # Gestión de motores locales
│   │   ├── agent_orchestrator.py     # Paralelismo y persistencia
│   │   ├── round_controller.py       # 4 fases del debate
│   │   ├── session_manager.py        # Ciclo de vida de sesiones
│   │   ├── prompts.py                # Prompts por rol
│   │   ├── tribunal.py               # Tribunal de Magistrados (Fase 2)
│   │   └── convergence.py            # Evaluador de convergencia (Fase 2)
│   ├── api/                 # API routes (Fase 3)
│   │   └── websocket.py              # WebSocket manager streaming
├── frontend/                # Fase 4: React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   │   ├── ChatInput.jsx      # Formulario nueva sesión
│   │   │   │   ├── SessionView.jsx    # Vista debate en progreso
│   │   │   │   └── AgentCard.jsx      # Card de agente con streaming
│   │   │   ├── Tribunal/
│   │   │   │   └── TribunalPanel.jsx  # Panel del Tribunal
│   │   │   └── History/
│   │   │       └── SessionList.jsx    # Historial de sesiones
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js        # Hook WebSocket
│   │   │   └── useSession.js          # Hook API REST
│   │   ├── store/
│   │   │   └── useStore.js            # Zustand stores
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── scripts/
│   ├── test_health.py       # Test Fase 0
│   ├── test_session.py      # Test Fase 1-2 (debate real)
│   └── test_websocket.py    # Test Fase 3 (streaming WebSocket)
├── data/                    # SQLite local (gitignored)
└── docs/                    # Documentación
```

---

## 🚀 Instalación Rápida (Windows)

### Opción 1: Instalador Automático (Recomendado)
```batch
:: 1. Ejecutar como Administrador:
INSTALL_COMPLETE.bat

:: 2. Descargar modelos de IA:
install_models.bat

:: 3. Iniciar el sistema:
start_synapse.bat

:: 4. Abrir interfaz web:
http://localhost:8000/static/debate_manager.html
```

### Opción 2: Instalación Manual
```bash
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt

:: Configurar variables de entorno
copy .env.example .env
:: Editar .env con tus credenciales

:: Iniciar servidor
cd backend
python main.py
```

### 3. Verificar instalación
```batch
:: Comando de verificación
check_health.bat

:: O manualmente:
curl http://localhost:8000/health
```

Verificar health check:
```bash
curl http://localhost:8000/health
```

### 4. Probar Fase 1 (Debate de 1 Ronda)

**Crear sesión de debate:**
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Cuáles son las ventajas de la semana laboral de 4 días?",
    "title": "Test Fase 1",
    "max_rounds": 1
  }'
```

**Ver resultado:**
```bash
# Reemplazar <session_id> con el ID devuelto
curl http://localhost:8000/api/v1/sessions/<session_id>
```

**O usar el script de test:**
```bash
python scripts/test_session.py
```

### 5. Probar WebSocket Streaming (Fase 3)

**Conectar y ver streaming en tiempo real:**
```bash
# Terminal 1: Crear sesión y conectar WebSocket
python scripts/test_websocket.py --rounds 2
```

### 6. Iniciar Frontend React (Fase 4)

**Instalar dependencias e iniciar:**
```bash
cd synapse-council/frontend
npm install
npm run dev
```

**Abrir en navegador:**
- URL: http://localhost:5173

**Features del frontend:**
- 🎨 Tema oscuro con colores del Council (azul pizarra + ámbar)
- ⚡ Streaming en tiempo real vía WebSocket
- 🏛️ Panel del Tribunal de Magistrados con scores en vivo
- 📊 Visualización de 10 agentes en paralelo
- 📜 Historial de sesiones con filtros

**Eventos WebSocket disponibles:**
- `session_started` - Inicio de sesión
- `round_start` - Nueva ronda
- `phase_started` - Inicio de fase (ANALYSIS, CRITIQUE, SYNTHESIS, TRIBUNAL)
- `agent_token` - Token generado (streaming texto)
- `agent_completed` - Agente finalizó
- `tribunal_started`, `tribunal_objection`, `tribunal_verdict` - Eventos del Tribunal
- `session_completed` - Sesión finalizada

**Conectar vía wscat:**
```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/sessions/<session_id>
```

---

## 📊 Plan de Implementación

| Fase | Descripción | Estado |
|------|-------------|--------|
| **0** | Infraestructura base, DB, health check | ✅ COMPLETADA |
| **1** | Motor core, 1 ronda completa | ✅ COMPLETADA |
| **2** | Múltiples rondas, Tribunal de Magistrados | ✅ COMPLETADA |
| **3** | WebSocket streaming en tiempo real | ✅ COMPLETADA |
| **4** | Frontend React completo | ✅ COMPLETADA |
| **5** | Hardening, reputación EMA, tests | ✅ COMPLETADA |
| **6** | Debates Iterativos Multi-Agente | ✅ **COMPLETADA** |

### ✅ FASE 1 - Motor Core (COMPLETADA)

- ✅ Local Engine Manager (Ollama, LM Studio, Jan)
- ✅ Agent Orchestrator (paralelismo, persistencia, cross-references)
- ✅ Round Controller (4 fases: análisis, crítica, síntesis)
- ✅ Session Manager (ciclo de vida completo)
- ✅ Sistema de prompts (Analista, Crítico, Síntesis)
- ✅ Cruce híbrido Local↔Nube
- ✅ API REST: POST /sessions, GET /sessions/{id}, GET /sessions, DELETE /sessions/{id}
- ✅ Background tasks para ejecución asíncrona

### ✅ FASE 2 - Tribunal y Múltiples Rondas (COMPLETADA)

- ✅ **Tribunal de Magistrados** (3 roles: Evidencias, Riesgos, Alineación)
- ✅ **Protocolo de Consenso Forzado (PCO)** - hasta 3 iteraciones
- ✅ **Convergence Evaluator** - heurísticas de similitud y estabilidad
- ✅ **Múltiples rondas** - hasta 3 rondas con convergencia automática
- ✅ **Contexto acumulado** entre rondas
- ✅ **Veredicto soberano** SIEMPRE ejecutado en LOCAL (PC B)

### ✅ FASE 3 - WebSocket Streaming (COMPLETADA)

- ✅ **WebSocket Manager** - gestión de conexiones múltiples
- ✅ **Streaming de tokens** - texto generado token a token en tiempo real
- ✅ **Eventos de ciclo de vida** - session_start, phase_start, agent_complete, etc.
- ✅ **Eventos del Tribunal** - tribunal_started, tribunal_objection, tribunal_verdict
- ✅ **Heartbeat/ping** - mantenimiento de conexión
- ✅ **Broadcast por sesión** - múltiples clientes pueden observar misma sesión

### ✅ FASE 4 - Frontend React (COMPLETADA)

- ✅ **React 18 + Vite 5** - Build tooling moderno
- ✅ **Tailwind CSS 3** - Styling con tema oscuro personalizado
- ✅ **Zustand** - Estado global sin boilerplate
- ✅ **React Router 6** - Navegación SPA
- ✅ **Componente ChatInput** - Formulario de nueva consulta
- ✅ **Componente SessionView** - Vista de debate en progreso con streaming
- ✅ **Componente AgentCard** - Cards de agentes con texto en tiempo real
- ✅ **Componente TribunalPanel** - Panel del Tribunal de Magistrados
- ✅ **Componente SessionList** - Historial de sesiones
- ✅ **Hooks useWebSocket/useSession** - Integración con API y WebSocket

### ✅ FASE 5 - Hardening y Reputación EMA (COMPLETADA)

- ✅ **Sistema de Reputación EMA** - Exponential Moving Average (α=0.3)
  - TSA: Tasa de Supervivencia de Argumentos
  - IID: Índice de Independencia Dialéctica
  - PVT: Precisión en Validación Técnica
- ✅ **Elección dinámica de agentes** - Selección por reputation_score
- ✅ **Elevación automática a Supabase** - Memoria-oscar para veredictos notables
- ✅ **Debates Iterativos** - Sistema de múltiples iteraciones con contexto persistente
- ✅ **Liberación Automática de RAM** - Unload de modelos entre turnos para evitar OOM
- ✅ **Rate Limiting** - 60 req/min, burst de 10
- ✅ **Security Headers** - CSP, HSTS, X-Frame-Options
- ✅ **Logging estructurado** - Todas las requests HTTP
- ✅ **Tests end-to-end** - Scripts de test completos

### ✅ FASE 6 - Debates Iterativos Multi-Agente (COMPLETADA)

- ✅ **Sistema de Iteraciones Avanzado** - 3+ iteraciones con contexto persistente
- ✅ **Múltiples Roles Dinámicos** - ANALYST, CRITIC, VALIDATOR, CONSENSUS
- ✅ **Cruzamientos Críticos** - Agentes se responden entre sí para profundizar argumentos
- ✅ **Liberación Automática de RAM** - `unload_model()` antes de cada turno
- ✅ **Sistema de Consenso** - Búsqueda de acuerdos con soluciones propuestas
- ✅ **API Endpoint** - `/api/v1/debate/create/iterative` para debates iterativos
- ✅ **Maratón de 10 Debates** - Script `run_10_debates.py` para ejecución automática

**Características del Sistema Iterativo:**
- Contexto completo entre iteraciones (resúmenes acumulativos)
- Roles cambian dinámicamente en cada fase
- Validación de argumentos por agente VALIDATOR
- Búsqueda de consenso final con propuestas de solución
- Streaming en tiempo real de tokens generados
- Guardado automático de transcripcias y reporte maestro

**Uso del script de 10 debates:**
```bash
# Ejecutar maratón de 10 debates automáticamente
python run_10_debates.py

# Resultados en:
# - data/debates/MASTER_REPORT_10_DEBATES_*.md
# - data/debates/debate_debate_*.md (individuales)
```

---

## 🔧 Servicios Verificados en /health

- ✅ **Base de datos SQLite** - Persistencia local
- ✅ **Ollama** - Modelos open-source (PC B)
- ✅ **LM Studio** - Modelos GGUF (PC B)
- ✅ **Jan.ai** - Modelos experimentales (PC B)
- ✅ **OpenRouter** - APIs comerciales
- ✅ **Web Agent** - Playwright para IAs gratuitas

---

## 🏛️ Tribunal de Magistrados

1. **Magistrado de Evidencias** - Validación técnica rigurosa
2. **Magistrado de Riesgos** - Abogado del Diablo (seguridad)
3. **Magistrado de Alineación** - Product Owner pragmático

**Protocolo de Consenso Forzado (PCO)**:
- Propuesta → Veto → Corrección (hasta 3 iteraciones)
- Resolución por méritos si persiste disenso

---

## 📚 Documentación

- [MASTER_PLAN.md](docs/MASTER_PLAN.md) - Arquitectura completa
- [API_DOCS.md](docs/API_DOCS.md) - Endpoints (Fase 3+)

---

**Autor**: Óscar Fernandez  
**Versión**: 2.1.0  
**Estado**: Fase 6 ✅ Completada - Sistema de Debates Iterativos Operativo
