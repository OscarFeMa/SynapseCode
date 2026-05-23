# ESTADO ACTUAL - SYNAPSE COUNCIL MASTER-WORKER
## Documento de Continuidad para Arranque en Otro Ordenador
**Fecha:** 25 de Abril de 2026, 16:30
**Sesión:** Depuración de Worker Optimization y Modelos Grandes

---

## 1. RESUMEN EJECUTIVO

### Objetivo Original
Optimizar el Worker PC (<MASTER_IP>) para liberar memoria RAM y utilizar GPU, permitiendo ejecutar modelos grandes de AI (llama3:8b, mistral:7b, qwen2.5:7b) en local sin que los agentes se queden atascados en estado STREAMING.

### Estado Actual (ACTUALIZADO 16:40)
- **Worker optimizado:** ✅ Script ejecutado, memoria liberada, modelos descargados
- **Modelos verificados:** llama3:8b, mistral:7b, llama3.1:8b, tinyllama - TODOS funcionan con curl directo
- **Problema identificado:** ❌ Todos los modelos FALLAN desde el Master (incluso tinyllama)
- **Causa raíz:** NO es la complejidad del prompt (incluso "Hola" falla)
- **Hipótesis actual:** Problema en el consumo del generador async o circuit breaker
- **Logging agregado:** ✅ Se agregó logging detallado en:
  - `backend/adapters/ollama.py` - Método generate()
  - `backend/engine/local_engine_manager.py` - Método generate()
- **Próximo paso:** Verificar logs de structlog (pueden estar en archivo, no en consola)

---

## 2. INFRAESTRUCTURA CONFIGURADA

### Master Node (Este Ordenador)
- **IP:** <WORKER_IP>
- **Ruta proyecto:** `C:\Users\usuario\Desktop\Synapse_Master\`
- **Estado:** Servicio reiniciando (Background command ID: 1798)
- **Puerto API:** 8000

### Worker Node (MakederPc)
- **IP:** <MASTER_IP>
- **Usuario Windows:** `<WORKER_USERNAME>`
- **Contraseña Windows:** `<WORKER_PASSWORD>`
- **Contraseña RDP:** `<WORKER_PASSWORD>` (nota: usar usuario "maked" sin dominio para RDP)
- **Ollama URL:** http://`<WORKER_IP>`:11434
- **Ruta Ollama:** C:\Users\maked\AppData\Local\Programs\Ollama\ollama.exe
- **Acceso:** Via RDP (WinRM/SSH no configurados)

### Modelos Disponibles en Worker (Verificados)
```json
[
  {"name": "mistral:7b", "size": "4.37GB", "status": "disponible"},
  {"name": "llama3:8b", "size": "4.66GB", "status": "disponible"},
  {"name": "llama3.1:8b", "size": "4.92GB", "status": "disponible"},
  {"name": "qwen2.5:3b", "size": "1.93GB", "status": "disponible"},
  {"name": "tinyllama:latest", "size": "637MB", "status": "disponible"}
]
```

**Nota importante:** El modelo `qwen2.5:7b` falló al descargar por error de red. Se usa `qwen2.5:3b` como alternativa.

---

## 3. CAMBIOS REALIZADOS EN CÓDIGO

### Archivo: `backend/engine/round_controller.py`
**Última modificación:** Simplificado a 1 agente para depuración
```python
ANALYSIS_AGENTS = [
    AgentConfig("analyst_local_a", "LOCAL", "ollama", "llama3:8b", "Analista Técnico", max_tokens=1000),
]

CRITIQUE_MAPPING = {
    "critic_local_a": ("analyst_local_a", "LOCAL", "ollama", "Crítico Técnico", "llama3:8b"),
}

SYNTHESIS_AGENTS = [
    AgentConfig("synth_local", "LOCAL", "ollama", "llama3:8b", "Sintetizador Local", max_tokens=1000),
]
```

### Archivo: `backend/engine/agent_orchestrator.py`
**Última modificación:** Forzado stream=True siempre en llamadas locales
```python
# En call_agents_parallel(), método call_single():
# Se cambió de ejecución paralela a secuencial temporalmente

# En call_agent(), llamada a LOCAL:
# Forzar stream=True siempre para asegurar consumo completo del generador
async for token in self.local_manager.generate(
    engine_type=engine_type,
    model=config.model,
    prompt=user_prompt,
    system=system_prompt,
    temperature=config.temperature,
    max_tokens=config.max_tokens,
    stream=True  # <-- FORZADO A TRUE
):
```

---

## 4. PROBLEMA ACTUAL EN INVESTIGACIÓN

### Síntoma
Los modelos grandes (llama3:8b, mistral:7b) fallan cuando se ejecutan desde el Master, mostrando estado FAILED en la base de datos.

### Evidencia Recolectada
1. **Funciona individualmente:** 
   ```bash
   curl -X POST http://<MASTER_IP>:11434/api/generate \
     -H "Content-Type: application/json" \
     -d '{"model":"llama3:8b","prompt":"Hola","stream":false}'
   # Respuesta exitosa: "¡Hola! ¿En qué puedo ayudarte hoy?"
   ```

2. **Fallo desde el sistema:**
   - Estado en BD: FAILED
   - No se registran tokens de entrada/salida
   - No hay response_preview
   - Logs muestran: "Fase de análisis abortada: >50% de agentes fallaron"

3. **Comportamiento observado:**
   - Con stream=False: Los agentes se quedaban en STREAMING indefinidamente
   - Con stream=True forzado: Los agentes marcan FAILED inmediatamente
   - Ejecución secuencial vs paralela: Mismo resultado (FAILED)
   - Prompt simple vs complejo: Ambos fallan

### Hipótesis Actuales
1. **Consumo del generador async:** El generador de Ollama no se consume completamente en el contexto async del Master
2. **Manejo de errores:** Las excepciones en el generador no se capturan correctamente
3. **Timeout:** El modelo grande puede tardar más de lo que el sistema permite
4. **Contexto de ejecución:** Diferencia entre curl (síncrono) y el loop async del Master

---

## 5. SESIONES DE PRUEBA CREADAS

### Sesión 1: Con modelo complejo
- ID: `3ac27854-f698-4df7-8c1f-868efa3aa6e5`
- Query: "¿Cuál es la mejor estrategia para aprender programación?"
- Resultado: FAILED
- Tiempo de ejecución: ~2-3 segundos (muy rápido para fallo)

### Sesión 2: Con prompt simple
- ID: `f2e6891e-6382-43ee-8bc7-29aefbdd6469`
- Query: "Hola"
- **Resultado: FAILED** ✅ VERIFICADO
- Propósito: Aislar si el problema es la longitud/complejidad del prompt
- **Conclusión CRÍTICA:** El problema NO es el prompt. Incluso con "Hola" simple falla.
- **Implicación:** El problema es fundamental en el consumo del generador async de Ollama

### Archivos de prueba creados
- `test_session.json` - Query compleja original
- `test_session_simple.json` - Query simple "Hola"
- `test_llama3_8b.json` - Test directo de Ollama

---

## 6. SCRIPTS EN USB F: (PARA WORKER)

### Archivos disponibles en F:\
1. **`INSTALACION_AUTOMATICA_OPTIMIZACION.bat`**
   - Script completo de optimización
   - Libera RAM, configura GPU, descarga modelos
   - Genera log en C:\Users\maked\Desktop\optimizacion_log.txt

2. **`configurar_acceso_remoto_worker.bat`**
   - Intenta configurar WinRM/RDP (falló en ejecución anterior)
   - No es crítico para operación actual

3. **`INSTRUCCIONES_OPTIMIZACION_WORKER.md`**
   - Guía de ejecución manual

4. **`optimizar_worker_simple.bat`**
   - Versión simplificada del script de optimización
   - Más logs visibles

### Estado de ejecución en Worker
- Script ejecutado: ✅ SÍ (usuario lo ejecutó via RDP)
- Modelos descargados: ✅ SÍ (llama3:8b, mistral:7b, llama3.1:8b)
- Memoria liberada: ✅ SÍ (servicios detenidos)
- Variables de entorno GPU: ✅ Configuradas

---

## 7. PRÓXIMOS PASOS (CHECKLIST)

### Inmediatos (para continuar esta sesión)
- [ ] Verificar resultado de sesión con prompt simple (`f2e6891e-6382-43ee-8bc7-29aefbdd6469`)
- [ ] Si falla con prompt simple: Problema es más fundamental (no relacionado con prompt)
- [ ] Si funciona con prompt simple: Problema es el prompt/límite de tokens
- [ ] Revisar logs detallados de Ollama en el Worker (si existen)
- [ ] Probar con tinyllama para confirmar que el flujo funciona

### Debugging técnico (si prompt simple falla)
- [ ] Agregar logging detallado en `local_engine_manager.py` en método `generate()`
- [ ] Verificar que el generador async se consume completamente (no se abandona a mitad)
- [ ] Revisar manejo de excepciones en `agent_orchestrator.py` línea ~202
- [ ] Comparar payload exacto enviado por Master vs curl que funciona
- [ ] Considerar usar `ollama.chat()` en lugar de `ollama.generate()` si el formato es diferente

### Alternativas si no se resuelve
- [ ] Volver a tinyllama y probar con múltiples agentes en paralelo (verificar que el problema es solo con modelos grandes)
- [ ] Usar LM Studio en lugar de Ollama (puede manejar mejor los modelos grandes)
- [ ] Configurar un timeout más largo para modelos grandes
- [ ] Considerar usar OpenRouter para modelos grandes y locales para pequeños

### Optimización final (cuando funcione)
- [ ] Restaurar configuración completa con 3+ agentes
- [ ] Verificar ejecución paralela funciona correctamente
- [ ] Probar cruce híbrido local-cloud
- [ ] Ejecutar sesión completa de 3 rondas

---

## 8. COMANDOS ÚTILES PARA CONTINUAR

### Verificar estado de sesión
```bash
curl http://localhost:8000/api/v1/sessions/{session_id}
```

### Verificar modelos en Worker
```bash
curl http://<MASTER_IP>:11434/api/tags
```

### Test directo de modelo
```bash
curl -X POST http://<MASTER_IP>:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3:8b","prompt":"Hola","stream":false}'
```

### Crear nueva sesión de prueba
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","query":"Hola"}'
```

### Verificar logs del Master (en otra terminal)
```bash
cd C:\Users\usuario\Desktop\Synapse_Master
tail -f logs\synapse.log  # Si existe
```

---

## 9. NOTAS CRÍTICAS PARA CONTINUIDAD

### Lo que SÍ funciona actualmente
- ✅ Master-Worker comunicación básica
- ✅ Ollama respondiendo a curl directo
- ✅ Descarga de modelos completada
- ✅ Optimización de memoria en Worker
- ✅ Configuración de variables GPU

### Lo que NO funciona actualmente
- ❌ Modelos grandes desde el sistema Master
- ❌ Acceso remoto automatizado (WinRM/SSH)
- ❌ Ejecución en paralelo (cambiada a secuencial temporalmente)

### Decisiones pendientes
1. **¿Seguir con modelos grandes o volver a tinyllama?**
   - Si no se resuelve en 30 min más, sugerir volver a tinyllama y probar paralelo
   
2. **¿Usar LM Studio como alternativa a Ollama?**
   - LM Studio puede tener mejor manejo de memoria GPU
   
3. **¿Configurar WinRM en Worker para acceso remoto automatizado?**
   - Baja prioridad si RDP funciona

---

## 10. CONTACTO Y ACCESOS

### Worker PC (MakederPc)
- IP: <MASTER_IP>
- RDP: 3389
- Usuario RDP: maked
- Contraseña RDP: <WORKER_PASSWORD>
- Ollama: http://<MASTER_IP>:11434

### Master PC (Este ordenador)
- IP: <WORKER_IP>
- API: http://localhost:8000
- Ruta: C:\Users\usuario\Desktop\Synapse_Master\

---

## 11. CONTEXTO HISTÓRICO DE ESTA SESIÓN

### Checkpoint 14 (inicio de esta sesión)
- Todo list tenía items pendientes sobre optimización del Worker
- Se habían creado scripts para optimización automática
- El usuario ejecutó el script en el Worker via RDP
- Modelos grandes descargados: llama3:8b, mistral:7b

### Problemas encontrados en esta sesión
1. Modelos grandes funcionan con curl pero no desde Master
2. Se forzó stream=True en agent_orchestrator
3. Se cambió a ejecución secuencial temporalmente
4. Se simplificó a 1 agente para aislar problema
5. Se creó sesión de prueba con prompt simple "Hola"

### Estado de archivos modificados
- `backend/engine/round_controller.py` - Simplificado a 1 agente
- `backend/engine/agent_orchestrator.py` - stream=True forzado, ejecución secuencial
- `backend/engine/agent_orchestrator.py` - (líneas 261-309) método call_agents_parallel modificado
- `test_session_simple.json` - Creado para prueba
- `test_llama3_8b.json` - Creado para test directo

---

## 12. CONCLUSIÓN Y ESTADO FINAL DE LA SESIÓN

**Punto exacto donde estamos:**
El Master está corriendo. Se ha agregado logging detallado en TODO el flujo de ejecución:
- `backend/main.py` - Configuración de structlog para consola
- `backend/adapters/ollama.py` - Logging en método generate()
- `backend/engine/local_engine_manager.py` - Logging en método generate()
- `backend/engine/agent_orchestrator.py` - Logging en método call_agent()

**Descubrimientos CRÍTICOS:**
1. **Worker optimizado correctamente:** Modelos descargados (llama3:8b, mistral:7b, tinyllama)
2. **Curl funciona:** Todos los modelos responden correctamente via curl directo
3. **Master falla:** Todos los modelos fallan cuando se ejecutan desde el sistema (incluso tinyllama)
4. **No es el prompt:** Incluso "Hola" simple falla
5. **Logging agregado:** Se configuró structlog para mostrar en consola, pero NO se ven los logs de call_agent

**Hipótesis actual:**
El problema puede estar en:
- Circuit breaker activo (después de 3 fallos, el motor se bloquea por 60 segundos)
- Health check fallando antes de llegar al generate()
- Excepción silenciosa antes del logging
- Problema en la inicialización del LocalEngineManager

**Próximos pasos para continuar desde otro ordenador:**

### Paso 1: Verificar logs detallados
Ejecutar una sesión de prueba y observar la consola del Master:
```bash
curl -X POST http://localhost:8000/api/v1/sessions -H "Content-Type: application/json" -d '{"title":"Test","query":"Hola"}'
```

Buscar en la consola logs de:
- `call_agent.starting_generation`
- `local_engine.generate.start`
- `ollama.generate.start`

Si NO aparecen estos logs: El problema está ANTES de llegar al agente (posiblemente en el circuit breaker o en el health check).

### Paso 2: Verificar circuit breaker
El circuit breaker se activa después de 3 fallos consecutivos y bloquea el motor por 60 segundos. Esperar 60 segundos entre pruebas o reiniciar el Master.

### Paso 3: Probar llamada directa
Crear un script de prueba que llame directamente al OllamaClient sin pasar por el sistema completo:
```python
import asyncio
from backend.adapters.ollama import OllamaClient

async def test():
    client = OllamaClient(base_url="http://<MASTER_IP>:11434")
    async for token in client.generate(model="tinyllama:latest", prompt="Hola"):
        print(token)

asyncio.run(test())
```

### Paso 4: Verificar health check
El health check está en `local_engine_manager.py` línea 59-86. Verificar si está retornando `status: online`.

**Archivos modificados en esta sesión:**
- `backend/main.py` - Configuración logging
- `backend/adapters/ollama.py` - Logging detallado
- `backend/engine/local_engine_manager.py` - Logging detallado
- `backend/engine/agent_orchestrator.py` - Logging detallado + stream=True forzado
- `backend/engine/round_controller.py` - Configuración simplificada a 1 agente
- `ESTADO_ACTUAL_SESION.md` - Documento de continuidad creado

---

## ANEXO: COMANDOS DE VERIFICACIÓN RÁPIDA

Al arrancar en otro ordenador, ejecutar en orden:

```bash
# 1. Verificar Master está corriendo
curl http://localhost:8000/health

# 2. Verificar Worker responde
curl http://<MASTER_IP>:11434/api/tags

# 3. Verificar sesión de prueba reciente
curl http://localhost:8000/api/v1/sessions/f2e6891e-6382-43ee-8bc7-29aefbdd6469

# 4. Crear nueva sesión de prueba simple
curl -X POST http://localhost:8000/api/v1/sessions -H "Content-Type: application/json" -d '{"title":"Test","query":"Hola"}'
```

---

**Fin del documento de continuidad**
**Próxima acción recomendada:** Verificar estado de sesión f2e6891e-6382-43ee-8bc7-29aefbdd6469
