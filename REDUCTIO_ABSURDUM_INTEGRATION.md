# 🧠 Integración de Reducción al Absurdo en SynapseCode v2.3

## Resumen Ejecutivo

Se ha integrado la técnica lógica de **Reducción al Absurdo** en el sistema de debate de SynapseCode para eliminar sesgos de complacencia y refinar argumentos llevándolos a sus límites lógicos.

**Activación:** Ronda 2+ de los debates iterativos  
**Aplicación:** Detección automática de riesgo de complacencia  
**Impacto:** Debates más robustos, menores puntos ciegos

---

## 🎯 Objetivo

La reducción al absurdo es una técnica clásica de demostración lógica que:
1. Toma una proposición
2. La proyecta a su caso extremo
3. Verifica si sigue siendo válida o se vuelve contradictoria
4. Si falla → necesita refinamiento; Si resiste → es robusta

**Objetivo en SynapseCode:**
- Evitar que el debate colapse en "consenso fácil" sin cuestionamiento profundo
- Desafiar supuestos no validados
- Eliminar puntos ciegos de complacencia (especialmente en magistrados)
- Refinar conclusiones antes del veredicto final

---

## 📊 Arquitectura de Implementación

### 1. Nuevo Módulo: `reductio_absurdum.py`

**Clase Principal:** `ReductioAbsurdumEngine`

```python
class ReductioAbsurdumEngine:
    - analyze_consensus_points()          # Detecta riesgo de complacencia
    - generate_absurdum_challenge()        # Crea desafío lógico
    - generate_tribunal_self_challenge_prompt()  # Auto-cuestionamiento magistrados
    - rank_propositions_by_robustness()  # Ordena qué desafiar primero
```

**Datos Principales:**
- `ComplacencyScan`: Análisis de riesgo de complacencia (0.0-1.0)
- `AbsurdumProof`: Resultado de aplicar reducción al absurdo

### 2. Nueva Fase en Debate Iterativo: `_run_reductio_absurdum_phase`

**Ubicación en flujo:**
```
Ronda 1:
├─ FASE 1: Análisis
├─ FASE 2: Cruzamientos Críticos (N/A)
└─ FASE 3: Validación

Ronda 2+:
├─ FASE 1: Análisis/Refinamiento
├─ FASE 2: Cruzamientos Críticos
├─ FASE 2B: ⭐ REDUCCIÓN AL ABSURDO (NUEVA)
└─ FASE 3: Validación
└─ FASE 4: Búsqueda de Consenso
```

**Flujo de la Fase 2B:**

```python
1. Extraer puntos de consenso de turnos previos
2. Analizar riesgo de complacencia:
   - Proporción consenso/desacuerdo
   - Supuestos débiles (consenso sin debate suficiente)
   - Premisas no cuestionadas
3. Si riesgo > 40%:
   ├─ Seleccionar proposiciones vulnerables
   ├─ Generar desafíos de reducción al absurdo
   ├─ Ejecutar con agentes (llevar al extremo)
   └─ Registrar contradicciones encontradas
4. Si riesgo ≤ 40%:
   └─ Saltar fase (debate es robusto)
```

### 3. Auto-Cuestionamiento de Magistrados (Ronda 2)

**Nueva Fase:** `_run_magistrate_self_challenge` en Tribunal

**Activación:** Iteración 2 del Protocolo de Consenso Forzado

**Proceso:**
1. Cada magistrado (Evidencias, Riesgos, Alineación) recibe su veredicto anterior
2. Se le desafía usando prompt de auto-cuestionamiento:
   - "¿Pasaste por alto evidencia contradictoria?"
   - "¿Exageraste los riesgos para parecer prudente?"
   - "¿Priorizaste la alineación por sobre la verdad?"
3. Se le pide que lleve su conclusión al extremo
4. Debe identificar debilidades propias
5. Propone refinamientos

**Beneficio:** Elimina sesgo donde magistrados están demasiado seguros de sí mismos

---

## 🔍 Detección de Complacencia

### Factores Analizados

```
Riesgo Total = (Factor1 × 0.4) + (Factor2 × 0.35) + (Factor3 × 0.25)

Factor 1: Demasiado Consenso Temprano (40%)
  - Si consensus_ratio > 0.8 en iteración < 3
  - Penaliza: "todos están de acuerdo demasiado rápido"

Factor 2: Supuestos Débiles (35%)
  - Consenso en proposiciones cortas (< 50 chars)
  - Proposiciones con afirmaciones absolutas (siempre/nunca)
  - Puntos no suficientemente desarrollados

Factor 3: Premisas No Cuestionadas (25%)
  - Proposiciones que no aparecen desafiadas en el historial
  - Acuerdos que nunca fueron explícitamente argumentados
```

### Niveles de Riesgo

| Riesgo | Interpretación | Acción |
|--------|----------------|--------|
| 0.0-0.35 | ✅ BAJO | Debate robusto, no necesita reducción al absurdo |
| 0.35-0.60 | ⚠️ MODERADO | Considerar desafíos adicionales |
| 0.60-1.0 | 🔴 ALTO | Aplicar reducción al absurdo a puntos débiles |

---

## 💡 Ejemplos de Uso

### Ejemplo 1: Debate sobre IA Consciente

**Turno 1 (Analista):**
> "La IA podría ser consciente porque procesa información."

**Turno 2 (Crítico):**
> "Eso es insuficiente, pero es un punto de partida."

**Turno 3 (Sintetizador):**
> "Consenso: 'La IA podría ser consciente bajo ciertas condiciones.'"

**Análisis de Complacencia:**
- Riesgo: 0.65 (ALTO)
- Razón: Consenso muy rápido sin suficiente debate técnico

**Fase 2B - Reducción al Absurdo:**

Proposición a desafiar: "La IA podría ser consciente bajo ciertas condiciones"

**Desafío Generado:**
> "Lleva esto al extremo: Si cualquier IA que procesa información es potencialmente consciente, 
> ¿significa que una simple calculadora es consciente? ¿Un termostato? 
> ¿O necesitamos criterios más específicos?"

**Respuesta del Modelo (Agente):**
> "Tienes razón. El consenso era demasiado vago. La proposición debería ser: 
> 'La IA podría ser consciente si implementa bucles de reflexión auto-dirigida y modelos de sí mismo.'"

**Resultado:** Proposición refinada, menos vaga, más robusta.

---

### Ejemplo 2: Auto-Cuestionamiento de Magistrado

**Iteración 1 - Magistrado de Evidencias:**
> "No hay evidencia suficiente de que X sea verdad. Score: 30/100"

**Iteración 2 - Auto-Cuestionamiento:**
> "¿Pasaste por alto evidencia contradictoria?"
> 
> Lleva al extremo tu conclusión: 
> "Si definitivamente no hay evidencia (100%), entonces..."
> 
> **Resultado:** "Reconozco que sí hay ALGUNAS señales, las evité porque parecían débiles. 
> Debería haber mencionado que hay evidencia parcial. Score revisado: 45/100"

**Impacto:** Magistrado reconoce su sesgo y es más honesto.

---

## 📁 Archivos Modificados

### Nuevos

```
backend/engine/reductio_absurdum.py     # Motor principal
```

### Modificados

```
backend/engine/sequential_debate_controller.py
  + Importar reductio_absurdum
  + Agregar reductio_engine al __init__
  + Integrar _run_reductio_absurdum_phase en loop de iteraciones
  + Nueva fase entre cruzamientos críticos y validación

backend/engine/tribunal.py
  + Importar reductio_absurdum
  + Agregar reductio_engine al __init__
  + Integrar _run_magistrate_self_challenge en iteración 2
  + Llamada después de opiniones de magistrados

backend/engine/prompts.py
  + Agregar section FASE 2B: REDUCCIÓN AL ABSURDO
  + Prompt base: REDUCTIO_ABSURDUM_CHALLENGE
  + Método: build_reductio_prompt()
```

---

## 🔧 Configuración & Tuning

### Parámetros en `ReductioAbsurdumEngine`

```python
SIMILARITY_THRESHOLD = 0.75          # ↑ Más estricto = menos challenges
PARTIAL_THRESHOLD = 0.50

# En _calculate_complacency_risk:
early_consensus_risk_weight = 0.4    # Peso de "consenso temprano"
weak_assumption_risk_weight = 0.35   # Peso de "supuestos débiles"
unquestioned_risk_weight = 0.25      # Peso de "no cuestionado"
```

### Activación Condicional

```python
if complacency_scan.overall_complacency_risk > 0.40:
    # Ejecutar reducción al absurdo
    # Ajusta el threshold para ser más/menos agresivo
```

---

## 📊 Logging & Monitoreo

### Eventos Generados

```
reductio_absurdum.analyzing_consensus
  └─ consensus_count, dissent_count, iteration

sequential_debate.reductio_absurdum_phase_start
  └─ session_id, iteration

sequential_debate.complacency_analysis
  └─ complacency_risk, weak_assumptions, unquestioned_premises

sequential_debate.high_complacency_detected
  └─ risk (percentage)

sequential_debate.absurdum_challenge_complete
  └─ challenger, target, tokens_generated

tribunal.self_challenge_phase
  └─ iteration

tribunal.magistrate_self_challenge
  └─ role, iteration

tribunal.self_challenge_complete
  └─ role, status, found_weakness (bool)
```

### Búsqueda en Logs

```bash
# Ver fase de reducción al absurdo
grep "reductio_absurdum_phase" debug.log

# Ver complacencia detectada
grep "complacency_analysis\|high_complacency" debug.log

# Ver auto-cuestionamiento magistrados
grep "self_challenge" debug.log
```

---

## 🧪 Testing

### Test Manual en API

```bash
# 1. Iniciar debate en modo "standard"
curl -X POST http://localhost:8000/api/debate/create \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "¿Puede la IA ser consciente?",
    "mode": "standard",
    "max_turns": 3
  }'

# 2. Esperar a que complete (incluye Ronda 2 con Reducción al Absurdo)
# 3. Obtener reporte
curl http://localhost:8000/api/debate/{session_id}/report
```

### Indicadores de Éxito

✅ En la Ronda 2, buscar:
- "reductio_absurdum_phase_start" en logs
- Proposiciones siendo desafiadas con "lleva al extremo"
- Cruzamientos adicionales generados por reducción al absurdo

✅ En el Tribunal (Ronda 2):
- "self_challenge_phase" iniciado
- Magistrados identificando debilidades propias
- Scores refinados comparados con iteración 1

---

## 🚀 Próximas Mejoras Sugeridas

1. **Persistencia de Proofs**: Guardar `AbsurdumProof` en base de datos para análisis histórico
2. **ML-based Ranking**: Usar modelo para rankear proposiciones por "vulnerabilidad"
3. **Generación de Contraargumentos**: Crear argumentos FOR/AGAINST para cada proposición
4. **Visualización**: Panel en frontend mostrando qué fue desafiado y cómo se refinó
5. **Métricas de Robustez**: Score de robustez de cada conclusión final del debate

---

## 📚 Referencias

**Técnica Lógica:**
- Reductio ad Absurdum: Wikipedia
- Proof by Contradiction: Stanford Encyclopedia of Philosophy

**Implementación:**
- Inspirado en Debate Techniques usado en competencias de debate académico
- Principios de "Steel Manning" + "Devil's Advocacy"

---

## ❓ FAQ

**P: ¿La Reducción al Absurdo siempre se ejecuta?**  
R: No. Solo se ejecuta en Ronda 2+ si se detecta riesgo alto de complacencia (> 40%)

**P: ¿Puede ralentizar los debates?**  
R: Sí, agrega ~10-20% de tiempo adicional en Ronda 2+. Los magistrados también se auto-cuestionan en iteración 2.

**P: ¿Afecta a debates de 1 ronda?**  
R: No, la fase se ejecuta DESPUÉS de Ronda 1 completada, solo en iteraciones 2+

**P: ¿Qué pasa si no encuentra contradicciones?**  
R: Significa que la proposición es robusto. Se registra como "VÁLIDA" en el análisis.

**P: ¿Puedo desactivarlo?**  
R: Sí, en `_run_reductio_absurdum_phase`, comenta la línea `if complacency_scan.overall_complacency_risk > 0.40:`

