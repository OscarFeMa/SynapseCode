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

**Versión actual:** v3.0.0
**Última actualización:** 2026-05-19  
**Repositorio:** https://github.com/OscarFeMa/SynapseCode  
**Web:** https://synapsecode.org  
**Estado:** Production Ready ✅
