# 📜 Changelog - SynapseCode

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.8.0] - 2026-05-17

### 🚀 Añadido

#### Búsqueda Web en Tiempo Real
- **DuckDuckGo Search** (`ddgs`): Reemplaza Wikipedia/HTTP por búsquedas reales sin API key
- **Trafilatura**: Extracción de contenido completo de artículos (no solo snippets)
- **Contexto web para agentes**: Los debates reciben información actualizada del tema
- **Tribunal con contexto web**: Verificación factual con datos reales

#### Reportes Profesionales HTML/PDF
- **HTML interactivo**: Tema oscuro, gráficos Chart.js, responsive
- **PDF imprimible**: Tema claro, gráficos SVG inline, optimizado para impresión
- **Generación automática**: Se generan al completar cada debate
- **Métricas incluidas**: Tokens, latencia, calidad, consenso, veredicto

#### Sistema de Fallback para Agentes Locales
- **Fallback a llama3:8b**: Cuando un modelo local falla, usa automáticamente un modelo estable
- **Validación de respuestas vacías**: Detecta 0 tokens como error (antes silencio)
- **Paridad cloud/local**: Ahora ambos tipos de agente tienen fallback

#### Recuperación Automática de Errores CUDA
- **Detección de errores GPU**: CUDA OOM, shared object initialization failed, runner terminated
- **Recovery automático**: Limpia memoria GPU y reintenta la generación
- **Retry en warm_model**: 2 intentos con delay para HTTP 500 transitorios
- **HTTP 500 en streaming**: Detecta y reporta errores durante generación (antes silenciosos)

### 🔧 Mejoras Técnicas

- **llama3.2:latest → llama3:8b**: Corregido en todos los archivos de configuración
- **max_tokens aumentado**: 500 → 1000-1200 para respuestas más ricas
- **Safety policy**: `.safety-policy.yml` para CI/CD con vulnerabilidades ignoradas justificadas
- **Ruff linting**: 15 errores corregidos (F541, W291, W293, F841, F401, I001, F821)
- **Ruff formatting**: 4 archivos formateados

### 🐛 Fixes

- **Respuestas vacías silent fail**: `_run_local_agent` ahora lanza RuntimeError si tokens_out == 0
- **HTTP 500 no detectado**: Streaming generate ahora valida status_code antes de leer líneas
- **Coroutine no awaited**: `_is_cuda_error` cambiado de async a sync
- **Variable `query` indefinida**: Corregido a `query_ddg` en web_search_service
- **Imports desordenados**: Reorganizados en report_generator y sequential_debate_controller
- **Variables no usadas**: Eliminadas (provider, tokens_in, turn_num, web_context, AsyncSession)

---

## [2.7.0] - 2026-05-16

### 🚀 Añadido

#### SynapseCode Control Center v2.7
- **Panel Web Completo**: 6 pestañas (Command, Launcher, Metrics, Tribunal, Models, History)
- **Zero Dependencies**: Vanilla JS puro, sin build, sin node_modules, sin CDNs
- **Estado en Tiempo Real**: Polling automático configurable (2-30s)
- **Conexión Master ↔ Worker**:
  - Detección automática de IP del Worker vía `resolve_worker_ip()`
  - Panel de estado con modo "CONECTADO (Master+Worker)" o "LOCAL (todo en Master)"
  - Heartbeat monitoring con fallback a comprobación de servicios
- **Monitor de Servicios Worker**:
  - Ollama, LM Studio, Jan con estado (RUNNING/STOPPED)
  - Detección de servicios en `127.0.0.1` como fallback para servicios que no exponen en red
  - Botones de lanzamiento directo (`POST /worker/services/launch`)
- **Panel de Bases de Datos** (Tab History):
  - Estado de SQLite (local) y Supabase (cloud)
  - Sincronización: pendientes, reintentos, vencidos, en memoria
  - Botones: Forzar Sync, Sync Pendientes, Ver Cloud
- **Diseño Neural Terminal**: Dark mode, grid de circuito, animaciones CSS
- **WebSocket**: Conexión a `/ws/sessions/{id}` para streaming de debates

#### Logging Rotatorio
- **4 archivos por tipo**: `synapse.log`, `synapse_error.log`, `synapse_engine.log`, `synapse_api.log`
- **Rotación automática**: 10MB por archivo, 5 backups
- **Filtros por módulo**: Engine y API separados automáticamente
- **Configuración en `.env`**: `LOG_LEVEL`, `LOG_DIR`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`, `LOG_TO_FILE`

### 🔧 Mejoras Técnicas

- **CORS**: Añadido `localhost:8080` para desarrollo frontend
- **Jan URL**: Corregido a `http://localhost:1337/v1` (incluyendo en `worker_jan_url`)
- **Health Endpoint**: Ahora verifica servicios del Worker si no hay heartbeat TCP
- **WebSocket URL**: Corregido a `/ws/sessions/{id}`
- **Supabase**: Configurado y conectado (`jdbzjapshomatwyasmig.supabase.co`)
- **Demo Mode eliminado**: App 100% live con datos reales del backend

### 📋 Tests

- 5 nuevos tests para logging config (imports, file creation, settings, filters)
- Total: **162 tests** pasando

---

## [2.6.0] - 2026-05-16

### 🚀 Añadido

#### Timeout Configurable por Modelo
- **`MODEL_TIMEOUTS` en `.env`**: JSON con patrones de modelo → timeout en segundos
- **Timeout automático**: `asyncio.wait_for()` envuelve cada llamada a agente
- **Patrones por substring**: `"70b": 300` aplica a cualquier modelo con "70b" en el nombre
- **Defaults por engine**: Ollama (600s), OpenRouter (90s), Groq (30s), Gemini (30s)
- **6 nuevos tests**: Coverage completo de `get_model_timeout()`

### 🔧 Mejoras Técnicas

- **`get_model_timeout()`** en Settings: Busca patrones ordenados por longitud (más largo primero)
- **`_run_local_agent()`**: Envuelto con `asyncio.wait_for(timeout)`
- **`_run_cloud_agent()`**: Envuelto con `asyncio.wait_for(timeout)`
- **Error handling**: `TimeoutError` con mensaje descriptivo y sugerencia

---

## [2.5.0] - 2026-05-16

### 🚀 Añadido

#### Pausar/Reanudar Debates
- **`POST /api/v1/debates/{id}/pause`**: Pausa un debate en ejecución
- **`POST /api/v1/debates/{id}/resume`**: Reanuda un debate pausado desde donde se quedó
- **Motivo de pausa**: Campo `reason` opcional para documentar por qué se pausó
- **Persistencia en DB**: Estado `paused`, `paused_at`, `pause_reason` guardados en SQLite
- **Migración automática**: `paused_at` y `pause_reason` añadidos a `sequential_debates`
- **Flujo completo**: crear → pausar → reanudar → continuar → exportar

#### Continuación de Debates
- **`POST /api/v1/debates/{id}/continue`**: Añade rondas a debates completados
- **Reutiliza contexto**: Acumula turnos previos para coherencia
- **Prompt de continuación personalizable**

### 🔧 Mejoras Técnicas

- **pytest-asyncio**: Actualizado a `>=0.24.0` para compatibilidad con pytest 9.x
- **CI/CD**: Eliminado `|| true` del workflow, ahora los tests deben pasar obligatoriamente
- **162 tests**: Batería completa cubriendo 21 niveles

---

## [2.4.0] - 2026-05-16

### 🚀 Añadido

- **Tribunal de Magistrados**: 3 roles especializados (Defensor, Fiscal, Árbitro)
- **Protocolo de Consenso Forzado**: Con umbral configurable
- **Fallback Chains**: Si un modelo falla, usa el siguiente automáticamente
- **Reducción al Absurdo**: Eliminación de sesgos de complacencia
- **Sistema de Reputación EMA**: TSA, IID, PVT por modelo y rol
- **Caché Semántica**: Respuestas cacheadas por similitud de embeddings
- **Data Warehouse**: Agregaciones automáticas para análisis histórico
- **Prometheus Metrics**: Observabilidad con `/metrics` endpoint
- **Web Agent**: 10 sitios de IA vía Playwright con stealth anti-detección
- **Debates Iterativos**: Multi-agente con cruzamientos críticos
- **Memoria Híbrida v2**: SQLite local + Supabase sync con queue persistente
- **Auto-Recuperación**: WorkerServiceManager lanza servicios caídos
- **Exportación**: JSON, Markdown, PDF de cualquier debate

---

*SynapseCode v2.7 · OscarFeMa · Mayo 2026*
