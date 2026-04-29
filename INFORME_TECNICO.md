# Informe Técnico - SynapseIA v2.0

## Estado del Proyecto

**Fecha:** 29 de abril de 2026  
**Versión:** 2.0.0  
**Estado:** Producción (Stable)  
**Último commit:** 263b915 - "fix: improve structured report generation with fallback and better JSON parsing"

---

## Resumen Ejecutivo

SynapseIA v2.0 es una plataforma de razonamiento colectivo híbrido completamente funcional. El sistema implementa todas las mejoras planificadas del documento `SynapseIA_Plan_Mejora_Completo.docx`, incluyendo:

- ✅ Tribunal de Magistrados integrado en pipeline secuencial
- ✅ Evaluador de Convergencia con parada anticipada
- ✅ Informe estructurado en JSON
- ✅ Taxonomía de intervenciones (CORAL v5.3)
- ✅ Monitor de calidad de respuestas
- ✅ Sistema de reputación EMA
- ✅ Memoria híbrida (SQLite + Supabase)
- ✅ Endpoint de diagnóstico del sistema

---

## Arquitectura Técnica

### Stack Tecnológico

#### Backend
- **Framework:** FastAPI 0.104+
- **Python:** 3.12
- **Base de datos:** SQLite (local) + Supabase (cloud)
- **ORM:** SQLAlchemy (async)
- **Logging:** Structlog
- **Async:** asyncio

#### Motores de IA
- **Ollama:** Modelos locales (llama3, mistral, phi3, gemma2, qwen, deepseek)
- **LM Studio:** Modelos GGUF locales
- **Jan.ai:** Modelos experimentales
- **OpenRouter:** APIs comerciales (configurable)
- **Web Agent:** Playwright para IAs gratuitas

#### Frontend
- **Framework:** React 18 + Vite 5
- **Styling:** Tailwind CSS 3
- **State:** Zustand
- **Routing:** React Router 6

---

## Componentes Implementados

### 1. SequentialDebateController

**Archivo:** `backend/engine/sequential_debate_controller.py`  
**Estado:** ✅ Completado  
**Funcionalidades:**
- Debate secuencial multi-modelo
- Carga/descarga dinámica de modelos
- Fallback local si cloud falla
- Integración con Tribunal de Magistrados
- Evaluación de convergencia con early stop
- Generación de informe estructurado
- Monitor de calidad integrado
- Actualización de reputación EMA

**Campos de DebateSession:**
```python
@dataclass
class DebateSession:
    tribunal_verdict: Optional[Dict[str, Any]] = None
    consensus_score: float = 0.0
    convergence_level: str = 'UNKNOWN'
    structured_report: Optional[Dict[str, Any]] = None
```

### 2. Tribunal de Magistrados

**Archivo:** `backend/engine/tribunal.py`  
**Estado:** ✅ Completado  
**Funcionalidades:**
- 3 magistrados especializados (Evidencias, Riesgos, Alineación)
- Protocolo de Consenso Forzado (PCO) - hasta 3 iteraciones
- Ejecución siempre en LOCAL (soberanía neuronal)
- Veredicto soberano final

**Configuración de Magistrados:**
```python
MAGISTRATES = {
    "evidence": AgentConfig(model="llama3.2:latest", temperature=0.2),
    "risk": AgentConfig(model="local-model", temperature=0.3),
    "alignment": AgentConfig(model="llama3.2:latest", temperature=0.4)
}
```

### 3. ConvergenceEvaluator

**Archivo:** `backend/engine/convergence.py`  
**Estado:** ✅ Completado  
**Funcionalidades:**
- Evaluación de similitud entre respuestas
- Detección de estabilidad de argumentos
- Parada anticipada (early stop) si converge
- Cálculo de consensus_score (0-1)

**Integración en SequentialDebateController:**
```python
if idx % 2 == 0 and idx >= 2:
    convergence_result = self.convergence_evaluator.evaluate(...)
    if convergence_result.should_stop:
        session.convergence_level = convergence_result.consensus_level
        session.consensus_score = convergence_result.similarity_score
        break
```

### 4. InterventionTaxonomy

**Archivo:** `backend/engine/intervention_taxonomy.py`  
**Estado:** ✅ Completado  
**Funcionalidades:**
- Taxonomía de 10 tipos de intervenciones (CORAL v5.3)
- Detector heurístico basado en palabras clave
- Clasificación por rol y contenido

**Tipos de intervenciones:**
- APERTURA, ARGUMENTO, CONTRAARGUMENTO, REFUTACION
- PREGUNTA, CONSENSO, SINTESIS, CRITICA
- VALIDACION, DESCONOCIDO

### 5. QualityMonitor

**Archivo:** `backend/engine/quality_monitor.py`  
**Estado:** ✅ Completado  
**Funcionalidades:**
- Evaluación de calidad de respuestas
- Filtrado de respuestas cortas (< 80 caracteres)
- Detección de respuestas truncadas
- Validación de formato esperado por rol

**Integración en SequentialDebateController:**
```python
q_score, _ = evaluate_response(turn.response_received, agent_config.role.value)
turn.quality_score = q_score
```

### 6. ReputationManager

**Archivo:** `backend/engine/reputation_manager.py`  
**Estado:** ✅ Completado  
**Funcionalidades:**
- Sistema de reputación EMA (Exponential Moving Average)
- Métricas: TSA, IID, PVT, Efficiency
- Actualización asíncrona (background)
- Alfa = 0.3 (últimos ~3 debates pesan 65%)

**Integración en SequentialDebateController:**
```python
asyncio.create_task(reputation_manager.update_after_turn(
    model=agent_config.model,
    provider=agent_config.provider,
    role=agent_config.role.value,
    tokens_out=turn.tokens_out,
    latency_ms=turn.latency_ms,
    success=True,
    intervention_type=intervention_type
))
```

### 7. HybridMemoryV2

**Archivo:** `backend/memory/hybrid_memory_v2.py`  
**Estado:** ✅ Completado  
**Funcionalidades:**
- Memoria híbrida SQLite (primario) + Supabase (background)
- Patrón "fire and forget" para Supabase
- Cola async para sincronización
- No bloquea el pipeline si Supabase falla

**Integración en main.py:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    hybrid_mem = get_hybrid_memory_v2()
    await hybrid_mem.start()
    yield
    await hybrid_mem.stop()
```

### 8. Endpoint de Diagnóstico

**Archivo:** `backend/api/routes/debug.py`  
**Estado:** ✅ Completado  
**Endpoints:**
- `GET /api/v1/debug/system` - Diagnóstico completo del sistema
- `GET /api/v1/debug/health-detailed` - Health check detallado
- `GET /api/v1/debug/config` - Configuración actual

---

## Base de Datos

### Tablas SQLite

1. **sequential_debates** - Debates completos
2. **sequential_debate_turns** - Turnos individuales
3. **sessions** - Sesiones del sistema RoundController
4. **agent_calls** - Llamadas a agentes
5. **model_reputation** - Reputación de modelos
6. **consensus_positions** - Posiciones en debates de consenso
7. **consensus_rounds** - Rondas de consenso

### Tablas Supabase

- **sequential_debates** - Sincronización cloud
- **sequential_debate_turns** - Sincronización cloud

**Nota:** Hay un error de schema en Supabase (columna `provider` not-null) que causa fallos en sync de turns. No afecta funcionalidad local.

---

## API Endpoints

### Debate API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/debate/create` | POST | Crear debate secuencial |
| `/api/v1/debate/{id}` | GET | Obtener debate |
| `/api/v1/debate/{id}/report` | GET | Obtener informe estructurado |
| `/api/v1/debates` | GET | Listar debates |
| `/api/v1/debate/cloud/sync/{id}` | POST | Forzar sync a Supabase |

### Debug API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/debug/system` | GET | Diagnóstico completo |
| `/api/v1/debug/health-detailed` | GET | Health detallado |
| `/api/v1/debug/config` | GET | Configuración |

### Health API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Estado del sistema |

---

## Problemas Conocidos

### 1. Supabase Sync Error

**Descripción:** Los turnos no se sincronizan correctamente a Supabase debido a constraint `provider` not-null.

**Error:** `null value in column "provider" of relation "sequential_debate_turns" violates not-null constraint`

**Impacto:** Bajo - Funcionalidad local no afectada

**Solución:** Actualizar schema de Supabase para permitir null en provider o asegurar que siempre se envía valor.

### 2. Structured Report Fallback

**Descripción:** El modelo a veces no genera JSON válido, se usa fallback básico.

**Impacto:** Bajo - Fallback proporciona información básica funcional

**Solución:** Mejorar prompt del modelo o usar modelo más robusto para estructuración.

---

## Métricas de Rendimiento

### Test Reciente (29/04/2026)

**Debate:** "Test tribunal integration"  
**Modo:** local_only  
**Agentes:** 4 (Analista, Crítico, Sintetizador, Refinador)

**Resultados:**
- **Tiempo total:** ~4 segundos
- **Turnos completados:** 4/4
- **Tokens in:** 147
- **Latencia promedio:** ~67ms/turno
- **Estado:** completed
- **Informe estructurado:** ✅ Generado (fallback)

---

## Próximos Pasos Recomendados

### Corto Plazo (1-2 semanas)

1. **Corregir schema Supabase**
   - Actualizar tabla sequential_debate_turns
   - Añadir constraint nullable en provider
   - Probar sync completo

2. **Mejorar Structured Report**
   - Usar modelo más robusto (mistral:7b)
   - Añadir más campos al reporte
   - Implementar retry si falla primera vez

3. **Tests Automatizados**
   - Crear tests unitarios para componentes
   - Tests de integración end-to-end
   - Tests de carga

### Medio Plazo (1 mes)

1. **Frontend Mejorado**
   - Panel de Tribunal en tiempo real
   - Visualización de convergencia
   - Gráficos de reputación de modelos

2. **Más Modelos**
   - Integrar Claude (Anthropic)
   - Integrar GPT-4 (OpenAI)
   - Añadir modelos especializados (código, matemáticas)

3. **Optimización**
   - Caching de respuestas
   - Streaming mejorado
   - Compresión de contexto

### Largo Plazo (3+ meses)

1. **Multi-Worker**
   - Soporte para múltiples Workers
   - Balanceo de carga
   - Failover automático

2. **Aprendizaje Automático**
   - Entrenamiento de modelos de reputación
   - Detección de patrones de debate
   - Recomendación de modelos

3. **Cloud Native**
   - Despliegue en Kubernetes
   - Escalado automático
   - Monitoreo avanzado

---

## Seguridad

### Implementado

- ✅ Rate limiting (60 req/min)
- ✅ Security headers (CSP, HSTS, X-Frame-Options)
- ✅ Validación de inputs
- ✅ Sanitización de prompts
- ✅ Logging estructurado

### Pendiente

- ⏳ Autenticación de usuarios
- ⏳ Autorización por roles
- ⏳ Encriptación de datos sensibles
- ⏳ Auditoría de accesos

---

## Monitoreo

### Logs

- **Formato:** Structlog (JSON en producción, consola en desarrollo)
- **Niveles:** DEBUG, INFO, WARNING, ERROR
- **Ubicación:** Terminal + archivo (configurable)

### Métricas

- **Health check:** `/health`
- **Debug info:** `/api/v1/debug/system`
- **Stats de debates:** Guardados en SQLite

---

## Dependencias

### Python (requirements.txt)

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.19.0
httpx>=0.25.0
structlog>=24.1.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
supabase>=2.3.0
playwright>=1.40.0
```

### Node.js (package.json)

```
{
  "dependencies": {
    "docx": "^8.5.0"
  }
}
```

---

## Comandos Útiles

### Desarrollo

```bash
# Iniciar backend
cd D:\proyectos\Synapse
python -m backend.main

# Iniciar frontend
cd D:\proyectos\Synapse\frontend
npm run dev

# Ejecutar tests
cd D:\proyectos\Synapse\backend
pytest
```

### Producción

```bash
# Health check
curl http://localhost:8000/health

# Crear debate
curl -X POST http://localhost:8000/api/v1/debate/create \
  -H "Content-Type: application/json" \
  -d @debate.json

# Obtener informe
curl http://localhost:8000/api/v1/debate/{id}/report
```

### Git

```bash
# Ver estado
git status

# Commitear cambios
git add .
git commit -m "mensaje"
git push origin main
```

---

## Documentación Relacionada

- **Manual de Usuario:** `MANUAL_USUARIO.md`
- **Workflow Local:** `WORKFLOW_LOCAL.md`
- **Estado Actual:** `ESTADO_ACTUAL_SESION.md`
- **Plan de Mejora:** `SynapseIA_Plan_Mejora_Completo.docx`
- **README:** `README.md`

---

## Contacto

- **Repositorio:** https://github.com/OscarFeMa/SynapseIA
- **Autor:** Óscar Fernández
- **Licencia:** MIT

---

**Versión del documento:** 1.0  
**Última actualización:** 29 de abril de 2026
