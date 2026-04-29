# Pensamiento Coral - Sistema de Computación Distribuida

Un ecosistema de procesamiento en paralelo mediante arquitectura Master-Worker que conecta dispositivos Windows 11 y Android (vía Termux) en una red local Wi-Fi.

## 🌟 Características

- **Auto-descubrimiento de red:** Los workers son detectados automáticamente mediante UDP broadcast
- **Identificación persistente:** Los workers se identifican por dirección MAC para mantener identidad persistente
- **Interfaz gráfica moderna:** Master con GUI usando customtkinter
- **Ejecución de comandos remotos:** Terminal integrada para enviar comandos a workers
- **Cola de tareas distribuida:** Sistema de cola con prioridades y reasignación automática
- **Multiplataforma:** Workers en Windows 11 y Android/Termux
- **Heartbeat automático:** Monitoreo de conectividad en tiempo real
- **Seguridad:** Token de autenticación compartido para conexiones seguras

## 📋 Requisitos del Sistema

### Master (Windows 11)
- Windows 11 o superior
- Python 3.8 o superior
- Conexión a red local Wi-Fi
- Dependencias: `customtkinter`, `tkinter`

### Worker (Windows 11)
- Windows 11 o superior
- Python 3.8 o superior
- Conexión a la misma red Wi-Fi que el Master

### Worker (Android/Termux)
- Android 7.0 o superior
- Termux (instalar desde F-Droid)
- Python en Termux
- Conexión a la misma red Wi-Fi que el Master

## 🚀 Instalación Rápida

### Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/PensamientoCoral.git
cd PensamientoCoral
```

### Instalar Dependencias (Master - Windows)

```bash
pip install customtkinter
```

### Instalar Dependencias (Worker - Android/Termux)

```bash
pkg update && pkg upgrade
pkg install python
termux-setup-storage
```

## 📖 Uso

### Iniciar el Master (Windows)

```bash
cd src
python Master.py
```

Se abrirá la interfaz gráfica con:
- Tabla de workers conectados
- Botón para escanear red
- Terminal integrada
- Cola de tareas
- Historial de ejecuciones

### Iniciar el Worker (Windows)

```bash
cd src
python Worker.py
```

Opcionalmente, conectar directamente a un Master específico:

```bash
python Worker.py --master 192.168.1.100
```

### Iniciar el Worker (Android/Termux)

```bash
cd ~/PensamientoCoral/src
python Worker.py
```

Para ejecución en segundo plano:

```bash
nohup python Worker.py > worker.log 2>&1 &
```

Consulte [docs/ANDROID_DEPLOYMENT.md](docs/ANDROID_DEPLOYMENT.md) para instrucciones detalladas de Android.

## 🎯 Funcionalidades

### Escaneo de Red

1. Inicie el Master
2. Haga clic en "🔍 Escanear Red"
3. Los workers activos aparecerán en la tabla automáticamente

### Ejecución de Comandos

1. Seleccione un worker específico o "Todos"
2. Escriba el comando en el campo de texto
3. Presione Enter o haga clic en "Ejecutar"
4. La salida aparecerá en la terminal

### Cola de Tareas

1. Vaya a la pestaña "Cola de Tareas"
2. Escriba el comando a ejecutar
3. Asigne una prioridad (opcional, 0 por defecto)
4. Haga clic en "Agregar Tarea"
5. Las tareas se distribuirán automáticamente entre workers disponibles

### Reasignación Automática

Si un worker falla durante una tarea:
- La tarea se reasigna automáticamente a otro worker
- Se permite hasta 3 reintentos por tarea
- El historial de intentos se guarda

## 🔧 Configuración

Edite `src/config.py` para personalizar:

```python
# Token de seguridad (CAMBIAR EN PRODUCCIÓN)
SECRET_TOKEN = "pensamiento_coral_2024_secure_token"

# Puertos de red
UDP_BROADCAST_PORT = 54321
TCP_COMMAND_PORT = 54322
TCP_FILE_PORT = 54323

# Intervalo de heartbeat (segundos)
HEARTBEAT_INTERVAL = 5

# Timeout de heartbeat (segundos)
HEARTBEAT_TIMEOUT = 15

# Máximo de reintentos por tarea
MAX_TASK_RETRIES = 3
```

## 📦 Empaquetamiento

### Crear Ejecutable Windows

Ejecute el script de empaquetamiento:

```bash
cd scripts
build_windows.bat
```

Esto generará:
- `dist/PensamientoCoral_Master.exe`
- `dist/PensamientoCoral_Worker.exe`

Distribuya estos ejecutables sin necesidad de instalar Python.

## 🏗️ Arquitectura

```
PensamientoCoral/
├── src/
│   ├── config.py          # Configuración compartida
│   ├── Master.py          # Nodo central con GUI
│   └── Worker.py          # Agente de ejecución
├── scripts/
│   └── build_windows.bat  # Script de empaquetamiento
├── docs/
│   └── ANDROID_DEPLOYMENT.md  # Guía para Android
└── README.md              # Este archivo
```

### Flujo de Comunicación

1. **Descubrimiento:** Master envía UDP broadcast → Workers responden con info
2. **Handshake:** Master y Worker intercambian tokens de autenticación
3. **Conexión TCP:** Se establece canal persistente para comandos
4. **Heartbeat:** Worker envía latidos cada 5 segundos
5. **Ejecución:** Master envía comandos → Worker ejecuta → Retorna resultado

## 🔒 Seguridad

- **Token de autenticación:** Todas las conexiones requieren el token secreto
- **Validación de handshake:** Solo workers registrados pueden conectarse
- **Identificación por MAC:** Evita suplantación de identidad
- **Timeout de heartbeat:** Detecta workers desconectados automáticamente

## 🐛 Solución de Problemas

### Workers no aparecen en escaneo

1. **Verificar red:** Asegúrese de que Master y Workers estén en la misma red Wi-Fi
2. **Verificar firewall:** Windows Firewall puede bloquear UDP broadcast
3. **Usar conexión directa:** `python Worker.py --master <IP_MASTER>`

### Error de conexión rechazada

1. **Verificar token:** Asegúrese de que `SECRET_TOKEN` sea idéntico en Master y Workers
2. **Reiniciar workers:** Los workers deben escanear después de iniciar el Master

### Comandos no se ejecutan

1. **Verificar estado:** El worker debe mostrar "Active" en la tabla
2. **Verificar heartbeat:** Si el worker está "Inactive", reinícielo
3. **Verificar permisos:** Algunos comandos requieren privilegios elevados

## 📊 Monitoreo

### En la GUI del Master

- **Estado de workers:** Activo/Inactivo basado en heartbeat
- **Carga de CPU:** Porcentaje de uso (si disponible)
- **Historial de tareas:** Registro completo de ejecuciones
- **Terminal en tiempo real:** Salida de comandos

### Logs

Los logs se generan en la terminal con formato:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Nivel de log configurable en `config.py`.

## 🔄 Actualización

### Actualizar desde Git

```bash
git pull origin main
```

### Actualizar Workers

1. Detenga workers en ejecución
2. Reemplace archivos `Worker.py` y `config.py`
3. Reinicie workers

## 🤝 Contribuciones

Este proyecto es modular y extensible. Algunas ideas para futuras expansiones:

- Transferencia de archivos entre Master y Workers
- Ejecución de scripts Python remotos
- Sistema de prioridades dinámicas
- Monitoreo de recursos en tiempo real
- Soporte para VPN y redes remotas
- Interfaz web alternativa
- Sistema de plugins

## 📝 Licencia

Este proyecto es de código abierto. Úselo y modifíquelo libremente.

## 👥 Autores

Desarrollado como parte del proyecto "Pensamiento Coral" para computación distribuida.

## 📞 Soporte

Para problemas o preguntas:
- Revise la documentación en `docs/`
- Consulte los logs para errores detallados
- Verifique la configuración de red y firewall

## 🎓 Concepto

"Pensamiento Coral" representa la idea de múltiples dispositivos trabajando en conjunto, como un coral, formando un sistema de procesamiento distribuido más potente que la suma de sus partes.

---

**¡Disfrute de su clúster de computación distribuida!**
