# Instalar servidor web SynapseCode en Linux Mint

## Requisitos

- Linux Mint (cualquier versión reciente)
- Conexión a internet
- Conocimientos básicos de terminal
- **IMPORTANTE:** Este PC actuará como servidor 24/7, la tapa irá cerrada

---

## Paso 0: Configurar cierre de tapa (ANTES DE NADA)

Por defecto Linux Mint suspende el portátil al cerrar la tapa. Hay que evitarlo:

```bash
sudo sed -i 's/^#HandleLidSwitchExternalPower=.*/HandleLidSwitchExternalPower=ignore/' /etc/systemd/logind.conf 2>/dev/null || true
sudo sed -i 's/^#HandleLidSwitch=.*/HandleLidSwitch=ignore/' /etc/systemd/logind.conf 2>/dev/null || true
if ! grep -q "^HandleLidSwitchExternalPower=ignore" /etc/systemd/logind.conf; then
    echo "HandleLidSwitchExternalPower=ignore" | sudo tee -a /etc/systemd/logind.conf > /dev/null
fi
if ! grep -q "^HandleLidSwitch=ignore" /etc/systemd/logind.conf; then
    echo "HandleLidSwitch=ignore" | sudo tee -a /etc/systemd/logind.conf > /dev/null
fi
sudo systemctl restart systemd-logind
```

Esto hace que cerrar la tapa **NO** suspenda el equipo.
- Conecta el cargador antes de cerrar la tapa
- Si quieres apagarlo, usa `sudo shutdown -h now` o el botón de apagado desde el menú
- La pantalla se apagará al cerrar la tapa, pero el sistema sigue funcionando

> **NOTA:** También desactiva la suspensión automática por inactividad.
> En el menú de Linux Mint: `Menú → Preferencias → Gestor de energía`
> Pon "Suspender equipo cuando esté inactivo" a **Nunca** (tanto con batería como con AC).
> Alternativamente desde terminal:
> ```bash
> gsettings set org.cinnamon.settings-daemon.plugins.power sleep-display-ac 0
> gsettings set org.cinnamon.settings-daemon.plugins.power sleep-display-battery 0
> ```

Para comprobar que funcionó:

```bash
grep -E "HandleLidSwitch" /etc/systemd/logind.conf
```

Debe mostrar:
```
HandleLidSwitchExternalPower=ignore
HandleLidSwitch=ignore
```

---

## Paso 1: Abrir terminal

Presiona `Ctrl + Alt + T` o busca "Terminal" en el menú.

---

## Paso 2: Actualizar el sistema

```bash
sudo apt update && sudo apt upgrade -y
```

Esto actualiza la lista de paquetes e instala las últimas versiones. Te pedirá tu contraseña de usuario.

---

## Paso 3: Instalar nginx y herramientas

```bash
sudo apt install nginx curl unzip -y
```

- **nginx**: servidor web que servirá los archivos HTML
- **curl**: para descargar archivos desde internet
- **unzip**: para descomprimir el zip de GitHub

---

## Paso 4: Crear carpeta para la web

```bash
sudo mkdir -p /var/www/synapsecode
```

---

## Paso 5: Descargar los archivos desde GitHub

```bash
cd /tmp
rm -rf SynapseCode-main
curl -L -o SynapseCode.zip https://github.com/OscarFeMa/SynapseCode/archive/refs/heads/main.zip
unzip -o SynapseCode.zip
sudo cp -r SynapseCode-main/frontend/web/* /var/www/synapsecode/
```

### Explicación:
1. `cd /tmp` — vamos a la carpeta temporal
2. `rm -rf SynapseCode-main` — limpia descargas anteriores (por si acaso)
3. `curl` — descarga el último código desde GitHub
4. `unzip` — descomprime el archivo
5. `cp` — copia los archivos de la web a la carpeta definitiva

---

## Paso 6: Dar permisos

```bash
sudo chown -R www-data:www-data /var/www/synapsecode
sudo chmod -R 755 /var/www/synapsecode
```

Esto asegura que nginx pueda leer los archivos.

---

## Paso 7: Configurar nginx

Creamos el archivo de configuración:

```bash
sudo nano /etc/nginx/sites-available/synapsecode
```

Se abrirá un editor azul. **Borra todo lo que aparezca** y pega exactamente esto:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name _;

    root /var/www/synapsecode;
    index index.html;

    # Servir archivos estáticos
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Redirigir /admin a admin.html
    location /admin {
        alias /var/www/synapsecode;
        try_files /admin.html =404;
    }

    # Proxy inverso hacia el Master (cuando esté encendido)
    location /api/ {
        proxy_pass http://192.168.1.100:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
        proxy_next_upstream error timeout invalid_header http_502 http_503 http_504;
        proxy_next_upstream_tries 1;
    }

    access_log /var/log/nginx/synapsecode_access.log;
    error_log  /var/log/nginx/synapsecode_error.log warn;
}
```

**⚠️ IMPORTANTE:** En la línea `proxy_pass http://192.168.1.100:8000;` debes cambiar `192.168.1.100` por la **IP real del PC Windows donde corre el Master**.

Para saber la IP del Master (Windows):
- Abre `cmd` en Windows
- Escribe `ipconfig`
- Busca `Dirección IPv4` (algo como `192.168.1.X`)

### Guardar en nano:
1. `Ctrl + O` (Letra O, no cero)
2. Presiona `Enter`
3. `Ctrl + X` para salir

---

## Paso 8: Activar el sitio

```bash
sudo ln -sf /etc/nginx/sites-available/synapsecode /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
```

Verificar que la configuración es correcta:

```bash
sudo nginx -t
```

Debería mostrar:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

Reiniciar nginx:

```bash
sudo systemctl restart nginx
```

---

## Paso 9: Abrir puerto en el firewall

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Si te dice que `ufw` no está activo, no pasa nada, el puerto 80 ya está abierto por defecto.

---

## Paso 10: PROBAR

Desde el mismo Linux Mint abre el navegador y visita:

```
http://localhost
```

Deberías ver la página principal de SynapseCode.

Desde otro ordenador en la misma red, usa la IP de Linux Mint:

```
http://IP_DE_LINUX_MINT
```

Para saber la IP de Linux Mint:

```bash
ip a | grep inet
```

Busca algo como `192.168.1.X`.

---

## Paso 11: Verificar que el proxy al Master funciona

Con el Master encendido en Windows, visita desde cualquier navegador:

```
http://IP_DE_LINUX_MINT/api/health
```

Si el Master está encendido, verás el JSON con el estado. Si está apagado, verás una página de error 502 — eso es normal y esperado.

---

## Cómo actualizar la web cuando haya cambios

Cuando modifiques archivos en Windows y los subas a GitHub, en Linux Mint ejecuta esto:

```bash
cd /tmp && rm -rf SynapseCode-main && curl -L -o SynapseCode.zip https://github.com/OscarFeMa/SynapseCode/archive/refs/heads/main.zip && unzip -o SynapseCode.zip && sudo cp -r SynapseCode-main/frontend/web/* /var/www/synapsecode/ && echo "✅ Web actualizada"
```

---

## (Opcional) HTTPS con Let's Encrypt

Solo si tienes un dominio apuntando a la IP de Linux Mint:

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tudominio.com
```

Sigue las instrucciones en pantalla.

---

## (Opcional) Auto-actualización cada 10 minutos

Para que Linux Mint descargue automáticamente los cambios cada 10 minutos:

```bash
crontab -e
```

Selecciona `nano` si te pregunta. Al final del archivo añade:

```cron
*/10 * * * * cd /tmp && rm -rf SynapseCode-main && curl -L -o SynapseCode.zip -s https://github.com/OscarFeMa/SynapseCode/archive/refs/heads/main.zip && unzip -qo SynapseCode.zip && sudo cp -r SynapseCode-main/frontend/web/* /var/www/synapsecode/
```

Guarda con `Ctrl + O`, `Enter`, `Ctrl + X`.

---

## Solución de problemas

### "No puedo acceder desde otro ordenador"
- Asegúrate de que ambos PCs estén en la **misma red**
- Desde Linux Mint ejecuta: `sudo systemctl status nginx`
- Verifica la IP con: `ip a | grep inet`

### "502 Bad Gateway" todo el tiempo
- El Master (Windows) está apagado o la IP es incorrecta
- Edita la IP: `sudo nano /etc/nginx/sites-available/synapsecode`
- Cambia `proxy_pass http://192.168.1.100:8000;` por la IP correcta
- Luego: `sudo nginx -t && sudo systemctl restart nginx`

### "403 Forbidden"
- Permisos incorrectos. Ejecuta de nuevo el paso 6.

### "Archivos no actualizados"
- Ejecuta manualmente el comando del paso "Cómo actualizar la web"
