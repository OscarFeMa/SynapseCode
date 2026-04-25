"""
Synapse Link Manager v1.0
Auto-configurador de arquitectura Master-Worker para Synapse Council
Detecta automáticamente el rol según servicios disponibles
"""
import os
import sys
import socket
import json
import time
import asyncio
import requests
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_status(msg: str, status: str = "info"):
    """Imprime mensajes con color"""
    if status == "success":
        print(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")
    elif status == "error":
        print(f"{Colors.FAIL}✗{Colors.ENDC} {msg}")
    elif status == "warning":
        print(f"{Colors.WARNING}⚠{Colors.ENDC} {msg}")
    elif status == "info":
        print(f"{Colors.OKBLUE}ℹ{Colors.ENDC} {msg}")
    elif status == "header":
        print(f"\n{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")

def get_local_ip() -> str:
    """Obtiene la IP local de forma robusta"""
    try:
        # Método 1: Conexión a DNS de Google
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            # Método 2: Hostname
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"

def check_local_engine(port: int, name: str) -> bool:
    """Verifica si un motor local está corriendo"""
    try:
        response = requests.get(f"http://localhost:{port}/api/tags" if port == 11434 
                               else f"http://localhost:{port}/v1/models", 
                               timeout=2)
        return response.status_code == 200
    except:
        return False

def detect_role() -> Tuple[str, Dict[str, bool]]:
    """
    Detecta automáticamente si este PC debe ser Master o Worker
    basado en qué motores locales están disponibles
    """
    print_status("Detectando motores locales...", "info")
    
    engines = {
        "ollama": check_local_engine(11434, "Ollama"),
        "lm_studio": check_local_engine(1234, "LM Studio"),
        "jan": check_local_engine(1337, "Jan.ai")
    }
    
    local_engines_count = sum(engines.values())
    
    print(f"  • Ollama (puerto 11434): {'✓ Running' if engines['ollama'] else '✗ Not found'}")
    print(f"  • LM Studio (puerto 1234): {'✓ Running' if engines['lm_studio'] else '✗ Not found'}")
    print(f"  • Jan.ai (puerto 1337): {'✓ Running' if engines['jan'] else '✗ Not found'}")
    
    if local_engines_count > 0:
        print_status(f"Detectados {local_engines_count} motores locales → Configurando como WORKER", "success")
        return "WORKER", engines
    else:
        print_status("No se detectaron motores locales → Configurando como MASTER", "warning")
        print("  (El Master usa OpenRouter/Web Agent y delega motores locales al Worker)")
        return "MASTER", engines

def configure_env_file(project_path: Path, role: str, worker_ip: Optional[str] = None, 
                       local_engines: Optional[Dict[str, bool]] = None) -> bool:
    """Configura el archivo .env según el rol detectado"""
    
    env_path = project_path / ".env"
    env_example_path = project_path / ".env.example"
    
    print_status(f"Configurando {env_path} como {role}...", "info")
    
    # Configuraciones base según rol
    if role == "MASTER":
        config = f"""# Auto-configurado por Synapse Link Manager
NODE_ROLE=MASTER
PORT=8000
HOST=0.0.0.0

# --- Worker Configuration ---
# IP del Worker (se actualizará automáticamente vía discovery)
WORKER_HOST={worker_ip or ""}
WORKER_OLLAMA_PORT=11434
WORKER_LM_STUDIO_PORT=1234
WORKER_JAN_PORT=1337

# --- API Keys (rellenar si se tienen) ---
# OPENROUTER_API_KEY=tu_api_key_aqui

# --- Supabase (Opcional, para elevación a nube) ---
# SUPABASE_URL=tu_url
# SUPABASE_ANON_KEY=tu_key

# --- Features del Master ---
WEB_AGENT_ENABLED=true
MAX_CONCURRENT_SESSIONS=3
DISCOVERY_PORT=54321
DISCOVERY_INTERVAL=5
"""
    else:  # WORKER
        # El Worker desactiva OpenRouter y Web Agent
        config = f"""# Auto-configurado por Synapse Link Manager
NODE_ROLE=WORKER
PORT=8001
HOST=0.0.0.0

# --- Puertos de los Motores Locales ---
WORKER_OLLAMA_PORT=11434
WORKER_LM_STUDIO_PORT=1234
WORKER_JAN_PORT=1337

# --- Configuración de Features ---
# El Worker no usa estos servicios (se desactivan)
SUPABASE_ENABLED=false
WEB_AGENT_ENABLED=false
OPENROUTER_API_KEY=

# --- Discovery P2P ---
DISCOVERY_PORT=54321
DISCOVERY_INTERVAL=5

# --- Motores disponibles en este Worker ---
# OLLAMA_AVAILABLE={'true' if local_engines and local_engines.get('ollama') else 'false'}
# LM_STUDIO_AVAILABLE={'true' if local_engines and local_engines.get('lm_studio') else 'false'}
# JAN_AVAILABLE={'true' if local_engines and local_engines.get('jan') else 'false'}
"""
    
    try:
        # Backup del .env anterior si existe
        if env_path.exists():
            backup_path = project_path / ".env.backup"
            with open(env_path, 'r') as f:
                old_content = f.read()
            with open(backup_path, 'w') as f:
                f.write(old_content)
            print(f"  Backup creado: {backup_path}")
        
        # Escribir nueva configuración
        with open(env_path, 'w') as f:
            f.write(config)
        
        print_status(f"Archivo .env configurado correctamente", "success")
        return True
        
    except Exception as e:
        print_status(f"Error al configurar .env: {e}", "error")
        return False

class UDPDiscoveryTest:
    """Test de descubrimiento UDP entre Master y Worker"""
    
    def __init__(self, port: int = 54321):
        self.port = port
        self.peers_found = []
        
    async def send_beacon(self, role: str):
        """Envía beacons UDP broadcast"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.1)
        
        message = json.dumps({
            "node_id": f"test-{role}-{int(time.time())}",
            "role": role,
            "port": 8000 if role == "MASTER" else 8001,
            "ip": get_local_ip()
        }).encode('utf-8')
        
        try:
            while True:
                sock.sendto(message, ('<broadcast>', self.port))
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            sock.close()
            
    async def listen_for_peers(self, duration: int = 10):
        """Escucha beacons durante X segundos"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind(('', self.port))
        except OSError as e:
            print_status(f"No se puede escuchar en puerto {self.port}: {e}", "error")
            return []
        
        sock.settimeout(2.0)
        start_time = time.time()
        
        print(f"Escuchando beacons durante {duration} segundos...")
        
        while time.time() - start_time < duration:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                peer_role = message.get("role")
                peer_ip = addr[0]
                
                if peer_role and peer_ip != get_local_ip():
                    peer_info = {
                        "role": peer_role,
                        "ip": peer_ip,
                        "node_id": message.get("node_id")
                    }
                    if peer_info not in self.peers_found:
                        self.peers_found.append(peer_info)
                        print_status(f"Peer descubierto: {peer_role} en {peer_ip}", "success")
                        
            except socket.timeout:
                continue
            except json.JSONDecodeError:
                continue
                
        sock.close()
        return self.peers_found

def test_http_connection(ip: str, port: int) -> bool:
    """Test de conexión HTTP al otro nodo"""
    try:
        response = requests.get(f"http://{ip}:{port}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Flujo principal de configuración"""
    print_status("╔════════════════════════════════════════════════╗", "header")
    print_status("║     SYNAPSE LINK MANAGER v1.0               ║", "header")
    print_status("║  Auto-configuración Master-Worker           ║", "header")
    print_status("╚════════════════════════════════════════════════╝", "header")
    
    # Detectar IP local
    local_ip = get_local_ip()
    print(f"\nIP Local detectada: {Colors.BOLD}{local_ip}{Colors.ENDC}")
    
    # Detectar rol automáticamente
    role, local_engines = detect_role()
    
    # Determinar path del proyecto
    script_dir = Path(__file__).parent.parent
    project_path = script_dir.absolute()
    
    print(f"\nProyecto: {project_path}")
    
    # Configurar .env
    if configure_env_file(project_path, role, local_engines=local_engines):
        print_status("Configuración completada", "success")
    else:
        print_status("Error en configuración", "error")
        sys.exit(1)
    
    # Test de descubrimiento UDP
    print_status("\n--- Test de Descubrimiento UDP ---", "header")
    print("Buscando otros nodos Synapse en la red local...")
    
    discovery = UDPDiscoveryTest()
    
    async def run_discovery_test():
        # Iniciar beacon propio
        beacon_task = asyncio.create_task(discovery.send_beacon(role))
        
        # Escuchar peers
        peers = await discovery.listen_for_peers(duration=10)
        
        # Cancelar beacon
        beacon_task.cancel()
        try:
            await beacon_task
        except asyncio.CancelledError:
            pass
            
        return peers
    
    try:
        peers = asyncio.run(run_discovery_test())
        
        if peers:
            print(f"\n{Colors.OKGREEN}✓ Se encontraron {len(peers)} peer(s):{Colors.ENDC}")
            for peer in peers:
                print(f"  • {peer['role']}: {peer['ip']}")
                
                # Test HTTP
                peer_port = 8000 if peer['role'] == "MASTER" else 8001
                if test_http_connection(peer['ip'], peer_port):
                    print(f"    {Colors.OKGREEN}✓ Conexión HTTP exitosa{Colors.ENDC}")
                else:
                    print(f"    {Colors.FAIL}✗ No responde HTTP en puerto {peer_port}{Colors.ENDC}")
        else:
            print(f"\n{Colors.WARNING}⚠ No se detectaron otros nodos{Colors.ENDC}")
            print("  Asegúrate de que:")
            print("    1. El otro PC tenga Synapse Council corriendo")
            print("    2. Ambos estén en la misma red local")
            print("    3. El firewall permita tráfico UDP puerto 54321")
    except Exception as e:
        print_status(f"Error en test de descubrimiento: {e}", "error")
    
    # Resumen final
    print_status("\n--- Resumen de Configuración ---", "header")
    print(f"Rol asignado: {Colors.BOLD}{role}{Colors.ENDC}")
    print(f"Puerto: {8000 if role == 'MASTER' else 8001}")
    print(f"IP Local: {local_ip}")
    print(f"\n{Colors.OKCYAN}Para iniciar:{Colors.ENDC}")
    print(f"  cd {project_path}")
    print(f"  python backend/main.py")
    
    if role == "MASTER":
        print(f"\n{Colors.WARNING}Nota:{Colors.ENDC} El Master usará motores remotos del Worker.")
        print(f"      Asegúrate de que el Worker esté corriendo primero.")

if __name__ == "__main__":
    main()
