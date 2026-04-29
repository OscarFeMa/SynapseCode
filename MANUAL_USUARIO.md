# Manual de Usuario - SynapseIA v2.0

## ¿Qué es SynapseIA?

SynapseIA es una plataforma de **razonamiento colectivo híbrido** que orquesta múltiples modelos de IA en debates estructurados. El sistema utiliza un **Tribunal de Magistrados** para emitir veredictos soberanos sobre los debates.

---

## Arquitectura del Sistema

### Master (PC Principal)
- **Ubicación:** Este ordenador (192.168.1.41:8000)
- **Función:** Orquesta los debates, gestiona la API y el frontend
- **Rol:** MASTER

### Worker (PC Secundario)
- **Ubicación:** MakederPc (192.168.1.43:11434)
- **Función:** Ejecuta modelos de IA locales (Ollama)
- **Rol:** WORKER

---

## Cómo Iniciar el Sistema

### Paso 1: Iniciar el Backend

```bash
cd D:\proyectos\Synapse
python -m backend.main
```

El sistema iniciará en `http://localhost:8000`

### Paso 2: Verificar el Estado

Abre en tu navegador: `http://localhost:8000/health`

Deberías ver:
- **database:** healthy
- **ollama:** online (con 11 modelos disponibles)
- **lm_studio:** offline (normal si no está configurado)
- **jan:** offline (normal si no está configurado)

---

## Cómo Crear un Debate

### Método 1: Usando curl (Línea de Comandos)

Crea un archivo JSON (ej. `mi_debate.json`):

```json
{
  "topic": "¿Cuáles son las ventajas de la semana laboral de 4 días?",
  "mode": "local_only",
  "agents": [
    {
      "id": "agent1",
      "name": "Analista",
      "role": "analyst",
      "node": "LOCAL",
      "engine": "ollama",
      "model": "llama3.2:latest",
      "provider": "meta",
      "system_prompt": "Analiza el tema propuesto"
    },
    {
      "id": "agent2",
      "name": "Critico",
      "role": "critic",
      "node": "LOCAL",
      "engine": "ollama",
      "model": "mistral:latest",
      "provider": "mistral",
      "system_prompt": "Critica el análisis anterior"
    }
  ]
}
```

Ejecuta el debate:

```bash
curl -X POST http://localhost:8000/api/v1/debate/create \
  -H "Content-Type: application/json" \
  -d @mi_debate.json
```

Respuesta:
```json
{
  "session_id": "abc-123-def",
  "topic": "¿Cuáles son las ventajas de la semana laboral de 4 días?",
  "status": "accepted",
  "mode": "local_only",
  "total_turns": 4
}
```

### Método 2: Usando el Frontend (Web)

Abre en tu navegador: `http://localhost:5173`

1. Escribe tu pregunta en el campo de texto
2. Selecciona el modo (local_only o hybrid)
3. Haz clic en "Iniciar Debate"
4. Observa el debate en tiempo real

---

## Cómo Consultar un Debate

### Obtener el Debate Completo

```bash
curl http://localhost:8000/api/v1/debate/{session_id}
```

### Obtener el Informe Estructurado

```bash
curl http://localhost:8000/api/v1/debate/{session_id}/report
```

Respuesta:
```json
{
  "session_id": "abc-123-def",
  "structured_report": {
    "summary": "Resumen del debate...",
    "consensus_level": 75,
    "key_findings": ["punto 1", "punto 2"],
    "risks_identified": ["riesgo 1"],
    "action_items": ["acción 1"],
    "generated_by": "llama3:8b"
  },
  "source": "memory"
}
```

---

## Roles de los Agentes

El sistema utiliza 4 roles principales en cada debate:

1. **Analyst (Analista):** Analiza el tema propuesto
2. **Critic (Crítico):** Critica el análisis anterior
3. **Synthesizer (Sintetizador):** Sintetiza los argumentos
4. **Refiner (Refinador):** Refina las conclusiones

---

## Tribunal de Magistrados

El Tribunal de Magistrados evalúa el debate y emite un veredicto final. Consta de 3 magistrados:

1. **Magistrado de Evidencias:** Valida la evidencia técnica
2. **Magistrado de Riesgos:** Identifica riesgos potenciales
3. **Magistrado de Alineación:** Evalúa la alineación con objetivos

### Protocolo de Consenso Forzado (PCO)

- El Tribunal puede iterar hasta 3 veces para alcanzar consenso
- Si no hay consenso, emite un veredicto por méritos
- El veredicto es **soberano** (final)

---

## Modelos Disponibles

### Modelos Locales (Ollama)

- **llama3.2:latest** - Modelo generalista (Meta)
- **mistral:latest** - Modelo eficiente (Mistral)
- **phi3:latest** - Modelo compacto (Microsoft)
- **gemma2:2b** - Modelo pequeño (Google)
- **qwen2.5-coder:7b-16k** - Modelo para código (Alibaba)
- **deepseek-r1:7b** - Modelo de razonamiento (DeepSeek)

### Modelos Cloud (Opcional)

- **kimi-k2.6:cloud** - Modelo avanzado (Moonshot)
- **kimi-k2.5:cloud** - Modelo avanzado (Moonshot)
- **deepseek-v4-flash:cloud** - Modelo rápido (DeepSeek)

---

## Modos de Operación

### local_only
- Solo utiliza modelos locales (Ollama)
- Más rápido, sin costes
- Ideal para pruebas y desarrollo

### hybrid
- Combina modelos locales y cloud
- Mayor calidad de respuestas
- Puede tener costes (según proveedor cloud)

---

## Funcionalidades Avanzadas

### Evaluación de Convergencia

El sistema evalúa si los agentes están convergiendo en sus opiniones:
- Evalúa cada 2 turnos
- Si hay convergencia alta, detiene el debate temprano (early stop)
- Ahorra tiempo y recursos

### Monitor de Calidad

Filtra respuestas de baja calidad:
- Respuestas muy cortas (< 80 caracteres)
- Respuestas sin formato esperado
- Respuestas truncadas

### Sistema de Reputación EMA

Cada modelo tiene una puntuación de reputación:
- **TSA:** Tasa de Supervivencia de Argumentos
- **IID:** Índice de Independencia Dialéctica
- **PVT:** Precisión en Validación Técnica
- **Efficiency:** Eficiencia (tokens/ms)

Las puntuaciones se actualizan después de cada turno.

---

## Archivos de Transcripción

Los debates se guardan automáticamente en:
```
D:\proyectos\Synapse\data\debates\
```

Formato: `debate_{session_id}_{timestamp}.md`

---

## Solución de Problemas

### El sistema no arranca

**Error:** `ModuleNotFoundError: No module named 'backend'`

**Solución:**
```bash
cd D:\proyectos\Synapse
python -m backend.main
```

### Ollama no responde

**Error:** `ollama: offline`

**Solución:**
1. Verifica que Ollama esté ejecutándose en el Worker (MakederPc)
2. Ejecuta en el Worker: `ollama serve`
3. Verifica la conexión: `curl http://192.168.1.43:11434/api/tags`

### El debate falla

**Error:** `status: failed`

**Solución:**
1. Revisa los logs en la terminal
2. Verifica que el modelo solicitado esté disponible
3. Prueba con un modelo más pequeño (ej. phi3:latest)

---

## Endpoints API Principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Estado del sistema |
| `/api/v1/debate/create` | POST | Crear nuevo debate |
| `/api/v1/debate/{id}` | GET | Obtener debate |
| `/api/v1/debate/{id}/report` | GET | Obtener informe estructurado |
| `/api/v1/debates` | GET | Listar todos los debates |
| `/api/v1/debug/system` | GET | Diagnóstico del sistema |

---

## Contacto y Soporte

- **Repositorio:** https://github.com/OscarFeMa/SynapseIA
- **Documentación técnica:** Ver `INFORME_TECNICO.md`
- **Workflow local:** Ver `WORKFLOW_LOCAL.md`

---

**Versión:** 2.0.0  
**Última actualización:** 29 de abril de 2026
