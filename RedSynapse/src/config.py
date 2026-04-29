"""
Módulo de configuración compartida para el sistema Pensamiento Coral.
Contiene constantes y parámetros de configuración utilizados tanto por el Master como por los Workers.
"""

# ==================== CONFIGURACIÓN DE SEGURIDAD ====================
# Token secreto compartido para autenticación entre Master y Workers
# IMPORTANTE: Cambiar este valor en producción
SECRET_TOKEN = "pensamiento_coral_2024_secure_token"

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
