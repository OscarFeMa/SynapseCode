# Configuración del Synapse Worker (Otro PC)

## Requisitos Previos
- Ollama o LM Studio corriendo en el puerto 11434 (Ollama) o 1234 (LM Studio)
- Python 3.10+ instalado
- Ambos PCs en la misma red local

## Pasos de Configuración

### 1. Copiar archivos al PC Worker
Copia esta carpeta `Synapse_Worker` al otro PC.

### 2. Ejecutar configuración automática
Abre CMD o PowerShell en la carpeta `Synapse_Worker` y ejecuta:

```batch
configure_worker.bat
```

O manualmente crea el archivo `.env`:

```ini
NODE_ROLE=WORKER
PORT=8001
HOST=0.0.0.0

WORKER_OLLAMA_PORT=11434
WORKER_LM_STUDIO_PORT=1234
WORKER_JAN_PORT=1337

SUPABASE_ENABLED=false
WEB_AGENT_ENABLED=false

DISCOVERY_PORT=54321
DISCOVERY_INTERVAL=5
```

### 3. Verificar motores locales
Antes de iniciar, asegúrate de que los motores estén corriendo:

```batch
# Test Ollama
curl http://localhost:11434/api/tags

# Test LM Studio
curl http://localhost:1234/v1/models
```

### 4. Iniciar el Worker

```batch
start_worker.bat
```

O manualmente:

```batch
venv\Scripts\activate
python backend\main.py
```

### 5. Verificar que está corriendo

```batch
curl http://localhost:8001/health
curl http://localhost:8001/api/v1/network/peers
```

## Comunicación Master-Worker

Una vez ambos estén corriendo:

1. **Discovery automático**: Los nodos se detectan vía UDP broadcast (puerto 54321)
2. **El Master** obtiene automáticamente la IP del Worker
3. **Las peticiones** de motores locales del Master van al Worker

## Firewall de Windows

Si hay problemas de conexión, abre estos puertos en el firewall:

```batch
# Como Administrador:
netsh advfirewall firewall add rule name="Synapse-UDP" dir=in action=allow protocol=udp localport=54321
netsh advfirewall firewall add rule name="Synapse-HTTP" dir=in action=allow protocol=tcp localport=8001
```

## Verificación

En el Master (este PC), verifica que ve al Worker:

```batch
curl http://localhost:8000/api/v1/network/peers
```

Debería mostrar:
```json
{
  "status": "active",
  "peers": [
    {"role": "WORKER", "ip": "192.168.x.x", ...}
  ]
}
```

## Solución de Problemas

### No se detectan los peers
1. Verifica que ambos PCs estén en la misma red/subred
2. Desactiva temporalmente el firewall para probar
3. Ejecuta en ambos PCs: `python scripts\network_diagnostic.py`

### Error "bind failed"
El puerto 54321 está en uso. Cierra otras instancias de Synapse.

### El Master no conecta al Worker
1. Verifica la IP del Worker: `ipconfig` en el PC Worker
2. Configura manualmente en el Master `.env`: `WORKER_HOST=IP_DEL_WORKER`
3. Reinicia el Master

## Arquitectura

```
┌──────────────────┐         UDP Broadcast         ┌──────────────────┐
│   MASTER (Este)  │  ←────────────────────────→   │     WORKER       │
│                  │      Puerto 54321             │   (Otro PC)      │
│  - OpenRouter    │                               │  - Ollama        │
│  - Web Agent     │  ←───── HTTP ──────────────→  │  - LM Studio     │
│  - Puerto 8000   │      Motores Locales          │  - Puerto 8001   │
└──────────────────┘                               └──────────────────┘
```
