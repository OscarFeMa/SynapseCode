# 📋 Roadmap — SynapseCode v2.8+

**Fecha:** 17 de mayo de 2026  
**Versión Actual:** 2.8.0  
**CI/CD:** ✅ Pasando (150 tests, Ruff clean, Bandit + Safety)

---

## ✅ Implementado en v2.4 – v2.8

| Feature | Versión | Estado |
|---------|---------|--------|
| Caché semántica | v2.4 | ✅ |
| Data Warehouse | v2.4 | ✅ |
| Prometheus metrics | v2.4 | ✅ |
| Logging rotatorio | v2.7 | ✅ |
| Reducción al absurdo | v2.4 | ✅ |
| Continuación de debates | v2.5 | ✅ |
| Pausa/Reanudación | v2.5 | ✅ |
| Timeouts por modelo | v2.6 | ✅ |
| Fallback chains Tribunal | v2.4 | ✅ |
| Tests automatizados (150) | v2.7 | ✅ |
| CI/CD pipeline | v2.7 | ✅ |
| Búsqueda web DuckDuckGo | v2.8 | ✅ |
| Reportes HTML/PDF | v2.8 | ✅ |
| CUDA auto-recovery | v2.8 | ✅ |
| Fallback local llama3:8b | v2.8 | ✅ |

---

## 🔥 Pendiente — Prioridad Alta

### F-1: Visualización de argumentación (D3.js)
**Impacto:** Alto — diferenciador visual clave  
**Esfuerzo:** 3-5 días

Grafo interactivo de argumentos, contra-argumentos y relaciones entre agentes.

### F-2: Full-text search FTS5 en debates
**Impacto:** Alto — búsqueda instantánea en historial  
**Esfuerzo:** 2-3 días

```sql
CREATE VIRTUAL TABLE debates_fts USING fts5(
    topic, final_verdict, structured_report,
    content='sequential_debates', content_rowid='rowid'
);
```

### F-3: Comparación entre debates
**Impacto:** Medio — análisis de tendencias  
**Esfuerzo:** 3-4 días

Endpoint `GET /api/v1/debates/compare?id1=X&id2=Y` → diff de veredictos, métricas, consenso.

---

## 📋 Pendiente — Prioridad Media

### F-4: Debate paralelo (múltiples agentes simultáneos)
**Impacto:** Medio — reduce tiempo de debate 60%  
**Esfuerzo:** 5-8 días

Actualmente secuencial. Paralelizar agentes independientes con `asyncio.gather()`.

### F-5: Persistencia de AbsurdumProofs en BD
**Impacto:** Medio — auditoría de razonamiento  
**Esfuerzo:** 2-3 días

Tabla `reductio_absurdum_proofs` con: debate_id, agent_model, original_proposition, contradiction_found, robustness_score.

### F-6: GPU metrics en dashboard
**Impacto:** Medio — diagnóstico OOM en tiempo real  
**Esfuerzo:** 2-3 días

Endpoint `GET /api/v1/system/worker/resources` → nvidia-smi parsing, gauge de VRAM en Control Center.

---

## 💡 Pendiente — Prioridad Baja

### F-7: Exportación DOCX
**Impacto:** Bajo — librería ya instalada  
**Esfuerzo:** 1-2 días

`GET /api/v1/debates/{id}/export/docx` → python-docx con portada, tabla de turnos, veredicto.

### F-8: Notificaciones push
**Impacto:** Bajo — UX improvement  
**Esfuerzo:** 2-3 días

Web notifications cuando debate completa o tribunal emite veredicto.

### F-9: Migrar Control Center a React
**Impacto:** Bajo — frontend/ ya existe  
**Esfuerzo:** 5-10 días

Reemplazar vanilla JS en `/admin` por React app en `/frontend`.

---

## 📊 Estimación Total

| Prioridad | Tareas | Esfuerzo |
|-----------|--------|----------|
| Alta | 3 | 8-12 días |
| Media | 3 | 9-14 días |
| Baja | 3 | 8-15 días |
| **Total** | **9** | **25-41 días** |

---

## 🚫 Descartado / No planeado

| Idea | Motivo |
|------|--------|
| Redis cache | SQLite+Supabase suficiente; añade ops overhead |
| PostgreSQL | Supabase sync cubre necesidad cloud |
| weasyprint para PDF | No funciona en Windows; xhtml2pdf funciona |
| Flask en lugar de FastAPI | FastAPI async es superior para este use case |
| Eliminar Electron desktop | Legacy pero funcional; baja prioridad |
