# Informe de Próximos Pasos - SynapseCode

**Fecha:** 2026-05-16  
**Contexto:** continuación del roadmap de mejoras futuras y revisión del estado real del workspace.  
**Objetivo:** ordenar los siguientes pasos por impacto, dependencias y riesgo técnico.

---

## 1. Estado Actual Consolidado

El backend ya avanzó de forma importante en las áreas de rendimiento, persistencia y observabilidad. En el workspace actual hay trabajo implementado o parcialmente implementado en:

- Caché de reportes y backfill de `structured_report`.
- Persistencia de Reducción al Absurdo en SQLite.
- Exportación JSON estructurada con metadata.
- Métricas Prometheus en `/metrics`.
- Token buffering para WebSocket.
- Pre-carga de modelos Ollama en background.
- Caché determinista y caché semántica de respuestas.
- Cola persistente de sincronización con Supabase.
- Modelos y gestor de Data Warehouse.
- Documentación de queries analytics.

El estado funcional ha mejorado, pero el sistema está entrando en una fase donde las piezas nuevas dependen más de la integridad del esquema SQLite, los tests y el orden de inicialización. La prioridad inmediata ya no es añadir otra feature, sino estabilizar la base para que lo nuevo no quede frágil.

---

## 2. Hallazgo Crítico

La ejecución de tests muestra un fallo actual:

```text
sqlite3.OperationalError: no such column: prompt_response_cache.prompt_embedding
```

La causa probable es que `Base.metadata.create_all()` crea tablas nuevas, pero no actualiza tablas existentes cuando se agregan columnas. El modelo `PromptResponseCache` ya espera columnas nuevas como:

- `prompt_embedding`
- `similarity_threshold`
- `expires_at`

Pero la base local `data/synapse.db` contiene una versión anterior de la tabla `prompt_response_cache`.

**Impacto:** la caché semántica y la caché determinista pueden fallar en entornos existentes aunque funcionen en una base limpia.

**Conclusión:** el próximo paso óptimo es una migración segura de esquema antes de continuar con Data Warehouse, tribunal configurable o UI.

---

## 3. Próximo Paso Inmediato

### Paso 1 - Migraciones SQLite idempotentes

**Prioridad:** P0  
**Objetivo:** asegurar que las tablas existentes evolucionen sin borrar datos.

Acciones recomendadas:

- Crear un módulo de migraciones ligeras en `backend/database/migrations/`.
- Añadir migración para `prompt_response_cache`:
  - `prompt_embedding TEXT NULL`
  - `similarity_threshold FLOAT NOT NULL DEFAULT 0.85`
  - `expires_at DATETIME NULL`
- Añadir validación de índices si faltan.
- Ejecutar migraciones desde `init_db()` después de `create_all()`.
- Añadir test que cree una tabla antigua y verifique que `init_db()` la actualiza.

Resultado esperado:

- `pytest -p no:asyncio backend/tests/test_system.py -q` vuelve a pasar completo.
- La caché funciona sobre bases existentes y bases nuevas.

---

## 4. Orden Óptimo Después de Estabilizar

### Paso 2 - Hardening de Data Warehouse

**Motivo:** ya hay modelos, gestor y documentación, pero antes de usarlo como fuente de verdad conviene comprobarlo con datos reales y tests.

Acciones:

- Añadir tests para `WarehouseManager.process_sequential_debate()`.
- Corregir referencias frágiles si aparecen, especialmente accesos ORM a relaciones.
- Exponer endpoint admin de analytics básico:
  - resumen diario
  - top temas
  - leaderboard de modelos
- Añadir métrica Prometheus de debates agregados.

Valor:

- Convierte las mejoras de persistencia en insights históricos útiles.
- Prepara paneles y comparativas sin depender de lecturas manuales SQL.

### Paso 3 - Health y alerting operativo

**Motivo:** ya existe `/metrics`, cola Supabase y health checks. Falta convertirlos en señales accionables.

Acciones:

- Añadir `/health/sync` o extender `/api/v1/system/metrics`.
- Señalar estados:
  - cola vacía
  - cola con retries
  - cola bloqueada por credenciales Supabase
- Añadir gauges/counters:
  - `synapse_supabase_sync_failures_total`
  - `synapse_supabase_sync_retries_total`
  - `synapse_prompt_cache_hits_total`
  - `synapse_prompt_cache_misses_total`
- Documentar reglas Prometheus/Grafana mínimas.

Valor:

- Permite detectar degradación antes de que el usuario note pérdida de datos o lentitud.

### Paso 4 - Tribunal configurable

**Motivo:** es una mejora de calidad del razonamiento, pero depende de que la base operativa ya sea observable y estable.

Acciones:

- Crear `backend/engine/tribunal_config.py`.
- Permitir configuración por rol:
  - evidence
  - risk
  - alignment
- Añadir fallback chain local/cloud.
- Exponer configuración en API o `.env`.
- Añadir tests de selección y fallback.

Valor:

- Mejora la calidad del veredicto final sin cambiar el flujo completo del debate.

### Paso 5 - Continuación de debates

**Motivo:** ya hay persistencia de reportes, turnos, reductio y warehouse. La continuación necesita apoyarse en esa base.

Acciones:

- Endpoint `POST /api/v1/debates/{id}/continue`.
- Recuperar contexto desde DB si no está en memoria.
- Crear rondas 4+ con prompt contextualizado.
- Invalidar reporte/cache del debate continuado.
- Registrar continuación en export JSON y warehouse.

Valor:

- Convierte debates terminados en conversaciones evolutivas, una mejora directa de UX.

### Paso 6 - Dashboard admin/analytics

**Motivo:** el backend ya tendrá señales suficientes. Antes sería una UI bonita sobre datos incompletos.

Acciones:

- Vista de cola Supabase.
- Vista de métricas Prometheus resumidas.
- Vista de analytics warehouse.
- Vista de caché: hit rate, entries, cleanup.
- Responsive básico del admin actual.

Valor:

- Hace visible el sistema para operar, depurar y tomar decisiones.

---

## 5. Riesgos Técnicos

### Riesgo 1 - Esquema SQLite sin migraciones

Este es el riesgo más inmediato. Cada nueva columna en modelos puede romper instalaciones existentes.

Mitigación:

- Migraciones idempotentes.
- Tests que simulen esquemas antiguos.
- Evitar depender solo de `create_all()`.

### Riesgo 2 - Trabajo parcialmente duplicado en caché

Hay caché determinista integrada en `_run_local_agent()` y caché semántica en `backend/caching/semantic_cache.py`. Conviene unificar responsabilidades para que no haya dos caminos con métricas o invalidación divergentes.

Mitigación:

- Definir `SemanticCacheService` como interfaz principal.
- Mantener fallback determinista dentro del servicio.
- Instrumentar hits/misses en un solo lugar.

### Riesgo 3 - Warehouse implementado antes de estar probado

El warehouse existe, pero necesita tests de integración con datos reales de `SequentialDebate`.

Mitigación:

- Tests por tabla agregada.
- Backfill idempotente.
- Endpoint de inspección para comprobar conteos.

### Riesgo 4 - Demasiados cambios sin corte de estabilización

El diff actual es grande y toca módulos críticos. Seguir añadiendo features sin estabilizar elevaría el coste de depuración.

Mitigación:

- Resolver test rojo.
- Ejecutar suite completa.
- Crear commit de estabilización antes de seguir con nuevas features.

---

## 6. Recomendación Ejecutiva

La secuencia óptima desde este punto es:

1. Migraciones SQLite idempotentes para corregir `prompt_response_cache`.
2. Tests y hardening del Data Warehouse.
3. Health/alerting operativo para sync, cache y warehouse.
4. Tribunal configurable.
5. Continuación de debates.
6. Dashboard admin/analytics responsive.

El criterio es simple: primero asegurar que la base no se rompe en instalaciones existentes, luego convertir los datos persistidos en información útil, y después mejorar la calidad del debate y la experiencia de uso.

---

## 7. Criterio de Salida Para la Próxima Iteración

Antes de avanzar al siguiente bloque funcional, debería cumplirse:

```bash
pytest -p no:asyncio backend/tests/test_system.py -q
```

Resultado esperado:

```text
23 passed
```

Además:

- `init_db()` debe actualizar esquemas antiguos sin borrar datos.
- `/metrics` debe seguir respondiendo.
- `/api/v1/system/metrics` debe mostrar `supabaseSyncQueueSize`.
- La caché debe funcionar tanto con bases nuevas como con `data/synapse.db` existente.

