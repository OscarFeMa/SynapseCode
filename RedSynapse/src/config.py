"""
Modulo de configuracion compartida para el sistema Pensamiento Coral.
Contiene constantes y parametros de configuracion utilizados tanto por el Master como por los Workers.
"""

import os

# ==================== CONFIGURACION DE SEGURIDAD ====================
# Token secreto compartido para autenticacion entre Master y Workers
# Se carga desde variable de entorno RED_SYNAPSE_SECRET
# Generar uno nuevo con: python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_TOKEN = os.getenv("RED_SYNAPSE_SECRET")
if not SECRET_TOKEN:
    raise RuntimeError(
        "RED_SYNAPSE_SECRET environment variable not set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\" "
        "and add it to your .env file or system environment."
    )

# ==================== CONFIGURACIÓN DE RED ====================
# Puerto UDP para descubrimiento de workers en la red local
UDP_BROADCAST_PORT = 54321

# Puerto TCP para comunicación de comandos y transferencia de datos
TCP_COMMAND_PORT = 54322

# Puerto TCP para transferencia de archivos
TCP_FILE_PORT = 54323

# Dirección de broadcast para descubrimiento UDP
BROADCAST_ADDRESS = "255.255.255.255"

# Timeout para conexiones TCP (en segundos)
TCP_TIMEOUT = 30

# ==================== CONFIGURACIÓN DE HEARTBEAT ====================
# Intervalo de heartbeat en segundos
HEARTBEAT_INTERVAL = 5

# Tiempo máximo sin heartbeat antes de marcar worker como inactivo (en segundos)
HEARTBEAT_TIMEOUT = 15

# ==================== CONFIGURACIÓN DE TAREAS ====================
# Tamaño máximo del buffer para transferencia de datos (en bytes)
BUFFER_SIZE = 4096

# Número máximo de reintentos para una tarea fallida
MAX_TASK_RETRIES = 3

# Tiempo de espera para respuesta de comando (en segundos)
COMMAND_TIMEOUT = 60

# ==================== CONFIGURACIÓN DE LOGGING ====================
# Nivel de logging: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"

# Formato de log
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ==================== CONFIGURACIÓN DE PERSISTENCIA ====================
# Archivo JSON para persistir la información de workers
WORKERS_DB_FILE = "workers_database.json"

# Archivo JSON para persistir el historial de tareas
TASKS_HISTORY_FILE = "tasks_history.json"
