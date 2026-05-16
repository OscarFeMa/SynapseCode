# Data Warehouse Analytics Queries

Guía de queries SQL para análisis histórico de debates en SynapseCode.

## Tablas del Warehouse

- **debates_aggregate**: Agregación principal por debate (unifica Session y SequentialDebate)
- **topics_trending**: Agregación diaria de temas más debatidos
- **consensus_patterns**: Patrones de consenso por tema y configuración
- **model_performance**: Performance de modelos por rol
- **daily_metrics_snapshot**: Snapshot diario de métricas globales

---

## Trending Topics

### Top 10 temas más debatidos últimos 7 días
```sql
SELECT 
    topic_text,
    SUM(debate_count) as total_debates,
    AVG(avg_consensus_level) as avg_consensus,
    AVG(avg_duration_seconds) as avg_duration,
    SUM(total_turns) as total_turns
FROM topics_trending
WHERE date >= date('now', '-7 days')
GROUP BY topic_text
ORDER BY total_debates DESC
LIMIT 10;
```

### Temas más debatidos por modo
```sql
SELECT 
    t.topic_text,
    d.mode,
    COUNT(*) as debate_count,
    AVG(d.duration_seconds) as avg_duration
FROM debates_aggregate d
JOIN topics_trending t ON d.topic_hash = t.topic_hash
WHERE d.completed_at >= date('now', '-30 days')
GROUP BY t.topic_text, d.mode
ORDER BY debate_count DESC;
```

### Evolución de un tema específico en el tiempo
```sql
SELECT 
    date,
    debate_count,
    avg_consensus_level,
    avg_duration_seconds
FROM topics_trending
WHERE topic_hash = (SELECT topic_hash FROM topics_trending WHERE topic_text LIKE '%IA%' LIMIT 1)
ORDER BY date DESC
LIMIT 30;
```

---

## Consensus Patterns

### Patrones de consenso por modo
```sql
SELECT 
    mode,
    consensus_level,
    debate_count,
    avg_rounds_to_convergence,
    avg_tokens_per_debate,
    success_rate
FROM consensus_patterns
WHERE debate_count >= 3
ORDER BY success_rate DESC;
```

### Consenso por tema específico
```sql
SELECT 
    topic_text,
    mode,
    consensus_level,
    debate_count,
    avg_rounds_to_convergence
FROM consensus_patterns cp
JOIN topics_trending tt ON cp.topic_hash = tt.topic_hash
WHERE tt.topic_text LIKE '%automatización%'
ORDER BY avg_rounds_to_convergence ASC;
```

### Tasa de éxito por configuración
```sql
SELECT 
    mode,
    COUNT(*) as total_debates,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    CAST(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as success_rate
FROM debates_aggregate
WHERE completed_at >= date('now', '-30 days')
GROUP BY mode;
```

---

## Model Performance

### Leaderboard de modelos por rol
```sql
SELECT 
    model_name,
    provider,
    agent_role,
    total_turns,
    avg_latency_ms,
    efficiency_score_avg,
    tsa_score_avg,
    iid_score_avg,
    pvt_score_avg,
    success_rate
FROM model_performance
WHERE total_turns >= 10
ORDER BY efficiency_score_avg DESC;
```

### Modelos más rápidos
```sql
SELECT 
    model_name,
    engine,
    agent_role,
    avg_latency_ms,
    total_turns
FROM model_performance
WHERE total_turns >= 5
ORDER BY avg_latency_ms ASC
LIMIT 10;
```

### Modelos con mejor tasa de argumentos supervivientes (TSA)
```sql
SELECT 
    model_name,
    agent_role,
    tsa_score_avg,
    total_turns
FROM model_performance
WHERE total_turns >= 5
ORDER BY tsa_score_avg DESC;
```

### Comparación de modelos por proveedor
```sql
SELECT 
    provider,
    COUNT(DISTINCT model_name) as unique_models,
    SUM(total_turns) as total_turns,
    AVG(avg_latency_ms) as avg_latency,
    AVG(efficiency_score_avg) as avg_efficiency
FROM model_performance
GROUP BY provider
ORDER BY total_turns DESC;
```

---

## Evolución Temporal

### Métricas globales últimos 30 días
```sql
SELECT 
    date,
    total_debates_completed,
    total_debates_failed,
    total_turns_executed,
    total_tokens_generated,
    total_cost_usd,
    avg_debate_duration_seconds,
    unique_topics_count,
    active_models_count
FROM daily_metrics_snapshot
WHERE date >= date('now', '-30 days')
ORDER BY date DESC;
```

### Tendencia de debates completados por semana
```sql
SELECT 
    strftime('%Y-%W', date) as week,
    SUM(total_debates_completed) as completed,
    SUM(total_debates_failed) as failed,
    SUM(total_tokens_generated) as tokens
FROM daily_metrics_snapshot
WHERE date >= date('now', '-90 days')
GROUP BY week
ORDER BY week DESC;
```

### Distribución de modos en el tiempo
```sql
SELECT 
    strftime('%Y-%m', completed_at) as month,
    mode,
    COUNT(*) as debate_count,
    AVG(duration_seconds) as avg_duration
FROM debates_aggregate
WHERE completed_at >= date('now', '-180 days')
GROUP BY month, mode
ORDER BY month DESC, debate_count DESC;
```

---

## Análisis de Costos

### Costo total por modo
```sql
SELECT 
    mode,
    COUNT(*) as debate_count,
    SUM(estimated_cost_usd) as total_cost,
    AVG(estimated_cost_usd) as avg_cost_per_debate,
    SUM(total_tokens_out) as total_tokens
FROM debates_aggregate
WHERE completed_at >= date('now', '-30 days')
GROUP BY mode
ORDER BY total_cost DESC;
```

### Costo por modelo
```sql
SELECT 
    model_name,
    provider,
    COUNT(*) as debates,
    AVG(estimated_cost_usd) as avg_cost,
    AVG(total_tokens_out) as avg_tokens
FROM debates_aggregate d
JOIN sequential_debate_turns t ON d.id = t.debate_id
WHERE d.completed_at >= date('now', '-30 days')
GROUP BY model_name, provider
ORDER BY avg_cost DESC;
```

### Eficiencia de costo (tokens por dólar)
```sql
SELECT 
    mode,
    SUM(total_tokens_out) as total_tokens,
    SUM(estimated_cost_usd) as total_cost,
    CASE 
        WHEN SUM(estimated_cost_usd) > 0 
        THEN SUM(total_tokens_out) / SUM(estimated_cost_usd) 
        ELSE 0 
    END as tokens_per_dollar
FROM debates_aggregate
WHERE completed_at >= date('now', '-30 days') AND estimated_cost_usd > 0
GROUP BY mode
ORDER BY tokens_per_dollar DESC;
```

---

## Análisis de Reductio Absurdum

### Debates con más pruebas de absurdo
```sql
SELECT 
    d.id,
    d.topic_text,
    d.mode,
    COUNT(rap.id) as absurdum_proofs_count,
    AVG(rap.confidence_score) as avg_confidence
FROM debates_aggregate d
LEFT JOIN reductio_absurdum_proofs rap ON d.id = rap.debate_id
WHERE d.has_reductio_proofs = 1
GROUP BY d.id
ORDER BY absurdum_proofs_count DESC
LIMIT 10;
```

### Proposiciones más cuestionadas
```sql
SELECT 
    proposition,
    COUNT(*) as challenge_count,
    AVG(confidence_score) as avg_confidence,
    SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END) as valid_count,
    SUM(CASE WHEN is_valid = 0 THEN 1 ELSE 0 END) as invalid_count
FROM reductio_absurdum_proofs
GROUP BY proposition
ORDER BY challenge_count DESC
LIMIT 10;
```

---

## Queries Avanzadas

### Debates que convergieron más rápido
```sql
SELECT 
    id,
    topic_text,
    mode,
    rounds_executed,
    duration_seconds,
    total_tokens_out
FROM debates_aggregate
WHERE status = 'completed' 
  AND consensus_level = 'CONSENSUS_REACHED'
  AND rounds_executed <= 2
ORDER BY duration_seconds ASC
LIMIT 10;
```

### Modelos usados por debate
```sql
SELECT 
    d.id,
    d.topic_text,
    d.mode,
    d.unique_models_count,
    GROUP_CONCAT(DISTINCT t.model_name) as models_used
FROM debates_aggregate d
JOIN sequential_debate_turns t ON d.id = t.debate_id
WHERE d.completed_at >= date('now', '-7 days')
GROUP BY d.id
ORDER BY d.unique_models_count DESC;
```

### Correlación entre duración y consenso
```sql
SELECT 
    consensus_level,
    AVG(duration_seconds) as avg_duration,
    AVG(rounds_executed) as avg_rounds,
    COUNT(*) as debate_count
FROM debates_aggregate
WHERE status = 'completed' AND consensus_level IS NOT NULL
GROUP BY consensus_level
ORDER BY avg_duration ASC;
```

---

## Scripts de Utilidad

### Backfill del Warehouse
```python
from backend.database.warehouse import warehouse_manager
import asyncio

async def backfill():
    stats = await warehouse_manager.backfill_historical_data()
    print(f"Backfill completado: {stats}")

asyncio.run(backfill())
```

### Procesar debate específico
```python
from backend.database.warehouse import warehouse_manager
import asyncio

async def process_debate(debate_id: str):
    success = await warehouse_manager.process_sequential_debate(debate_id)
    print(f"Procesamiento: {'exitoso' if success else 'fallido'}")

asyncio.run(process_debate("tu-debate-id"))
```

---

## Notas de Performance

- Las tablas del warehouse tienen índices optimizados para queries analíticos
- Para queries con grandes volúmenes de datos, considera agregar `LIMIT` y filtrar por fecha
- Las agregaciones diarias (topics_trending, daily_metrics_snapshot) se actualizan automáticamente
- Para análisis en tiempo real, usa las tablas fuente (sessions, sequential_debates)
- Para análisis históricos, usa las tablas del warehouse para mejor performance

---

## Integración con Supabase

Las tablas del warehouse se sincronizan automáticamente con Supabase usando el queue existente. Para verificar el estado de sincronización:

```sql
SELECT 
    kind,
    status,
    COUNT(*) as queue_size
FROM supabase_sync_queue
WHERE kind LIKE 'warehouse_%'
GROUP BY kind, status;
```
