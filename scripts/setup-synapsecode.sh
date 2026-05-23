#!/bin/bash
set -e

# ============================================================
#  INSTALADOR AUTOMÁTICO — SynapseCode Web Server en Linux Mint
#  Modo de uso:
#    chmod +x setup-synapsecode.sh
#    ./setup-synapsecode.sh
# ============================================================

ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
SIN_COLOR='\033[0m'

info()  { echo -e "${AZUL}[INFO]${SIN_COLOR} $1"; }
ok()    { echo -e "${VERDE}[OK]${SIN_COLOR} $1"; }
warn()  { echo -e "${AMARILLO}[AVISO]${SIN_COLOR} $1"; }
error() { echo -e "${ROJO}[ERROR]${SIN_COLOR} $1"; }

# ── Comprobar que se ejecuta como usuario normal (no root) ──
if [ "$EUID" -eq 0 ]; then
    error "NO ejecutes este script como root. Ejecútalo como tu usuario normal."
    error "El script ya usa sudo cuando es necesario."
    exit 1
fi

clear
echo "========================================================"
echo "  INSTALADOR SynapseCode — Servidor Web para Linux Mint"
echo "========================================================"
echo ""

# ── Bienvenida ──
echo "Este script va a:"
echo "  1. Configurar el cierre de tapa (no suspender)"
echo "  2. Actualizar el sistema"
echo "  3. Instalar nginx + curl + unzip"
echo "  4. Descargar la web desde GitHub"
echo "  5. Configurar nginx con proxy al Master"
echo "  6. Dejar el servidor funcionando"
echo ""
echo "Todo automático, solo te preguntará la IP del Master."
echo ""

read -p "¿Quieres continuar? (s/N): " confirm
if [ "$confirm" != "s" ] && [ "$confirm" != "S" ]; then
    echo "Instalación cancelada."
    exit 0
fi

# ══════════════════════════════════════════════════════════════
#  PASO 0 — EVITAR SUSPENSIÓN AL CERRAR LA TAPA
# ══════════════════════════════════════════════════════════════
echo ""
info "[Paso 0/8] Configurando cierre de tapa..."

sudo sed -i 's/^#HandleLidSwitchExternalPower=.*/HandleLidSwitchExternalPower=ignore/' /etc/systemd/logind.conf 2>/dev/null || true
sudo sed -i 's/^#HandleLidSwitch=.*/HandleLidSwitch=ignore/' /etc/systemd/logind.conf 2>/dev/null || true

if ! grep -q "^HandleLidSwitchExternalPower=ignore" /etc/systemd/logind.conf 2>/dev/null; then
    echo "HandleLidSwitchExternalPower=ignore" | sudo tee -a /etc/systemd/logind.conf > /dev/null
fi
if ! grep -q "^HandleLidSwitch=ignore" /etc/systemd/logind.conf 2>/dev/null; then
    echo "HandleLidSwitch=ignore" | sudo tee -a /etc/systemd/logind.conf > /dev/null
fi

sudo systemctl restart systemd-logind

# También evitar suspensión por inactividad (Cinnamon)
gsettings set org.cinnamon.settings-daemon.plugins.power sleep-display-ac 0 2>/dev/null || true
gsettings set org.cinnamon.settings-daemon.plugins.power sleep-display-battery 0 2>/dev/null || true
gsettings set org.cinnamon.settings-daemon.plugins.power sleep-inactive-ac-timeout 0 2>/dev/null || true
gsettings set org.cinnamon.settings-daemon.plugins.power sleep-inactive-battery-timeout 0 2>/dev/null || true

ok "Cierre de tapa configurado. Ya puedes cerrarla sin que se apague."

# ══════════════════════════════════════════════════════════════
#  PASO 1 — ACTUALIZAR SISTEMA
# ══════════════════════════════════════════════════════════════
echo ""
info "[Paso 1/8] Actualizando el sistema (puede tardar)..."
sudo apt update -qq && sudo apt upgrade -y -qq
ok "Sistema actualizado."

# ══════════════════════════════════════════════════════════════
#  PASO 2 — INSTALAR DEPENDENCIAS
# ══════════════════════════════════════════════════════════════
echo ""
info "[Paso 2/8] Instalando nginx, curl, unzip..."
sudo apt install -y -qq nginx curl unzip
ok "Dependencias instaladas."

# ══════════════════════════════════════════════════════════════
#  PASO 3 — CREAR CARPETA
# ══════════════════════════════════════════════════════════════
echo ""
info "[Paso 3/8] Creando carpeta /var/www/synapsecode..."
sudo mkdir -p /var/www/synapsecode
ok "Carpeta creada."

# ══════════════════════════════════════════════════════════════
#  PASO 4 — DESCARGAR DESDE GITHUB
# ══════════════════════════════════════════════════════════════
echo ""
info "[Paso 4/8] Descargando web desde GitHub..."
cd /tmp
rm -rf SynapseCode-main SynapseCode.zip
curl -sL -o SynapseCode.zip https://github.com/OscarFeMa/SynapseCode/archive/refs/heads/main.zip
unzip -qo SynapseCode.zip
sudo cp -r SynapseCode-main/frontend/web/* /var/www/synapsecode/
sudo chown -R www-data:www-data /var/www/synapsecode
sudo chmod -R 755 /var/www/synapsecode
ok "Web descargada y copiada."

# ══════════════════════════════════════════════════════════════
#  PASO 5 — PEDIR IP DEL MASTER
# ══════════════════════════════════════════════════════════════
echo ""
info "[Paso 5/8] Configuración del proxy al Master (PC Windows)..."

# Detectar IP local para dar una pista
MI_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+' | grep -v '127.0.0.1' | head -1)
SUBRED=$(echo "$MI_IP" | cut -d. -f1-3)
echo "Tu IP en esta máquina es: $MI_IP"
echo "El Master suele estar en: ${SUBRED}.100 (por ejemplo)"
echo ""

read -p "Introduce la IP del Master (Windows): " MASTER_IP

if [ -z "$MASTER_IP" ]; then
    warn "No se introdujo IP. Usando 192.168.1.100 como placeholder."
    warn "Deberás editarlo después en /etc/nginx/sites-available/synapsecode"
    MASTER_IP="192.168.1.100"
fi

ok "Master configurado en: $MASTER_IP"

# ══════════════════════════════════════════════════════════════
#  PASO 6 — CONFIGURAR NGINX
# ══════════════════════════════════════════════════════════════
echo ""
info "[Paso 6/8] Creando configuración de nginx..."

sudo tee /etc/nginx/sites-available/synapsecode > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name _;

    root /var/www/synapsecode;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /admin {
        alias /var/www/synapsecode;
        try_files /admin.html =404;
    }

    location /api/ {
        proxy_pass http://${MASTER_IP}:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
        proxy_next_upstream error timeout invalid_header http_502 http_503 http_504;
        proxy_next_upstream_tries 1;
    }

    access_log /var/log/nginx/synapsecode_access.log;
    error_log  /var/log/nginx/synapsecode_error.log warn;
}
EOF

ok "Configuración creada."

# ══════════════════════════════════════════════════════════════
#  PASO 7 — ACTIVAR SITIO
# ══════════════════════════════════════════════════════════════
echo ""
info "[Paso 7/8] Activando sitio y reiniciando nginx..."

sudo ln -sf /etc/nginx/sites-available/synapsecode /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

if sudo nginx -t 2>&1 | grep -q "successful"; then
    sudo systemctl restart nginx
    ok "Nginx configurado y funcionando."
else
    error "La configuración de nginx tiene errores:"
    sudo nginx -t
    exit 1
fi

# ══════════════════════════════════════════════════════════════
#  PASO 8 — FIREWALL
# ══════════════════════════════════════════════════════════════
echo ""
info "[Paso 8/8] Abriendo puertos en firewall..."

sudo ufw allow 80/tcp 2>/dev/null || true
sudo ufw allow 443/tcp 2>/dev/null || true
ok "Puertos 80 y 443 abiertos."

# ══════════════════════════════════════════════════════════════
#  FINAL
# ══════════════════════════════════════════════════════════════
echo ""
echo "========================================================"
echo -e "${VERDE}  INSTALACIÓN COMPLETADA${SIN_COLOR}"
echo "========================================================"
echo ""
echo "  Web disponible en:"
echo "    http://localhost         (desde este PC)"
echo "    http://$MI_IP  (desde la red local)"
echo ""
echo "  Admin:"
echo "    http://$MI_IP/admin"
echo ""
echo "  Cuando el Master esté encendido:"
echo "    http://$MI_IP/api/health"
echo ""
echo "  Para actualizar la web tras cambios en GitHub:"
echo "    cd /tmp && rm -rf SynapseCode-main && curl -sL -o SynapseCode.zip https://github.com/OscarFeMa/SynapseCode/archive/refs/heads/main.zip && unzip -qo SynapseCode.zip && sudo cp -r SynapseCode-main/frontend/web/* /var/www/synapsecode/ && sudo chown -R www-data:www-data /var/www/synapsecode && echo OK"
echo ""
echo "  Para reiniciar nginx:"
echo "    sudo systemctl restart nginx"
echo ""
echo "  Para apagar este servidor:"
echo "    sudo shutdown -h now"
echo ""
echo "RECUERDA: Conecta el cargador ANTES de cerrar la tapa."
echo ""
echo "========================================================"
