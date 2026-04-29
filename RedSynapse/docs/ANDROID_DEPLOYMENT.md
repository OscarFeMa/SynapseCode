# Guía de Despliegue para Android/Termux

Esta guía explica cómo configurar y ejecutar el Worker de Pensamiento Coral en dispositivos Android usando Termux.

## Requisitos Previos

- Dispositivo Android (versión 7.0 o superior recomendada)
- Conexión a la misma red Wi-Fi que el Master
- Al menos 500 MB de espacio libre

## Paso 1: Instalar Termux

1. Descarga Termux desde F-Droid (recomendado) o desde GitHub releases:
   - F-Droid: https://f-droid.org/packages/com.termux/
   - GitHub: https://github.com/termux/termux-app/releases

2. Instala el APK en tu dispositivo Android

## Paso 2: Configurar Termux

Abre Termux y ejecuta los siguientes comandos:

```bash
# Actualizar paquetes
pkg update && pkg upgrade

# Configurar almacenamiento (permite acceder a archivos del sistema)
termux-setup-storage

# Instalar Python
pkg install python

# Instalar dependencias adicionales
pip install --upgrade pip
```

## Paso 3: Obtener el Código del Worker

### Opción A: Clonar desde Git (si tienes el repositorio)

```bash
# Instalar git
pkg install git

# Clonar el repositorio (reemplaza con tu URL)
git clone https://github.com/tu-usuario/PensamientoCoral.git
cd PensamientoCoral/src
```

### Opción B: Transferir archivo manualmente

1. Copia el archivo `src/Worker.py` y `src/config.py` a tu dispositivo
2. Mueve los archivos al directorio de Termux:
   ```bash
   # Los archivos estarán en /sdcard/Download/
   cp /sdcard/Download/Worker.py ~/PensamientoCoral/
   cp /sdcard/Download/config.py ~/PensamientoCoral/
   cd ~/PensamientoCoral
   ```

## Paso 4: Ejecutar el Worker

### Ejecución Interactiva (para pruebas)

```bash
cd ~/PensamientoCoral
python Worker.py
```

El Worker comenzará a escuchar mensajes de descubrimiento del Master.

### Ejecución como Servicio en Segundo Plano

Para que el Worker se ejecute en segundo plano incluso cuando cierres Termux:

```bash
# Instalar termux-service
pkg install termux-services

# Habilitar el servicio de runit
sv-enable termux-services

# Crear script de servicio
mkdir -p ~/.termux/service
cat > ~/.termux/service/worker << 'EOF'
#!/data/data/com.termux/files/usr/bin/sh
cd ~/PensamientoCoral
python Worker.py
EOF

# Dar permisos de ejecución
chmod +x ~/.termux/service/worker

# Iniciar el servicio
sv up worker
```

### Ejecución con nohup (alternativa simple)

```bash
cd ~/PensamientoCoral
nohup python Worker.py > worker.log 2>&1 &
```

Para ver el log:
```bash
tail -f worker.log
```

## Paso 5: Verificar Conexión

1. En el Master (Windows), ejecuta `Master.py`
2. Haz clic en el botón "🔍 Escanear Red"
3. El Worker de Android debería aparecer en la tabla de workers

## Paso 6: Conexión Directa (Opcional)

Si conoces la IP del Master, puedes conectar el Worker directamente:

```bash
python Worker.py --master 192.168.1.100
```

Reemplaza `192.168.1.100` con la IP real de tu Master.

## Solución de Problemas

### El Worker no aparece en el escaneo

1. **Verificar que estén en la misma red:**
   ```bash
   # En Termux
   ip addr show wlan0
   ```
   Asegúrate de que la IP esté en el mismo rango que el Master.

2. **Verificar firewall:**
   - Algunos routers bloquean broadcast UDP
   - Intenta usar conexión directa con `--master`

3. **Verificar que el Worker esté corriendo:**
   ```bash
   ps aux | grep Worker.py
   ```

### Error de permisos de almacenamiento

```bash
# Reconfigurar almacenamiento
termux-setup-storage
```

### Python no encontrado

```bash
# Reinstalar Python
pkg install python --reinstall
```

### El Worker se detiene al cerrar Termux

Usa el método de servicio en segundo plano (Paso 4 - Ejecución como Servicio) o nohup.

## Configuración Avanzada

### Cambiar el Token de Seguridad

Edita `config.py` en tu dispositivo:

```bash
nano ~/PensamientoCoral/config.py
```

Cambia el valor de `SECRET_TOKEN` y asegúrate de usar el mismo en el Master.

### Cambiar Puertos

Si los puertos predeterminados están en uso, edita `config.py`:

```python
UDP_BROADCAST_PORT = 54321  # Cambiar si es necesario
TCP_COMMAND_PORT = 54322   # Cambiar si es necesario
```

## Inicio Automático al Arrancar

Para que el Worker se inicie automáticamente al encender el dispositivo:

1. Instala Termux:Boot desde F-Droid
2. Crea el script de inicio:
   ```bash
   mkdir -p ~/.termux/boot
   cat > ~/.termux/boot/worker << 'EOF'
   #!/data/data/com.termux/files/usr/bin/sh
   cd ~/PensamientoCoral
   python Worker.py
   EOF
   chmod +x ~/.termux/boot/worker
   ```

## Rendimiento y Optimización

### Monitorear uso de recursos

```bash
# Ver uso de CPU
top

# Ver uso de memoria
free -h
```

### Limitar uso de CPU (si el dispositivo se sobrecalienta)

Puedes usar `cpulimit` para limitar el uso de CPU:

```bash
pkg install cpulimit
cpulimit -l 50 -p $(pgrep -f Worker.py)
```

Esto limita el Worker a usar máximo 50% de CPU.

## Seguridad

### Usar VPN para redes remotas

Si necesitas conectar workers desde redes diferentes:

1. Configura un servidor VPN (WireGuard, OpenVPN)
2. Conecta tanto el Master como los Workers a la VPN
3. Usa las IPs de la VPN para la comunicación

### Firewall de Android

Algunos dispositivos Android tienen firewalls que pueden bloquear conexiones. Asegúrate de permitir conexiones entrantes/salientes para Termux.

## Actualización del Worker

Para actualizar el Worker a una nueva versión:

```bash
cd ~/PensamientoCoral
git pull  # Si usas git
# O copia manualmente los nuevos archivos

# Reiniciar el servicio
sv restart worker
# O si usas nohup:
pkill -f Worker.py
nohup python Worker.py > worker.log 2>&1 &
```
