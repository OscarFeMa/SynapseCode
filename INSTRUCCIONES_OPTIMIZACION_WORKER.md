# Instrucciones de Optimización del Worker Synapse

## Objetivo
Liberar memoria RAM y configurar GPU en el Worker para ejecutar modelos de IA más grandes.

## Pasos a seguir en el Worker (192.168.1.43)

### 1. Copiar scripts al Worker
Copia estos archivos desde el Master al Worker:
- `optimizar_worker_completo.bat`
- `configurar_ollama_gpu.bat`

Puedes usar:
- RDP (Escritorio Remoto) para acceder al Worker
- Compartir carpeta de red
- USB

### 2. Ejecutar optimización de memoria
En el Worker:
1. Abre `optimizar_worker_completo.bat` como **Administrador**
2. Sigue las instrucciones
3. El script:
   - Detiene servicios innecesarios (Windows Search, Xbox, etc.)
   - Cierra navegadores y aplicaciones que consumen RAM
   - Limpia archivos temporales
   - Configura variables de entorno para Ollama
   - Aumenta memoria virtual
   - Reinicia Ollama con configuración GPU

### 3. Configurar Ollama para GPU
En el Worker:
1. Abre `configurar_ollama_gpu.bat` como **Administrador**
2. El script:
   - Verifica GPU NVIDIA
   - Configura variables de entorno para GPU
   - Descarga modelos optimizados:
     - `llama3:8b` (~4.6GB VRAM)
     - `qwen2.5:7b` (~4.2GB VRAM)
     - `mistral:7b` (~4.1GB VRAM)

### 4. Verificar configuración
En el Worker, ejecuta:
```cmd
nvidia-smi
```
Deberías ver la GPU y su memoria libre.

```cmd
ollama list
```
Deberías ver los modelos descargados.

### 5. Actualizar configuración en Master
En el Master, actualiza `backend/engine/round_controller.py`:
```python
ANALYSIS_AGENTS = [
    AgentConfig("analyst_local_a", "LOCAL", "ollama", "llama3:8b", "Analista Técnico", max_tokens=1000),
    AgentConfig("analyst_local_b", "LOCAL", "ollama", "qwen2.5:7b", "Analista Estratégico", max_tokens=1000),
    AgentConfig("analyst_local_c", "LOCAL", "ollama", "mistral:7b", "Analista Empírico", max_tokens=1000),
]
```

### 6. Restaurar ejecución paralela
En `backend/engine/agent_orchestrator.py`, restaura la ejecución paralela:
```python
# Ejecutar en paralelo
tasks = [call_single(config) for config in agent_configs]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 7. Probar
Reinicia el Master y ejecuta una sesión de prueba.

## Notas importantes

- **GPU NVIDIA requerida**: Los scripts requieren GPU NVIDIA con drivers CUDA instalados
- **Memoria VRAM**: Verifica que tu GPU tenga suficiente VRAM (mínimo 8GB recomendado)
- **RAM**: El Worker debería tener al menos 16GB RAM para modelos grandes
- **Ejecutar como Administrador**: Ambos scripts requieren privilegios de administrador

## Solución de problemas

### Si Ollama no usa GPU:
```cmd
set OLLAMA_NUM_GPU=999
set OLLAMA_GPU_OVERHEAD=0
ollama serve
```

### Si modelos fallan por memoria:
- Reduce `OLLAMA_MAX_LOADED_MODELS` a 1
- Usa modelos más pequeños (qwen2.5:3b, tinyllama)
- Cierra otras aplicaciones en el Worker

### Si GPU no se detecta:
- Instala drivers NVIDIA CUDA más recientes
- Verifica que la GPU esté habilitada en el BIOS
- Ejecuta `nvidia-smi` para verificar
