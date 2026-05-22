**[🇪🇸 Español](#español-history) · [🇬🇧 English](#english-history)**

---

# <a name="español-history"></a>🇪🇸 Historial de Desarrollo

# 📜 Historia de Desarrollo - SynapseCode v3.0

## Resumen del Proyecto

SynapseCode es una plataforma de razonamiento colectivo híbrido que orquesta múltiples modelos de IA en debates estructurados por roles, con validación cruzada y consenso multi-agente.

---

## 🗓️ Línea Temporal de Desarrollo

### **Fase 12: Publicación Web y Estabilización (Completada - v3.0)**

#### Mayo 19, 2026: Despliegue en SynapseCode.org y Fixes Críticos
- ✅ **Landing Page Pública**: Nueva web con diseño editorial en `synapsecode.org`.
- ✅ **Despliegue SPA React**: React App desplegada bajo la ruta `/app/` manejando cliente-servidor dinámico con fallback estático (Netlify/GH Pages).
- ✅ **Compartición de Debates (FEAT-6)**: `SharePage.jsx` y exportación estática para compartir debates en la web pública mediante Supabase.
- ✅ **SEO Básico**: `sitemap.xml` y `robots.txt` para la visibilidad de la landing.
- ✅ **Clean Code & Linting (FIX-4)**: Solucionados 43 lints complejos con Ruff Auto-fixer (B, SIM, PERF).
- ✅ **Refactor de Contexto (FEAT-7)**: Extracción del ContextWindowManager a `debate_models.py` para gestión unificada.
- ✅ **Estabilización de Pipelines**: Tests unitarios y de integración de GitHub Actions arreglados.

### **Fase 13: Responsive Design + Consolidación (Completada - v3.0)**

#### Mayo 20, 2026: Diseño Responsive, Cleanup y Unificación
- ✅ **Responsive Landing Page**: Breakpoints 768px y 480px para móvil/tablet
  - Nav colapsado, hero adaptativo, grid en 1 columna
  - Diagrama de arquitectura con fuente monoespaciada (alineación correcta)
- ✅ **Responsive Admin Panel**: Nav horizontal scrollable, tablas compactas, forms apilados
- ✅ **Eliminación GitHub Pages**: Workflow `deploy-web.yml` removido, todo sirve desde backend local
- ✅ **Consolidación Synapse → SynapseCode**: Merge completo de ~80 commits perdidos por force push
- ✅ **Desktop Shortcuts**: `SynapseCode.lnk` (silencioso + abre navegador) y `SynapseCode Logs.lnk` (visible)
- ✅ **Cache Cloudflare**: Resuelto redirect fantasma a `/app` por caché de versión antigua
- ✅ **Botón "Ver App"**: Color blanco explícito `#FFFFFF` sobre fondo petroleum
### **Fase 11: Admin Panel v3.0 - Compact Dashboard + Full Debates View (Completada - v3.0)**

#### Mayo 19, 2026: Rediseño Completo del Panel de Administración
- ✅ **Dashboard Compacto**: 4 paneles en una sola vista — Worker & Servicios, Diagnóstico, Métricas, Logs Recientes
- ✅ **Pestañas reducidas**: De 8 a 3 — Dashboard, Debates, Configuración + Info Proyecto
- ✅ **Ventana completa de debates** (`/admin/all-debates`):
  - Búsqueda por tema en tiempo real
  - Filtro por estado (completados, en vivo, error)
  - Orden por fecha o tokens
  - Paginación (20 por página)
  - Tarjetas expandibles con secuencia de turnos
  - 4 botones de export: JSON, DOCX, PDF, TXT
- ✅ **Nuevo endpoint de exportación TXT**: `GET /api/v1/debates/{id}/export/txt`
- ✅ **Nuevo endpoint de documentos**: `GET /api/v1/docs/{doc_name}` (readme, history)
- ✅ **Pestaña Info Proyecto**: Renderiza README.md y HISTORY.md como HTML formateado
- ✅ **Markdown renderer inline**: Sin dependencias externas, parsing vanilla JS
- ✅ **Fix 404 en debates completados**: Verifica lista activa antes de consultar memoria
- ✅ **Fix tarjeta expandida se cierra**: Polling actualiza solo metadata sin reconstruir DOM
- ✅ **WebSocket optimizado**: `updateDebateListMeta()` en vez de `renderDebateList()` completo
- ✅ **CI/CD fixes**: Import HTTPException en main.py, f-strings sin placeholders eliminados
- ✅ **Seguridad**: CVE-2026-40347 (`python-multipart`) parcheado, safety policy actualizada

### **Fase 10: Unificación Visual Editorial (Completada - v2.9)**

#### Mayo 19, 2026: Admin Panel Rediseño + SPA Routing + Backend Endpoints
- ✅ **Admin Panel `/admin` rediseñado**: De dark theme (`#0f172a`) a diseño editorial light
  - Background `#F5F3EE` (cream paper), Accent `#23403B` (petroleum green)
  - Tipografía `Instrument Serif` (headings) + `Inter` (body) desde Google Fonts
  - Cards blancas con bordes sutiles, badges con colores pastel
  - Botones en verde petróleo, estados con colores suaves
  - Todas las 8 pestañas unificadas: Dashboard, Debates, Nuevo Debate, Worker, Diagnóstico, Logs, Métricas, Configuración
- ✅ **SPA Routing fix**: `serve.cjs` ahora maneja client-side routing con fallback a `index.html`
- ✅ **Backend endpoints nuevos**:
  - `GET /circuit-breakers/status` - Estado de circuit breakers
  - `GET /model-registry/models` - Lista de modelos registrados
  - `POST /api-keys/{service}` - Alias para actualizar API keys
- ✅ **Process management**: `start_backend.bat` para lanzar backend como proceso persistente
- ✅ **API field mapping normalized**: `topic` ↔ `title`/`query`, `session_id` ↔ `id`, status uppercase
- ✅ **Circuit breakers**: Exposed via API y manejados graceful en frontend
- ✅ **React SPA**: 19 componentes rediseñados con tema editorial (Dashboard, Debates, Monitor, etc.)

### **Fase 9: Asignación Inteligente de Modelos (Completada - v2.8)**

#### Mayo 18, 2026: Model Registry + Evaluator + Role Matcher
- ✅ **Model Registry**: Registro central de 25+ modelos con metadata completa (contexto, velocidad, costo, especialidad)
- ✅ **Model Evaluator**: Consulta rankings web en vivo (LMSYS Arena, OpenRouter stats) con cache de 6h y fallback
- ✅ **Role Matcher**: Asignación automática del mejor modelo por rol según especialidad, plataforma y VRAM disponible
- ✅ **Smart Rotation Mode**: Nuevo modo `smart_rotation` para debates con asignación automática óptima
- ✅ **6 nuevos endpoints API**: `/models/registry`, `/models/best-by-category`, `/models/comparison-table`, `/models/role-matching`, `/models/update-rankings`, `/models/smart-config`
- ✅ **Tablas dinámicas por categoría**: finance, coding, analysis, reasoning, creative, multilingual, long_context, fast, free
- ✅ **Filtro VRAM automático**: Modelos que exceden 13.5GB VRAM del Worker se excluyen automáticamente
- ✅ **Modelos OOM bloqueados**: `qwen2.5-coder:14b`, `qwen2.5:14b`, `llama3:70b`, `mixtral:8x7b`
- ✅ **Ruff format aplicado**: 4 archivos formateados, 150 tests pasando
- ✅ **CI/CD verde**: Ruff check + pytest en cada commit

### **Fase 8: Resiliencia, Reportes y Búsqueda Web (Completada - v2.8)**

#### Mayo 17, 2026: Robustez del Sistema + Reportes Profesionales
- ✅ **Búsqueda web real**: DuckDuckGo (`ddgs`) + Trafilatura reemplazan Wikipedia/HTTP
- ✅ **Reportes HTML/PDF**: Generación automática con gráficos y métricas
- ✅ **Fallback local**: Agentes locales fallan → fallback automático a llama3:8b
- ✅ **Recuperación CUDA**: Detecta errores GPU, limpia memoria y reintenta
- ✅ **Validación respuestas vacías**: 0 tokens ahora lanza error (antes silent fail)
- ✅ **HTTP 500 en streaming**: Detectado y reportado correctamente
- ✅ **warm_model retry**: 2 intentos con delay para errores transitorios
- ✅ **llama3.2:latest → llama3:8b**: Corregido en toda la codebase
- ✅ **CI/CD limpio**: 15 errores de linting + 4 archivos de formato corregidos
- ✅ **Safety policy**: `.safety-policy.yml` para vulnerability checks

### **Fase 7: Cloud APIs y Web Agent (Completada - v2.2)**

#### Mayo 2026: APIs Cloud Gratuitas + Worker Auto-Management
- ✅ **Groq Cloud**: Integración con Llama 3.1, Llama 3.3, Qwen3
- ✅ **Google Gemini**: Integración con Gemini 2.5 Flash y 2.0 Flash
- ✅ **Web Agent v2**: 10 sitios de IA soportados con stealth anti-detección
- ✅ **Chrome nativo**: Web Agent usa Chrome del sistema con sesiones guardadas
- ✅ **WorkerServiceManager**: Detección y lanzamiento automático de servicios
- ✅ **Port forwarding**: LM Studio accesible desde la red vía netsh
- ✅ **Worker autostart**: Script de inicio automático para Ollama + LM Studio + Jan
- ✅ **Asistente API keys**: Script interactivo para obtener claves gratuitas
- ✅ **TaskManager**: Sistema de background tasks con retry y configuración
- ✅ **Hybrid Memory v2**: Sync a Supabase con fallback
- ✅ **QualityMonitor**: Filtro de respuestas de baja calidad
- ✅ **Fix OpenRouter URL**: Corrección de doble `/v1/`
- ✅ **Fix Gemini parser**: Streaming multilínea JSON
- ✅ **Fix Groq model**: Actualización a `llama-3.1-8b-instant`
- ✅ **Fix History list**: Response key corregida
- ✅ **Limpieza general**: 232 MB liberados, 150+ archivos obsoletos eliminados
- ✅ **Seguridad**: API keys redactadas del historial git

---**

#### Semanas 1-2: Infraestructura
- ✅ Setup de proyecto FastAPI
- ✅ Configuración de base de datos SQLite con SQLAlchemy
- ✅ Implementación de modelos de datos (7 tablas)
- ✅ Configuración de entornos virtualizados
- ✅ Sistema de logging con structlog

**Archivos creados:**
- `backend/main.py` - Servidor FastAPI
- `backend/config.py` - Configuración Pydantic
- `backend/database/models.py` - Modelos SQLAlchemy
- `backend/database/local_db.py` - Conexión SQLite

#### Semanas 3-4: Adaptadores de IA
- ✅ Cliente Ollama para modelos locales
- ✅ Cliente OpenRouter para APIs comerciales
- ✅ Implementación de streaming de tokens
- ✅ Sistema de fallback entre modelos

**Archivos creados:**
- `backend/adapters/ollama.py`
- `backend/adapters/openrouter.py`
- `backend/adapters/lm_studio.py`
- `backend/adapters/jan.py`

---

### **Fase 2: Motor de Debate (Completada)**

#### Semanas 5-6: Debate Secuencial (Tribunal de Magistrados)
- ✅ 4 roles especializados: Analyst, Critic, Synthesizer, Refiner
- ✅ Sistema de rondas secuenciales
- ✅ Persistencia en SQLite y Supabase
- ✅ Transcripciones en formato Markdown

**Características:**
- Protocolo de Consenso Forzado (PCO)
- Sistema de reputación EMA
- Veredicto soberano del Tribunal
- Streaming WebSocket en tiempo real

**Archivos creados:**
- `backend/engine/sequential_debate_controller.py`
- `backend/engine/agent_orchestrator.py`
- `backend/engine/local_engine_manager.py`

#### Semanas 7-8: Debate de Consenso Multi-Agente
- ✅ 4 agentes con validación cruzada
- ✅ Rondas: Proposal → Refutation → Synthesis → Convergence
- ✅ Detección de falacias lógicas
- ✅ Análisis de sesgos
- ✅ Score de consenso calculado semánticamente

**Características técnicas:**
- Async/await para paralelismo
- Retry con backoff exponencial (3 intentos)
- Fallback entre modelos (llama3→mistral→qwen)
- Parsing estructurado de respuestas

**Archivos creados:**
- `backend/engine/consensus_debate_controller.py` (1458 líneas)
- `backend/database/models.py` (modelos de consenso)

**Problemas resueltos:**
- ❌ Import `select` faltante en SQLAlchemy → ✅ Agregado
- ❌ Errores de agentes sin retry → ✅ Sistema de reintentos
- ❌ Fallas de modelo sin fallback → ✅ Multi-modelo fallback
- ❌ Parsing de respuestas inconsistente → ✅ Regex estructurado

---

### **Fase 3: API y WebSocket (Completada)**

#### Semana 9: Endpoints REST
- ✅ API para crear debates secuenciales
- ✅ API para debates de consenso
- ✅ Endpoints de consulta y listado
- ✅ Sistema de health checks

**Archivos creados:**
- `backend/api/routes/debate.py`

#### Semana 10: WebSocket y Frontend
- ✅ WebSocket para streaming de tokens
- ✅ Frontend React + Vite
- ✅ Componentes de UI para debate
- ✅ Visualización de estados

**Archivos creados:**
- `backend/api/websocket.py`
- `frontend/` (aplicación React)

---

### **Fase 4: Sincronización Cloud (Completada)**

#### Semana 11: Supabase Integration
- ✅ Servicio de sincronización Supabase
- ✅ Tablas para debates secuenciales
- ✅ Tablas para debates de consenso
- ✅ Políticas de seguridad RLS

**Archivos creados:**
- `backend/services/supabase_sync.py`
- `supabase_schema.sql`
- `supabase_consensus_schema.sql`

**Problemas resueltos:**
- ❌ Sincronización unidireccional → ✅ Bidireccional con conflict resolution
- ❌ Sin timestamps de sync → ✅ Campos `synced_at`
- ❌ Límites de tamaño en campos TEXT → ✅ Truncado inteligente

---

### **Fase 5: Interfaz de Gestión Web (Completada)**

#### Semana 12: Web Interface Standalone
- ✅ Interfaz HTML/CSS/JS completa
- ✅ Dashboard de gestión de debates
- ✅ Creación de debates con formularios
- ✅ Monitoreo en tiempo real de debates activos
- ✅ Visualización de debates completados
- ✅ Integración con API REST

**Archivos creados:**
- `web_interface/debate_manager.html` (aplicación standalone)

**Características:**
- Diseño moderno dark mode
- Responsive para móvil/desktop
- Toast notifications
- Modales para transcripciones
- Filtros y búsqueda
- Estadísticas en tiempo real

---

## 🔧 Problemas Críticos Resueltos

### 1. Sistema de Reintentos (CRÍTICO)
**Problema:** Agentes fallaban sin retry, mostrando `[Error: ]` en respuestas.

**Solución implementada:**
```python
async def _generate_agent_proposal_with_retry(self, session, agent, max_retries=2):
    fallback_models = ['llama3:8b', 'mistral:7b', 'qwen2.5:3b']
    
    for attempt in range(max_retries + 1):
        try:
            position = await self._generate_agent_proposal_once(session, agent)
            if position.position and not position.position.startswith("["):
                return position
        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial
    
    # Fallback a modelos alternativos
    for fallback_model in fallback_models:
        try:
            position = await self._generate_agent_proposal_once(session, fallback_agent)
            return position
        except:
            continue
```

**Resultado:** 0 errores de agentes en debates posteriores.

### 2. Persistencia de Consenso (CRÍTICO)
**Problema:** Debates quedaban en estado `running` en SQLite sin `consensus_score`.

**Causa:** Falta de import `select` en SQLAlchemy.

**Solución:**
```python
from sqlalchemy import select  # Agregado línea 16
```

### 3. Sincronización Supabase
**Problema:** Tablas de consenso no existían en Supabase.

**Solución:** Crear schema SQL completo con:
- `consensus_debates` (debates principales)
- `consensus_rounds` (rondas individuales)
- `consensus_agent_positions` (posiciones por agente)
- Políticas RLS para acceso anónimo

---

## 📊 Estadísticas del Proyecto

### Líneas de Código
| Componente | Líneas | Archivos |
|------------|--------|----------|
| Backend Python | ~8,500 | 45 |
| Frontend React | ~3,200 | 28 |
| Web Interface | ~1,800 | 1 |
| SQL/Schemas | ~400 | 3 |
| Scripts/Batch | ~800 | 8 |
| **TOTAL** | **~14,700** | **85** |

### Modelos de IA Soportados
| Proveedor | Modelos |
|-----------|---------|
| Meta | llama3:8b, llama3.1:8b |
| Mistral | mistral:7b |
| Alibaba | qwen2.5:3b |
| DeepSeek | deepseek-r1:7b |
| OpenRouter | gpt-4, claude-3, etc. |

### Base de Datos
| Tabla | Registros típicos |
|-------|-------------------|
| sequential_debates | ~50 debates |
| consensus_debates | ~20 debates |
| debate_turns | ~200 turnos |
| consensus_rounds | ~60 rondas |

---

## 🎯 Decisiones de Diseño Clave

### 1. Arquitectura Híbrida Master-Worker
**Decisión:** Separar procesamiento (Worker) de orquestación (Master).

**Justificación:**
- Permite usar PC más potente para IA (Worker)
- PC principal (Master) permanece responsiva
- Escalable a múltiples Workers
- Aislamiento de fallos

### 2. SQLite + Supabase (Dual Storage)
**Decisión:** Local primero, cloud como backup.

**Justificación:**
- Funciona offline
- Sincronización asíncrona no bloquea debates
- Recuperación ante fallos de red
- Costo cero para desarrollo local

### 3. Validación Cruzada en Consenso
**Decisión:** Cada agente valida posiciones de otros.

**Justificación:**
- Detecta falacias lógicas
- Reduce sesgos individuales
- Mayor calidad de consenso
- Score basado en acuerdo mútuo

### 4. Sistema de Reintentos con Fallback
**Decisión:** 3 intentos + cambio de modelo automático.

**Justificación:**
- Ollama a veces falla con modelos grandes
- Modelos pequeños (3B) más confiables
- Backoff exponencial no sobrecarga Worker
- Transparencia para usuario final

---

## 🚀 Deployment y Uso

### Instalación Automatizada
```batch
# Windows - Ejecutar como Administrador
INSTALL_MASTER.bat  # En PC Master
INSTALL_WORKER.bat  # En PC Worker
```

### Uso Básico
```bash
# Iniciar servidor
cd synapse-council
.\start_synapse.bat

# Abrir interfaz web
http://localhost:8000/static/debate_manager.html

# API endpoint
POST /api/v1/debate/consensus/create
```

---

## 👥 Contribuidores y Roles

- **Arquitectura:** Diseño de sistema híbrido
- **Backend:** FastAPI, SQLAlchemy, integraciones IA
- **Frontend:** React, WebSocket, UI/UX
- **DevOps:** Scripts de instalación, empaquetado

---

## 📈 Próximos Pasos (Roadmap v2.1)

1. **Visualización de Redes de Argumentación**
   - Grafo de argumentos con D3.js
   - Detección visual de falacias

2. **Sistema de Reputación Avanzado**
   - EMA por dominio temático
   - Leaderboard de agentes

3. **Exportación a Múltiples Formatos**
   - PDF con formato académico
   - JSON para integraciones
   - Markdown con frontmatter

4. **Optimización de Performance**
   - Caching de respuestas similares
   - Modelos cuantizados (Q4_K_M)
   - Paralelismo aumentado

---

## 📝 Notas de Desarrollo

### Lecciones Aprendidas

1. **Retry es esencial:** Los modelos locales fallan más que los comerciales. Un sistema robusto de reintentos es no negociable.

2. **Parsing estructurado:** Esperar formatos consistentes de LLMs es ingenuo. Regex y validación estricta son necesarios.

3. **Monitoreo en tiempo real:** Los debates largos (15+ min) requieren feedback visual constante para mantener engagement.

4. **Fallback graceful:** Cuando un modelo falla, el usuario no debe notarlo. Transición silenciosa a modelos de respaldo.

---

### **Fase 8: Control Center, Exportación y Estabilización (Completada - v2.3)**

#### Mayo 2026: Interfaz web completa, exportaciones limpias, CI
- ✅ **Control Center web** (`/admin`): Dashboard en tiempo real con 6 pestañas funcionales
  - Monitor de servicios Master/Worker con tarjetas de estado
  - Historial de debates completo con exportación directa
  - Formulario para crear nuevos debates (tema, modo, engine)
  - Métricas y estadísticas del sistema
  - Logs de eventos en vivo
- ✅ **Exportación limpia de resultados**
  - JSON con solo `tema`, `estado`, `intervenciones` (rol, agente, modelo, texto)
  - Markdown con iconos por rol (📊 analista, ⚡ crítico, 🔗 sintetizador...)
  - HTML imprimible (listo para PDF desde navegador, sin weasyprint)
- ✅ **Health check inteligente**
  - Groq y Gemini ahora aparecen como servicios en `/health`
  - Cada servicio offline incluye `suggested_fix` con la solución
  - Nuevos endpoints: `/health/live` y `/health/ready`
- ✅ **Health check methods**: Groq y Gemini tienen `health_check()` que verifica API key y lista modelos
- ✅ **SynapseDashboard.exe**: Consola de depuración, timeout de socket reintentos, Worker header solo muestra esenciales (Jan no bloquea estado)
- ✅ **start_synapse.bat**: Un clic para arrancar servidor + dashboard
- ✅ **CSP Swagger UI**: Permite CDN de jsdelivr y unpkg
- ✅ **Worker auto-launch**: Solo intenta WinRM si TrustedHosts configurado, RDP timeout 10s máx
- ✅ **Ultra debate turns**: Ahora persiste cada intervención como `SequentialDebateTurn` en DB
- ✅ **CI/CD**: GitHub Actions con tests de imports y pytest
- ✅ **Nuevo repositorio**: `https://github.com/OscarFeMa/SynapseCode`

--- 

## 📚 Recursos

- **Documentación:** `/docs/`
- **API Reference:** `http://localhost:8000/docs` (Swagger UI)
- **Scripts de prueba:** `/scripts/`
- **Esquemas SQL:** `supabase_*.sql`

---

# <a name="english-history"></a>🇬🇧 Development History

## 📜 Development History - SynapseCode v3.0

### Project Summary

SynapseCode is a hybrid collective reasoning platform that orchestrates multiple AI models in role-structured debates, with cross-validation and multi-agent consensus.

---

### 🗓️ Development Timeline

### **Phase 12: Web Publication and Stabilization (Completed - v3.0)**

#### May 19, 2026: Deployment on SynapseCode.org and Critical Fixes
- ✅ **Public Landing Page**: New web with editorial design at `synapsecode.org`.
- ✅ **React SPA Deployment**: React App deployed under `/app/` route handling dynamic client-server with static fallback (Netlify/GH Pages).
- ✅ **Debate Sharing (FEAT-6)**: `SharePage.jsx` and static export for sharing debates on the public web via Supabase.
- ✅ **Basic SEO**: `sitemap.xml` and `robots.txt` for landing page visibility.
- ✅ **Clean Code & Linting (FIX-4)**: Solved 43 complex lints with Ruff Auto-fixer (B, SIM, PERF).
- ✅ **Context Refactor (FEAT-7)**: Extracted ContextWindowManager to `debate_models.py` for unified management.
- ✅ **Pipeline Stabilization**: GitHub Actions unit and integration tests fixed.

### **Phase 13: Responsive Design + Consolidation (Completed - v3.0)**

#### May 20, 2026: Responsive Design, Cleanup and Unification
- ✅ **Responsive Landing Page**: Breakpoints 768px and 480px for mobile/tablet
  - Collapsed nav, adaptive hero, 1-column grid
  - Architecture diagram with monospace font (correct alignment)
- ✅ **Responsive Admin Panel**: Horizontal scrollable nav, compact tables, stacked forms
- ✅ **GitHub Pages Removal**: `deploy-web.yml` workflow removed, everything served from local backend
- ✅ **Synapse → SynapseCode Consolidation**: Complete merge of ~80 lost commits due to force push
- ✅ **Desktop Shortcuts**: `SynapseCode.lnk` (silent + opens browser) and `SynapseCode Logs.lnk` (visible)
- ✅ **Cloudflare Cache**: Fixed phantom redirect to `/app` from old version cache
- ✅ **"View App" Button**: Explicit white color `#FFFFFF` on petroleum background

### **Phase 11: Admin Panel v3.0 - Compact Dashboard + Full Debates View (Completed - v3.0)**

#### May 19, 2026: Complete Administration Panel Redesign
- ✅ **Compact Dashboard**: 4 panels in single view — Worker & Services, Diagnostics, Metrics, Recent Logs
- ✅ **Reduced Tabs**: From 8 to 3 — Dashboard, Debates, Configuration + Project Info
- ✅ **Full Debates View** (`/admin/all-debates`):
  - Real-time topic search
  - Status filter (completed, live, error)
  - Sort by date or tokens
  - Pagination (20 per page)
  - Expandable cards with turn sequence
  - 4 export buttons: JSON, DOCX, PDF, TXT
- ✅ **New TXT Export Endpoint**: `GET /api/v1/debates/{id}/export/txt`
- ✅ **New Documents Endpoint**: `GET /api/v1/docs/{doc_name}` (readme, history)
- ✅ **Project Info Tab**: Renders README.md and HISTORY.md as formatted HTML
- ✅ **Inline Markdown Renderer**: Vanilla JS parsing, no external dependencies
- ✅ **404 Fix for Completed Debates**: Checks active list before querying memory
- ✅ **Expandable Card Close Fix**: Polling updates only metadata without DOM reconstruction
- ✅ **WebSocket Optimization**: `updateDebateListMeta()` instead of full `renderDebateList()`
- ✅ **CI/CD Fixes**: HTTPException import in main.py, f-strings without placeholders removed
- ✅ **Security**: CVE-2026-40347 (`python-multipart`) patched, safety policy updated

### **Phase 10: Visual Editorial Unification (Completed - v2.9)**

#### May 19, 2026: Admin Panel Redesign + SPA Routing + Backend Endpoints
- ✅ **Admin Panel `/admin` Redesign**: From dark theme (`#0f172a`) to editorial light design
  - Background `#F5F3EE` (cream paper), Accent `#23403B` (petroleum green)
  - Typography `Instrument Serif` (headings) + `Inter` (body) from Google Fonts
  - White cards with subtle borders, pastel-colored badges
  - Petroleum green buttons, states with soft colors
  - All 8 tabs unified: Dashboard, Debates, New Debate, Worker, Diagnostics, Logs, Metrics, Configuration
- ✅ **SPA Routing Fix**: `serve.cjs` now handles client-side routing with fallback to `index.html`
- ✅ **New Backend Endpoints**:
  - `GET /circuit-breakers/status` - Circuit breaker status
  - `GET /model-registry/models` - Registered models list
  - `POST /api-keys/{service}` - Alias for updating API keys
- ✅ **Process Management**: `start_backend.bat` to launch backend as persistent process
- ✅ **API Field Mapping Normalized**: `topic` ↔ `title`/`query`, `session_id` ↔ `id`, status uppercase
- ✅ **Circuit Breakers**: Exposed via API and handled gracefully in frontend
- ✅ **React SPA**: 19 components redesigned with editorial theme (Dashboard, Debates, Monitor, etc.)

### **Phase 9: Intelligent Model Assignment (Completed - v2.8)**

#### May 18, 2026: Model Registry + Evaluator + Role Matcher
- ✅ **Model Registry**: Central registry of 25+ models with complete metadata (context, speed, cost, specialty)
- ✅ **Model Evaluator**: Live web rankings query (LMSYS Arena, OpenRouter stats) with 6h cache and fallback
- ✅ **Role Matcher**: Automatic best-model-per-role assignment based on specialty, platform and available VRAM
- ✅ **Smart Rotation Mode**: New `smart_rotation` mode for debates with optimal automatic assignment
- ✅ **6 New API Endpoints**: `/models/registry`, `/models/best-by-category`, `/models/comparison-table`, `/models/role-matching`, `/models/update-rankings`, `/models/smart-config`
- ✅ **Dynamic Tables by Category**: finance, coding, analysis, reasoning, creative, multilingual, long_context, fast, free
- ✅ **Automatic VRAM Filter**: Models exceeding 13.5GB Worker VRAM automatically excluded
- ✅ **OOM Models Blocked**: `qwen2.5-coder:14b`, `qwen2.5:14b`, `llama3:70b`, `mixtral:8x7b`
- ✅ **Ruff Format Applied**: 4 files formatted, 150 tests passing
- ✅ **CI/CD Green**: Ruff check + pytest on each commit

### **Phase 8: Resilience, Reports and Web Search (Completed - v2.8)**

#### May 17, 2026: System Robustness + Professional Reports
- ✅ **Real Web Search**: DuckDuckGo (`ddgs`) + Trafilatura replace Wikipedia/HTTP
- ✅ **HTML/PDF Reports**: Automatic generation with graphics and metrics
- ✅ **Local Fallback**: Local agents fail → automatic fallback to llama3:8b
- ✅ **CUDA Recovery**: Detects GPU errors, cleans memory and retries
- ✅ **Empty Response Validation**: 0 tokens now throws error (was silent fail)
- ✅ **HTTP 500 in Streaming**: Detected and reported correctly
- ✅ **warm_model retry**: 2 attempts with delay for transient errors
- ✅ **llama3.2:latest → llama3:8b**: Corrected throughout codebase
- ✅ **CI/CD Clean**: 15 linting errors + 4 format files corrected
- ✅ **Safety Policy**: `.safety-policy.yml` for vulnerability checks

### **Phase 7: Cloud APIs and Web Agent (Completed - v2.2)**

#### May 2026: Free Cloud APIs + Worker Auto-Management
- ✅ **Groq Cloud**: Integration with Llama 3.1, Llama 3.3, Qwen3
- ✅ **Google Gemini**: Integration with Gemini 2.5 Flash and 2.0 Flash
- ✅ **Web Agent v2**: 10 IA sites supported with anti-detection stealth
- ✅ **Native Chrome**: Web Agent uses system Chrome with saved sessions
- ✅ **WorkerServiceManager**: Automatic detection and launch of services
- ✅ **Port Forwarding**: LM Studio accessible via netsh from network
- ✅ **Worker Autostart**: Auto-start script for Ollama + LM Studio + Jan
- ✅ **API Keys Assistant**: Interactive script for obtaining free keys
- ✅ **TaskManager**: Background tasks system with retry and configuration
- ✅ **Hybrid Memory v2**: Sync to Supabase with fallback
- ✅ **QualityMonitor**: Filter for low-quality responses
- ✅ **OpenRouter URL Fix**: Correction of double `/v1/`
- ✅ **Gemini Parser Fix**: Multiline JSON streaming
- ✅ **Groq Model Fix**: Updated to `llama-3.1-8b-instant`
- ✅ **History List Fix**: Response key corrected
- ✅ **General Cleanup**: 232 MB freed, 150+ obsolete files removed
- ✅ **Security**: API keys redacted from git history

---

## 🔧 Critical Problems Solved

### 1. Retry System (CRITICAL)
**Problem:** Agents failed without retry, showing `[Error: ]` in responses.

**Implemented Solution:**
```python
async def _generate_agent_proposal_with_retry(self, session, agent, max_retries=2):
    fallback_models = ['llama3:8b', 'mistral:7b', 'qwen2.5:3b']
    
    for attempt in range(max_retries + 1):
        try:
            position = await self._generate_agent_proposal_once(session, agent)
            if position.position and not position.position.startswith("["):
                return position
        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    # Fallback to alternative models
    for fallback_model in fallback_models:
        try:
            position = await self._generate_agent_proposal_once(session, fallback_agent)
            return position
        except:
            continue
```

**Result:** 0 agent errors in subsequent debates.

### 2. Consensus Persistence (CRITICAL)
**Problem:** Debates remained in `running` state in SQLite without `consensus_score`.

**Cause:** Missing `select` import in SQLAlchemy.

**Solution:**
```python
from sqlalchemy import select  # Added line 16
```

### 3. Supabase Synchronization
**Problem:** Consensus tables didn't exist in Supabase.

**Solution:** Created complete SQL schema with:
- `consensus_debates` (main debates)
- `consensus_rounds` (individual rounds)
- `consensus_agent_positions` (positions by agent)
- RLS policies for anonymous access

---

## 📊 Project Statistics

### Lines of Code
| Component | Lines | Files |
|-----------|-------|-------|
| Backend Python | ~8,500 | 45 |
| Frontend React | ~3,200 | 28 |
| Web Interface | ~1,800 | 1 |
| SQL/Schemas | ~400 | 3 |
| Scripts/Batch | ~800 | 8 |
| **TOTAL** | **~14,700** | **85** |

### Supported AI Models
| Provider | Models |
|----------|--------|
| Meta | llama3:8b, llama3.1:8b |
| Mistral | mistral:7b |
| Alibaba | qwen2.5:3b |
| DeepSeek | deepseek-r1:7b |
| OpenRouter | gpt-4, claude-3, etc. |

### Database
| Table | Typical Records |
|-------|-----------------|
| sequential_debates | ~50 debates |
| consensus_debates | ~20 debates |
| debate_turns | ~200 turns |
| consensus_rounds | ~60 rounds |

---

## 🎯 Key Design Decisions

### 1. Hybrid Master-Worker Architecture
**Decision:** Separate processing (Worker) from orchestration (Master).

**Justification:**
- Enables using more powerful PC for AI (Worker)
- Main PC (Master) remains responsive
- Scalable to multiple Workers
- Fault isolation

### 2. SQLite + Supabase (Dual Storage)
**Decision:** Local first, cloud as backup.

**Justification:**
- Works offline
- Asynchronous sync doesn't block debates
- Recovery from network failures
- Zero cost for local development

### 3. Cross-Validation in Consensus
**Decision:** Each agent validates other agents' positions.

**Justification:**
- Detects logical fallacies
- Reduces individual biases
- Higher consensus quality
- Score based on mutual agreement

### 4. Retry System with Fallback
**Decision:** 3 attempts + automatic model switching.

**Justification:**
- Ollama sometimes fails with large models
- Smaller models (3B) more reliable
- Exponential backoff doesn't overload Worker
- Transparency for end user

---

## 🚀 Deployment and Usage

### Automated Installation
```batch
# Windows - Run as Administrator
INSTALL_MASTER.bat  # On Master PC
INSTALL_WORKER.bat  # On Worker PC
```

### Basic Usage
```bash
# Start server
cd synapse-council
.\start_synapse.bat

# Open web interface
http://localhost:8000/static/debate_manager.html

# API endpoint
POST /api/v1/debate/consensus/create
```

---

## 👥 Contributors and Roles

- **Architecture:** Hybrid system design
- **Backend:** FastAPI, SQLAlchemy, AI integrations
- **Frontend:** React, WebSocket, UI/UX
- **DevOps:** Installation scripts, packaging

---

## 📈 Next Steps (v2.1 Roadmap)

1. **Argumentation Network Visualization**
   - Argument graph with D3.js
   - Visual fallacy detection

2. **Advanced Reputation System**
   - EMA by topic domain
   - Agent leaderboard

3. **Multi-format Export**
   - Academic format PDF
   - JSON for integrations
   - Markdown with frontmatter

4. **Performance Optimization**
   - Similar response caching
   - Quantized models (Q4_K_M)
   - Increased parallelism

---

## 📝 Development Notes

### Lessons Learned

1. **Retry is Essential:** Local models fail more than commercial ones. A robust retry system is non-negotiable.

2. **Structured Parsing:** Expecting consistent LLM formats is naive. Strict regex and validation are necessary.

3. **Real-time Monitoring:** Long debates (15+ min) require constant visual feedback to maintain engagement.

4. **Graceful Fallback:** When a model fails, the user shouldn't notice. Silent transition to backup models.

---

### **Phase 8: Control Center, Exportation and Stabilization (Completed - v2.3)**

#### May 2026: Complete web interface, clean exports, CI
- ✅ **Web Control Center** (`/admin`): Real-time dashboard with 6 functional tabs
  - Master/Worker services monitor with state cards
  - Complete debate history with direct export
  - Form for creating new debates (topic, mode, engine)
  - System metrics and statistics
  - Live event logs
- ✅ **Clean Result Export**
  - JSON with only `tema`, `estado`, `intervenciones` (role, agent, model, text)
  - Markdown with role icons (📊 analyst, ⚡ critic, 🔗 synthesizer...)
  - Printable HTML (ready for PDF from browser, without weasyprint)
- ✅ **Intelligent Health Check**
  - Groq and Gemini now appear as services in `/health`
  - Each offline service includes `suggested_fix` with solution
  - New endpoints: `/health/live` and `/health/ready`
- ✅ **Health Check Methods**: Groq and Gemini have `health_check()` verifying API key and model listing
- ✅ **SynapseDashboard.exe**: Debug console, socket timeout retries, Worker header shows only essentials (Jan doesn't block state)
- ✅ **start_synapse.bat**: One-click to start server + dashboard
- ✅ **CSP Swagger UI**: Allows CDN from jsdelivr and unpkg
- ✅ **Worker Auto-launch**: Only attempts WinRM if TrustedHosts configured, RDP timeout max 10s
- ✅ **Ultra Debate Turns**: Now persists each intervention as `SequentialDebateTurn` in DB
- ✅ **CI/CD**: GitHub Actions with import tests and pytest
- ✅ **New Repository**: `https://github.com/OscarFeMa/SynapseCode`

---

## 📚 Resources

- **Documentation:** `/docs/`
- **API Reference:** `http://localhost:8000/docs` (Swagger UI)
- **Test Scripts:** `/scripts/`
- **SQL Schemas:** `supabase_*.sql`

---

**Current Version:** v3.0.0  
**Last Updated:** May 22, 2026  
**Repository:** https://github.com/OscarFeMa/SynapseCode  
**Web:** https://synapsecode.org  
**Status:** Production Ready ✅
