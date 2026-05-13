# 📜 Changelog - Synapse Council

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.3.0] - 2026-05-13

### 🚀 Añadido (Added)

#### Health Check Inteligente
- **Groq y Gemini en /health**: Ahora aparecen como servicios con estado online/error
- **Mensajes de ayuda**: Cada servicio offline incluye `suggested_fix` con la solución
- **Nuevos endpoints**: `/health/live` y `/health/ready`

#### Control Center Web (`/admin`)
- **Dashboard** con tarjetas de estado de todos los servicios en tiempo real
- **Debates**: Historial completo, activos, detalle con click, botones de exportación
- **Nuevo Debate**: Formulario completo (tema, modo, engine de prueba)
- **Worker**: Estado en vivo + botón lanzar servicios
- **Reportes**: Exportación por Session ID (JSON, MD, HTML imprimible)
- **Métricas**: Totales, top debates, tokens, tiempos

#### Exportación Limpia
- **JSON**: Solo tema, estado e intervenciones (rol, agente, modelo, texto)
- **Markdown**: Con iconos por rol (📊 analista, ⚡ crítico, 🔗 sintetizador...)
- **HTML/PDF**: Imprimible desde navegador, sin dependencias externas

#### APIs Cloud
- **Groq**: health_check añadido (lista modelos via API), modelos actualizados
- **Gemini**: health_check añadido (lista modelos via API), modelo 2.5-flash funcional
- **OpenRouter**: URL corregida (doble `/v1/` → `/v1`), 29 modelos gratuitos

#### Sistema de Inicio
- **start_synapse.bat**: Un clic para arrancar servidor + dashboard
- **Worker auto-launch**: Solo intenta WinRM si TrustedHosts configurado, timeout 5s máx

### 🔧 Mejoras Técnicas

- **Panel admin web** reescrito completo con 6 pestañas funcionales
- **Health check** ahora incluye Groq, Gemini en paralelo
- **SynapseDashboard.exe** con consola de depuración, socket check con reintentos
- **Debates ultra_crossing** ahora persisten turnos individuales en DB

### 🐛 Corregido (Fixed)

- **Ultra debate**: Turnos vacíos en DB — ahora guarda cada intervención como `SequentialDebateTurn`
- **CSP Swagger UI**: Añadidos CDN jsdelivr y unpkg a script-src y style-src
- **Dashboard EXE**: server_alive() con socket en vez de HTTP health (timeout 3.5s→1ms)
- **Worker header**: Jan ya no afecta estado general (es opcional)
- **Export PDF**: Eliminada dependencia de weasyprint, usa HTML imprimible

---


### 🚀 Añadido (Added)

#### APIs Cloud Gratuitas
- **Groq Cloud** — `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `qwen3-32b`
- **Google Gemini** — `gemini-2.5-flash`, `gemini-2.0-flash` (60 req/min)
- **Asistente de API keys** — `scripts/get_free_apis.py` guía registro en 5 servicios gratuitos
- **OpenRouter** — URL corregida, 29 modelos gratuitos disponibles

#### Web Agent Mejorado
- **10 sitios soportados**: ChatGPT, Claude, Gemini, DeepSeek, Perplexity, Grok, Mistral, Meta AI, HuggingChat, You.com
- **Modo stealth** anti-detección vía `playwright-stealth`
- **Chrome nativo**: usa Chrome del sistema con sesiones guardadas
- **Asistente de setup**: `scripts/setup_web_sessions.py` con menú interactivo

#### Worker Service Manager
- **`WorkerServiceManager`** (`backend/engine/worker_launcher.py`): Detecta servicios caídos en el Worker y los lanza automáticamente
- **Port forwarding**: `netsh` para exponer LM Studio (:1234) a la red
- **Auto-start script**: `scripts/worker_autostart.bat` para inicio automático de Ollama + LM Studio + Jan

#### Integraciones Completas
- **TaskManager**: Sistema de background tasks con retry y configuración por tarea
- **Hybrid Memory V2**: Sync a Supabase vía task_manager con fallback
- **QualityMonitor**: Filtro de respuestas de baja calidad en `build_context_prompt()`
- **ReputationManager**: `submit_reputation_update()` vía task_manager tras cada turno
- **ConvergenceEvaluator**: Evaluación por turno con early stop
- **Tribunal**: Integrado en flujo de debate secuencial e iterativo

### 🔧 Mejoras Técnicas

- **Gestor HTTP centralizado** (`http_client_manager.py`) con pool de conexiones
- **Retry con backoff exponencial** en adapters Groq, Gemini y base
- **Soporte multi-engine cloud**: groq, gemini, deepseek, openrouter en direct_chat
- **OpenRouter lazy init**: Property-based para evitar conexiones innecesarias
- **Rate limiting mejorado**: 120 req/min, burst 60, cleanup cada 300s
- **Middleware de seguridad**: Orden corregido (CORS después de seguridad)
- **Liveness/Readiness endpoints**: `/health/live` y `/health/ready`
- **DB health check real**: `SELECT 1` en cada health check

### 🐛 Corregido (Fixed)

- **OpenRouter URL**: Doble `/v1/` en endpoint corregido
- **Gemini parser**: Streaming multilínea JSON corregido
- **Groq model**: `llama3-8b-8192` descontinuado → `llama-3.1-8b-instant`
- **History list**: Response key `debates` → `sessions` para coincidir con modelo
- **DeepSeek error handling**: Mensajes de error silenciosos → visibles
- **Puerto LM Studio**: Corregido a 1235 donde funciona realmente

### 🧹 Limpieza

- **232 MB liberados**: build/, dist/, node_modules/, .claude/, __pycache__
- **150+ archivos eliminados**: test JSONs, test_venv/, web_interface/, scripts obsoletos
- **API keys redactadas** del historial git (filter-branch)
- **Documentación antigua** movida a docs/old/

---

### 🚀 Añadido (Added)

#### Sistema de Debates Iterativos Multi-Agente
- **Nuevo endpoint API** `/api/v1/debate/create/iterative` para debates iterativos
- **Controlador de debates secuenciales** (`sequential_debate_controller.py`) con sistema de iteraciones avanzado
- **Sistema de 3+ iteraciones** con contexto persistente entre cada ciclo
- **Roles dinámicos**: ANALYST → CRITIC → VALIDATOR → CONSENSUS
- **Cruzamientos críticos**: Agentes responden entre sí para profundizar argumentos
- **Generación de consenso** con soluciones propuestas

#### Gestión de Memoria Optimizada
- **Liberación automática de RAM** mediante `unload_model()` en OllamaClient
- Descarga de modelos antes de cada turno para prevenir errores OOM
- Sistema de tracking de modelos previos para liberación selectiva

#### Script de Maratón de Debates
- **Nuevo script** `run_10_debates.py` para ejecución automática de 10 debates
- **Temas controversiales predefinidos**:
  1. Derechos Legales y Morales de la IA
  2. Renta Básica Universal (UBI)
  3. Impuesto a la Riqueza de Multimillonarios
  4. Voto Obligatorio Universal
  5. Prohibición de IA en Industrias Creativas
  6. Colonización Humana de Marte
  7. Privacidad de Datos vs Beneficios Corporativos
  8. Control de Armas de Fuego
  9. Abolición de la Pena de Muerte
  10. Abolición de Exámenes Estandarizados
- **Generación automática de reporte maestro** con todos los debates
- **Guardado de transcripciones individuales** para cada debate

#### Estructuras de Datos
- `IteracionDebate` - Registro de iteraciones con turnos y consensos
- `CruzamientoCritico` - Interacciones entre agentes
- `DebateSession` extendida con soporte para iteraciones

### 📊 Estadísticas del Maratón (30 Abril 2026)

| Métrica | Valor |
|---------|-------|
| Debates completados | 10/10 |
| Total de turnos | 115 |
| Tiempo total | ~5.3 horas |
| Consensos alcanzados | 10/10 (100%) |
| Iteraciones por debate | 3 |
| Cruzamientos críticos | ~120 |

### 🔧 Mejoras Técnicas

- **Streaming robusto** de tokens desde Ollama API
- **Logging detallado** de generación y descarga de modelos
- **Conexión Master-Worker** corregida (IP: 192.168.1.44)
- **Modelos optimizados**: mistral:7b, llama3:8b, deepseek-r1:7b, gemma:7b

### 🐛 Corregido (Fixed)

- Corrección de IP del worker en `.env` (192.168.1.43 → 192.168.1.44)
- Fix de respuestas vacías mediante corrección en agregación de tokens
- Implementación de liberación automática de modelos para evitar OOM

---

## [2.0.0] - 2026-04-25

### 🚀 Añadido (Added)

#### Arquitectura Híbrida Master-Worker
- **PC A (Master)**: Orquestación, API REST, WebSocket
- **PC B (Worker)**: Ollama, LM Studio, Jan.ai
- **Sincronización** de sesiones y resultados entre nodos

#### Tribunal de Magistrados
- **3 Magistrados especializados**:
  - Magistrado de Evidencias (validación técnica)
  - Magistrado de Riesgos (abogado del diablo)
  - Magistrado de Alineación (pragmático)
- **Protocolo de Consenso Forzado (PCO)** - hasta 3 iteraciones
- **Veredicto soberano** siempre ejecutado en LOCAL

#### Sistema de Reputación EMA
- **Exponential Moving Average** (α=0.3)
- **Métricas**:
  - TSA: Tasa de Supervivencia de Argumentos
  - IID: Índice de Independencia Dialéctica
  - PVT: Precisión en Validación Técnica
- **Selección dinámica** de agentes por reputation_score

#### WebSocket Streaming
- **Streaming en tiempo real** de tokens generados
- **Eventos de ciclo de vida**: session_start, phase_start, agent_complete
- **Eventos del Tribunal**: tribunal_started, tribunal_objection, tribunal_verdict
- **Heartbeat/ping** para mantenimiento de conexión

#### Frontend React
- **React 18 + Vite 5**
- **Tailwind CSS 3** con tema oscuro personalizado
- **Zustand** para estado global
- **Componentes**:
  - ChatInput - Formulario de nueva consulta
  - SessionView - Vista de debate con streaming
  - AgentCard - Cards de agentes en tiempo real
  - TribunalPanel - Panel del Tribunal
  - SessionList - Historial de sesiones

#### Seguridad y Hardening
- **Rate Limiting** - 60 req/min, burst de 10
- **Security Headers** - CSP, HSTS, X-Frame-Options
- **Logging estructurado** con todas las requests HTTP

### 📁 Estructura del Proyecto
- Backend con FastAPI + SQLAlchemy + SQLite
- Sistema de adaptadores para múltiples motores de IA
- Gestor de motores locales con protocolo Wake & Sleep
- Sistema de prompts especializados por rol

---

## [1.0.0] - 2026-04-20

### 🚀 Añadido (Added)

#### Infraestructura Base
- **FastAPI** como framework principal
- **SQLAlchemy** con SQLite async para persistencia
- **Pydantic Settings** para configuración
- **7 tablas** de base de datos diseñadas

#### Motor de Debate Core
- **Local Engine Manager** - Gestión de Ollama, LM Studio, Jan
- **Agent Orchestrator** - Paralelismo y persistencia
- **Round Controller** - 4 fases: análisis, crítica, síntesis
- **Session Manager** - Ciclo de vida completo de sesiones
- **Sistema de prompts** - Especializados por rol (Analista, Crítico, Síntesis)

#### API REST
- `POST /api/v1/sessions` - Crear nueva sesión
- `GET /api/v1/sessions/{id}` - Obtener sesión
- `GET /api/v1/sessions` - Listar sesiones
- `DELETE /api/v1/sessions/{id}` - Eliminar sesión
- `GET /health` - Health check completo

#### Scripts de Test
- `test_health.py` - Verificación de infraestructura
- `test_session.py` - Test de debate real
- `test_websocket.py` - Test de streaming

---

## Notas de Versiones

- **v2.1.0**: Sistema de debates iterativos con liberación automática de RAM y maratón de 10 debates exitoso
- **v2.0.0**: Arquitectura híbrida completa con Tribunal de Magistrados y WebSocket streaming
- **v1.0.0**: Fundación estable con motor de debate core y API REST

---

**Autor**: Óscar Fernandez  
**Repositorio**: https://github.com/OscarFeMa/SynapseCode
