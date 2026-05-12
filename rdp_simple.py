#!/usr/bin/env python3
"""
RDP Simple - Conectar directamente al Worker
Resuelve makederpc → IP y abre RDP con credenciales preconfiguradas
"""
import socket
import subprocess
import sys
import time

def resolve_worker_ip(hostname="makederpc"):
    """Resuelve IP del Worker por hostname"""
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        return None

def connect_rdp(ip, username="MAKEDER\\maked", password="DNIcxwcaqza4"):
    """Conecta vía RDP usando mstsc.exe con credenciales automáticas"""
    try:
        # 1. Guardar credenciales en Windows Credential Manager
        cmdkey_cmd = [
            'cmdkey', 
            '/generic:TERMSRV/' + ip,
            '/user:' + username,
            '/pass:' + password
        ]
        
        result = subprocess.run(cmdkey_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️  Advertencia guardando credenciales: {result.stderr}")
        
        # 2. Crear archivo .rdp temporal sin pedir credenciales
        rdp_content = f"""full address:s:{ip}
username:s:{username}
domain:s:MAKEDER
screen mode id:i:2
use multimon:i:1
session bpp:i:32
authentication level:i:2
prompt for credentials:i:0
redirectdrives:i:1
redirectprinters:i:1
redirectclipboard:i:1
"""
        
        rdp_file = f"temp_worker_{ip.replace('.', '_')}.rdp"
        with open(rdp_file, 'w') as f:
            f.write(rdp_content)
        
        # 3. Abrir RDP con credenciales guardadas
        mstsc_cmd = ['mstsc', rdp_file]
        subprocess.Popen(mstsc_cmd)
        
        print(f"✅ RDP iniciado hacia {ip}")
        print(f"🔐 Credenciales inyectadas automáticamente")
        print(f"📁 Archivo RDP: {rdp_file}")
        
        # 4. Programar limpieza de credenciales (opcional)
        # Las credenciales se limpiarán manualmente si es necesario
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def cleanup_credentials(ip):
    """Limpia las credenciales guardadas"""
    try:
        cleanup_cmd = ['cmdkey', '/delete:TERMSRV/' + ip]
        result = subprocess.run(cleanup_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Credenciales eliminadas para {ip}")
        else:
            print(f"⚠️  No se encontraron credenciales para {ip}")
        return True
    except Exception as e:
        print(f"❌ Error limpiando credenciales: {e}")
        return False

def main():
    print("🖥️  RDP Simple - Conectar al Worker")
    print("=" * 40)
    
    # 1. Resolver IP
    print("📡 Resolviendo IP de makederpc...")
    ip = resolve_worker_ip()
    
    if not ip:
        print("❌ No se pudo resolver makederpc")
        input("Presiona ENTER para salir...")
        return
    
    print(f"✅ IP encontrada: {ip}")
    
    # 2. Conectar RDP
    print("🔐 Conectando vía RDP...")
    if connect_rdp(ip):
        print("✅ Conexión RDP iniciada")
        print("🖼️  Deberías ver la ventana de Escritorio Remoto")
        print("\n📋 Opciones:")
        print("1. Esperar a que se cierre la conexión")
        print("2. Limpiar credenciales ahora")
        
        choice = input("\nSelecciona opción (1/2): ").strip()
        if choice == "2":
            cleanup_credentials(ip)
    else:
        print("❌ Falló la conexión RDP")
    
    input("\nPresiona ENTER para salir...")

if __name__ == "__main__":
    main()
