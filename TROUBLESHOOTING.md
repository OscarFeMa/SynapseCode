# 🔧 Guía de Troubleshooting - Synapse Council v2.0

## Índice de Problemas

1. [Servidor no inicia](#servidor-no-inicia)
2. [Ollama no responde](#ollama-no-responde)
3. [Errores de agentes](#errores-de-agentes)
4. [Debate no se guarda](#debate-no-se-guarda)
5. [Supabase no sincroniza](#supabase-no-sincroniza)
6. [Interfaz web no carga](#interfaz-web-no-carga)
7. [Problemas de rendimiento](#problemas-de-rendimiento)

---

## Servidor no inicia

### Síntomas
- `start_synapse.bat` se cierra inmediatamente
- Error "No se encontró entorno virtual"
- Puerto 8000 ya está en uso

### Soluciones

#### 1. Crear entorno virtual
```batch
cd C:\Users\usuario\Desktop\Synapse_Master
python -m venv venv
venv\Scripts\pip install -r backend\requirements.txt
```

#### 2. Puerto ocupado
```batch
:: Buscar proceso usando puerto 8000
netstat -ano | findstr :8000

:: Matar proceso (reemplazar PID)
taskkill /PID [NUMERO_PID] /F
```

#### 3. Verificar Python
```batch
python --version
:: Debe mostrar Python 3.11 o superior

:: Si no funciona, usar ruta completa:
C:\Users\usuario\AppData\Local\Programs\Python\Python312\python.exe -m venv venv
```

---

## Ollama no responde

### Síntomas
- Error "Connection refused" al llamar a Ollama
- Agentes fallan con "ollama.generate.error"
- Timeout en generación de respuestas

### Soluciones

#### 1. Verificar Ollama está ejecutándose
```batch
:: En CMD:
curl http://localhost:11434/api/tags

:: Debe devolver lista de modelos
```

#### 2. Iniciar Ollama manualmente
```batch
:: Opción A - Servicio (recomendado)
ollama serve

:: Opción B - En segundo plano
start ollama serve
```

#### 3. Verificar modelo existe
```batch
ollama list

:: Si falta un modelo:
ollama pull llama3:8b
```

#### 4. Configuración en .env
```env
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Errores de agentes

### Síntomas
- Respuestas de agentes muestran `[Error: ...]`
- Agentes retornan textos vacíos o cortos
- Fallos intermitentes en rondas

### Soluciones

#### 1. Verificar sistema de reintentos está activo
Revisa en `consensus_debate_controller.py`:
```python
# Debe existir esta función:
async def _generate_agent_proposal_with_retry(self, session, agent, max_retries=2):
    fallback_models = ['llama3:8b', 'mistral:7b', 'qwen2.5:3b']
```

#### 2. Reducir tamaño de prompts
Edita el prompt en el código para que sea más corto:
```python
# Reducir num_predict en opciones de Ollama
options = {
    "temperature": 0.7,
    "num_predict": 400  # Reducir de 800 a 400
}
```

#### 3. Usar modelos más ligeros
```batch
:: Cambiar en el código o .env
:: De:
DEFAULT_MODEL=llama3:8b
:: A:
DEFAULT_MODEL=qwen2.5:3b  # Más rápido y estable
```

#### 4. Verificar logs detallados
```batch
:: Buscar errores específicos
cd logs
type synapse_*.log | findstr "ERROR"
```

---

## Debate no se guarda

### Síntomas
- Debates completados no aparecen en lista
- SQLite muestra estado `running` en lugar de `completed`
- `consensus_score` es NULL

### Soluciones

#### 1. Verificar import SQLAlchemy
En `consensus_debate_controller.py`:
```python
# DEBE existir esta línea:
from sqlalchemy import select

# Si falta, agregar después de:
from sqlalchemy.ext.asyncio import AsyncSession
```

#### 2. Verificar base de datos no está bloqueada
```batch
:: Matar procesos Python que puedan tener bloqueo
taskkill /F /IM python.exe

:: Reiniciar y probar de nuevo
start_synapse.bat
```

#### 3. Verificar permisos de directorio
```batch
:: Verificar acceso a carpeta data
icacls data\synapse.db

:: Si hay problemas, ejecutar como Administrador
```

#### 4. Script de verificación
```batch
:: Ejecutar verificación
cd C:\Users\usuario\Desktop\Synapse_Master
venv\Scripts\python.exe scripts\check_db.py
```

---

## Supabase no sincroniza

### Síntomas
- Debates no aparecen en Supabase
- Error "table consensus_debates does not exist"
- Network errors en logs

### Soluciones

#### 1. Verificar tablas creadas en Supabase
Ir a: `https://app.supabase.com/project/[ID]/editor`

Deben existir:
- `consensus_debates`
- `consensus_rounds`
- `consensus_agent_positions`

#### 2. Crear tablas manualmente
Ejecutar en SQL Editor de Supabase:
```sql
-- Ver archivo: supabase_consensus_schema.sql
-- Copiar todo el contenido y ejecutar
```

#### 3. Verificar configuración .env
```env
SUPABASE_URL=https://[tu-proyecto].supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_ENABLED=true
```

#### 4. Verificar políticas RLS
En Supabase, ir a: Auth → Policies

Debe existir:
- Policy "Allow anonymous read access" → SELECT
- Policy "Allow anonymous insert access" → INSERT
- Policy "Allow anonymous update access" → UPDATE

#### 5. Probar con curl
```batch
:: Probar conexión
curl -H "apikey: [TU_KEY]" \
     -H "Authorization: Bearer [TU_KEY]" \
     https://[tu-proyecto].supabase.co/rest/v1/consensus_debates?limit=1
```

---

## Interfaz web no carga

### Síntomas
- `debate_manager.html` muestra página en blanco
- Errores de CORS en consola
- API endpoints no responden

### Soluciones

#### 1. Verificar servidor está activo
```batch
curl http://localhost:8000/health
:: Debe retornar JSON con status
```

#### 2. Verificar ruta de archivos estáticos
El archivo debe estar en:
```
C:\Users\usuario\Desktop\Synapse_Master\web_interface\debate_manager.html
```

Y ser accesible en:
```
http://localhost:8000/static/debate_manager.html
```

#### 3. Abrir directamente desde archivos
Si el servidor no sirve archivos estáticos:
```
file:///C:/Users/usuario/Desktop/Synapse_Master/web_interface/debate_manager.html
```

#### 4. CORS issues
Verificar en `backend/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O tu dominio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Problemas de rendimiento

### Síntomas
- Debates tardan más de 20 minutos
- CPU al 100% durante rondas
- Memoria RAM saturada

### Soluciones

#### 1. Reducir número de agentes
Editar en código:
```python
# En lugar de 4 agentes, usar 2
agents = [
    DebateAgent(id="analyst", ...),
    DebateAgent(id="critic", ...),
    # Reducir synthesizer y refiner
]
```

#### 2. Usar modelos cuantizados
```batch
:: Modelos más rápidos:
ollama pull qwen2.5:3b      # 1.9GB
ollama pull phi3:3.8b       # 2.3GB

:: En lugar de:
ollama pull llama3.1:8b     # 4.7GB
```

#### 3. Reducir tokens de salida
```python
# En prompts de debate, reducir:
max_tokens = 300  # En lugar de 800
```

#### 4. Ejecutar Ollama con GPU (si disponible)
```batch
:: Verificar soporte GPU
ollama run llama3:8b --verbose

:: En logs debe aparecer "using GPU"
```

#### 5. Aumentar timeout
En `backend/adapters/ollama.py`:
```python
# Aumentar timeout para respuestas largas
timeout=300.0  # 5 minutos
```

---

## 🔍 Diagnóstico General

### Comando de verificación completa
```batch
:: 1. Verificar todo el sistema
cd C:\Users\usuario\Desktop\Synapse_Master
check_health.bat

:: 2. Verificar base de datos
venv\Scripts\python.exe scripts\check_db.py

:: 3. Verificar Ollama
curl http://localhost:11434/api/tags

:: 4. Verificar API
curl http://localhost:8000/health

:: 5. Verificar logs
type logs\synapse_*.log | tail -20
```

### Contacto y Soporte

Si ninguna solución funciona:

1. **Recopilar información:**
   - Versión de Python: `python --version`
   - Versión de Ollama: `ollama --version`
   - Logs completos de error
   - Configuración .env (sin claves API)

2. **Pasos de recuperación:**
   ```batch
   :: Reinicio completo limpio
   taskkill /F /IM python.exe
   taskkill /F /IM ollama.exe
   rmdir /S /Q data\synapse.db
   start_synapse.bat
   ```

3. **Reinstalación limpia:**
   ```batch
   :: Backup de datos
   xcopy data backup\ /E /I
   
   :: Reinstalar
   INSTALL_COMPLETE.bat
   ```

---

## 🚨 Errores Comunes y Códigos

| Error | Causa | Solución |
|-------|-------|----------|
| `ModuleNotFoundError` | Falta dependencia | `pip install [modulo]` |
| `ConnectionRefused` | Ollama no responde | Iniciar `ollama serve` |
| `timeout` | Modelo muy lento | Usar modelo más pequeño |
| `IntegrityError` | Conflicto en BD | Eliminar y recrear DB |
| `CORS error` | Configuración web | Revisar middleware CORS |
| `429 Too Many Requests` | Rate limit | Reducir velocidad de requests |

---

**Última actualización:** 2025-04-25  
**Versión documento:** v2.0.0
