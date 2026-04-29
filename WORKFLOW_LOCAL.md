# Workflow de Desarrollo Local - SynapseIA

## Ubicación del Proyecto

**Directorio de trabajo:** `D:\proyectos\Synapse`

Este es el repositorio principal unificado. Todos los cambios se hacen aquí primero.

## Directorios Archivados

- `D:\proyectos\ARCHIVOS\Synapse_Worker_ARCHIVE` - Copia antigua del Worker
- `D:\proyectos\ARCHIVOS\Synapse_Clone_ARCHIVE` - Copia antigua del Clone

**Nota:** No modificar estos directorios. Todo el trabajo se hace en `D:\proyectos\Synapse`.

---

## Estrategia de Trabajo

### Fase 1: Desarrollo Local (Sandbox)

1. **Implementar cambios** en `D:\proyectos\Synapse`
2. **Probar localmente** antes de commitear
3. **Verificar funcionalidad** con tests manuales
4. **Documentar cambios** en este archivo

### Fase 2: Commit Local

```bash
cd D:\proyectos\Synapse
git add .
git commit -m "feat: descripción del cambio"
```

### Fase 3: Push a GitHub

```bash
git push origin main
```

### Fase 4: Sincronización con otros repositorios (si aplica)

```bash
# En Synapse_Worker (si existe)
cd C:\Users\usuario\Desktop\Synapse_Worker
git pull origin main

# En Synapse_Clone (si existe)
cd C:\Users\usuario\Desktop\Synapse_Clone
git pull origin main
```

---

## Prompt de Continuación para Trabajo Local

Copia y pega este prompt cuando continúes trabajando en el proyecto:

```
═══════════════════════════════════════════════════════════════════════════════
PROMPT DE CONTINUACIÓN - SYNAPSEIA WORKFLOW LOCAL
═══════════════════════════════════════════════════════════════════════════════

CONTEXTO COMPLETO DEL PROYECTO:

UBICACIÓN:
- Directorio de trabajo: D:\proyectos\Synapse
- Repositorio Git: Conectado a https://github.com/OscarFeMa/SynapseIA.git
- Rama: main (up-to-date con origin/main)
- Último commit: "Synapse Council v2.0 - Release completo"

DIRECTORIOS ARCHIVADOS:
- D:\proyectos\ARCHIVOS\Synapse_Worker_ARCHIVE (NO modificar)
- D:\proyectos\ARCHIVOS\Synapse_Clone_ARCHIVE (NO modificar)

INFRAESTRUCTURA:
- Master: 192.168.1.41:8000 (FastAPI) - Este ordenador
- Worker: 192.168.1.43:11434 (Ollama) - MakederPc
- Modelos disponibles: llama3:8b, mistral:7b, qwen2.5:3b, deepseek-r1:7b, llama3.1:8b, tinyllama

ESTADO DE LOS CAMBIOS LOCALES (NO COMMITEADOS):

Archivos MODIFICADOS:
- backend/api/routes/debate.py
- backend/config.py
- backend/database/models.py
- backend/engine/agent_orchestrator.py
- backend/engine/sequential_debate_controller.py
- backend/main.py

Archivos NUEVOS:
- backend/api/routes/debug.py (endpoint de diagnóstico)
- backend/engine/intervention_taxonomy.py (taxonomía de intervenciones)
- backend/engine/quality_monitor.py (monitor de calidad)
- backend/engine/reputation_manager.py (gestor de reputación EMA)
- backend/memory/hybrid_memory_v2.py (memoria híbrida)
- backend/memory/__init__.py
- SynapseIA_Plan_Mejora_Completo.docx (plan técnico)
- generate_plan_docx.js (script para generar documentos)
- package.json, package-lock.json (dependencias Node)

BUGS CRÍTICOS (YA CORREGIDOS):
✅ Encoding corrupto en tribunal.py - _has_blocking_objection()
✅ Estimación de tokens incorrecta - cambiado de //4 a //3
✅ Modo hardcodeado en _sync_to_supabase - ahora dinámico

COMPONENTES EXISTENTES (FALTA INTEGRACIÓN):
✅ InterventionDetector - intervention_taxonomy.py (creado, no integrado)
✅ QualityMonitor - quality_monitor.py (creado, no integrado)
✅ ReputationManager - reputation_manager.py (creado, no integrado)
✅ HybridMemoryV2 - memory/hybrid_memory_v2.py (creado, no integrado)
✅ TribunalCouncil - tribunal.py (existe, no integrado en sequential)
✅ ConvergenceEvaluator - convergence.py (existe, no integrado en sequential)

OBJETIVO ACTUAL:

Implementar las mejoras del plan de integración en SequentialDebateController:

1. Añadir campos a DebateSession:
   - tribunal_verdict: Optional[Dict[str, Any]] = None
   - consensus_score: float = 0.0
   - convergence_level: str = 'UNKNOWN'
   - structured_report: Optional[Dict[str, Any]] = None

2. Implementar _run_tribunal() en SequentialDebateController:
   - Filtrar turnos completados (mínimo 2)
   - Construir síntesis local
   - Llamar a TribunalCouncil.deliberate()
   - Retornar dict con scores o None si falla

3. Integrar Tribunal en create_debate():
   - Antes de _generate_verdict()
   - Si tribunal_result existe → usarlo
   - Si no → fallback a texto plano

4. Integrar ConvergenceEvaluator:
   - Añadir al __init__
   - Evaluar cada 2 turnos
   - Si should_stop → break del bucle
   - Guardar consensus_score y convergence_level

5. Implementar _generate_structured_report():
   - Usar mistral:7b con temperatura 0.2
   - Generar JSON con campos definidos
   - Limpiar bloques ```json```
   - Fallback a dict básico si falla

6. Integrar QualityMonitor en build_context_prompt():
   - Filtrar turnos con is_usable() == False
   - Marcar como [OMITIDO - baja calidad]

7. Integrar ReputationManager en create_debate():
   - Tras cada turno completado
   - Llamar update_after_turn() con métricas

8. Integrar HybridMemoryV2:
   - En main.py lifespan: await hybrid_memory.start() / stop()
   - En SequentialDebateController: enqueue_sync() en lugar de _sync_to_supabase()

9. Endpoint de informe:
   - GET /api/v1/debates/{session_id}/report
   - Retornar session.structured_report

RESTRICCIONES ABSOLUTAS:
- Trabajar SOLO en D:\proyectos\Synapse
- NO modificar D:\proyectos\ARCHIVOS
- NO modificar Synapse_Worker ni Synapse_Clone directamente
- Probar cada cambio localmente antes de commitear
- Todo async - ninguna llamada bloqueante en el event loop
- Cada mejora captura sus excepciones internamente - nunca propagar al pipeline
- NO añadir dependencias cloud de pago en esta fase

VERIFICACIÓN ANTES DE COMMITEAR:
1. El sistema arranca sin errores: cd D:\proyectos\Synapse\backend && python main.py
2. Health check OK: curl http://localhost:8000/health
3. Test de debate corto: POST /api/v1/debates/sequential con topic simple
4. Verificar logs para errores (tribunal.deliberating, tribunal.completed)
5. Revisar git diff para confirmar cambios
6. Test endpoint debug: curl http://localhost:8000/api/v1/debug/system

COMANDOS ÚTILES:

# Ver cambios locales
cd D:\proyectos\Synapse
git status
git diff
git diff backend/engine/sequential_debate_controller.py

# Probar sistema
cd D:\proyectos\Synapse\backend
python main.py

# Test health check
curl http://localhost:8000/health

# Test debate corto
curl -X POST http://localhost:8000/api/v1/debates/sequential \
  -H "Content-Type: application/json" \
  -d '{"topic": "Test tribunal: 2+2=4", "mode": "local_only"}'

# Test endpoint debug
curl http://localhost:8000/api/v1/debug/system

# Ver logs de tribunal
# Buscar en logs: tribunal.deliberating, tribunal.magistrate_opinion, tribunal.completed

# Commit cuando esté listo
git add .
git commit -m "feat: descripción del cambio"
git push origin main

PLAN DE IMPLEMENTACIÓN (ORDEN SUGERIDO):
1. Añadir campos a DebateSession (5 min)
2. Implementar _run_tribunal() (1-2 h)
3. Integrar Tribunal en create_debate() (30 min)
4. Integrar ConvergenceEvaluator (1 h)
5. Implementar _generate_structured_report() (1.5 h)
6. Integrar QualityMonitor (1 h)
7. Integrar ReputationManager (1 h)
8. Integrar HybridMemoryV2 (1 h)
9. Endpoint /api/v1/debates/{id}/report (30 min)
10. Tests end-to-end (1 h)

TIEMPO TOTAL ESTIMADO: 8-10 horas

═══════════════════════════════════════════════════════════════════════════════
```

---

## Checklist de Implementación

### Bugs Críticos (YA CORREGIDOS)
- [x] Encoding corrupto en tribunal.py
- [x] Estimación de tokens incorrecta
- [x] Modo hardcodeado en _sync_to_supabase

### Mejoras de Alto Impacto (PENDIENTES)
- [ ] Añadir campos a DebateSession
- [ ] Implementar _run_tribunal()
- [ ] Integrar ConvergenceEvaluator
- [ ] Implementar _generate_structured_report()
- [ ] Endpoint /api/v1/debates/{id}/report

### Mejoras de Enriquecimiento (ARCHIVOS EXISTEN, FALTA INTEGRACIÓN)
- [ ] Integrar QualityMonitor en build_context_prompt()
- [ ] Integrar ReputationManager en create_debate()
- [ ] Integrar HybridMemoryV2 en main.py lifespan

---

## Notas de Desarrollo

### Estado de Componentes

| Componente | Archivo | Estado | Acción |
|------------|---------|--------|--------|
| InterventionDetector | intervention_taxonomy.py | ✅ Creado | Integrar en create_debate() |
| QualityMonitor | quality_monitor.py | ✅ Creado | Integrar en build_context_prompt() |
| ReputationManager | reputation_manager.py | ✅ Creado | Integrar en create_debate() |
| HybridMemoryV2 | memory/hybrid_memory_v2.py | ✅ Creado | Integrar en main.py |
| Tribunal | tribunal.py | ✅ Existe | Integrar en sequential_debate_controller |
| ConvergenceEvaluator | convergence.py | ✅ Existe | Integrar en sequential_debate_controller |

### Archivos Modificados (Cambios Locales)

1. **backend/api/routes/debate.py** - Posibles cambios en endpoints
2. **backend/config.py** - Configuración actualizada
3. **backend/database/models.py** - ModelReputation añadido
4. **backend/engine/agent_orchestrator.py** - Tokens corregidos
5. **backend/engine/sequential_debate_controller.py** - Cambios pendientes
6. **backend/main.py** - Cambios pendientes

---

## Próximos Pasos

1. Revisar los cambios locales actuales con `git diff`
2. Decidir si commitear los cambios actuales o descartar
3. Implementar las mejoras pendientes en SequentialDebateController
4. Probar exhaustivamente
5. Commitear y push a GitHub
6. Sincronizar otros repositorios si es necesario

---

**Última actualización:** 26 de abril de 2026
**Versión del documento:** 1.0
