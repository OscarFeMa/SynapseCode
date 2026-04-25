"""
Synapse Network Diagnostic Tool v1.0
Diagnóstico completo de conectividad Master-Worker
Uso: python network_diagnostic.py [--target IP] [--port PORT]
"""
import os
import sys
import socket
import json
import time
import asyncio
import argparse
import requests
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title: str):
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD} {title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

def print_item(label: str, value: str, status: str = "info"):
    if status == "success":
        status_icon = f"{Colors.GREEN}✓{Colors.ENDC}"
    elif status == "error":
        status_icon = f"{Colors.FAIL}✗{Colors.ENDC}"
    elif status == "warning":
        status_icon = f"{Colors.WARNING}⚠{Colors.ENDC}"
    else:
        status_icon = f"{Colors.BLUE}ℹ{Colors.ENDC}"
    print(f"{status_icon} {label}: {Colors.BOLD}{value}{Colors.ENDC}")

class NetworkDiagnostic:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "local_ip": None,
            "hostname": socket.gethostname(),
            "tests": {}
        }
    
    def get_local_ip(self) -> str:
        """Obtiene IP local de forma robusta"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            try:
                return socket.gethostbyname(socket.gethostname())
            except:
                return "127.0.0.1"
    
    def test_local_engines(self) -> Dict[str, Any]:
        """Testea motores locales"""
        print_section("TEST 1: Motores Locales")
        
        engines = {
            "Ollama": {"port": 11434, "endpoint": "/api/tags"},
            "LM Studio": {"port": 1234, "endpoint": "/v1/models"},
            "Jan.ai": {"port": 1337, "endpoint": "/v1/models"}
        }
        
        results = {}
        for name, config in engines.items():
            try:
                url = f"http://localhost:{config['port']}{config['endpoint']}"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    models = len(data.get("models", [])) if "models" in data else "N/A"
                    print_item(name, f"Online ({models} modelos)", "success")
                    results[name] = {"status": "online", "models": models}
                else:
                    print_item(name, f"Error HTTP {response.status_code}", "error")
                    results[name] = {"status": "error", "code": response.status_code}
            except requests.exceptions.ConnectionError:
                print_item(name, "Offline (no responde)", "warning")
                results[name] = {"status": "offline"}
            except Exception as e:
                print_item(name, f"Error: {str(e)[:30]}", "error")
                results[name] = {"status": "error", "error": str(e)}
        
        return results
    
    def test_udp_discovery(self, duration: int = 5) -> List[Dict]:
        """Test de descubrimiento UDP"""
        print_section("TEST 2: Descubrimiento UDP (P2P)")
        
        discovery_port = 54321
        peers_found = []
        
        # Crear socket de escucha
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind(('', discovery_port))
            print_item("Socket UDP", f"Escuchando en puerto {discovery_port}", "success")
        except OSError as e:
            print_item("Socket UDP", f"Error al bindear: {e}", "error")
            print(f"\n{Colors.WARNING}Sugerencia: Verifica que el puerto {discovery_port} no esté en uso{Colors.ENDC}")
            return []
        
        sock.settimeout(2.0)
        
        # Enviar beacon propio
        beacon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        beacon_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        message = json.dumps({
            "node_id": f"diagnostic-{int(time.time())}",
            "role": "DIAGNOSTIC",
            "port": 9999,
            "timestamp": datetime.now().isoformat()
        }).encode('utf-8')
        
        beacon_sock.sendto(message, ('<broadcast>', discovery_port))
        print_item("Beacon enviado", "Broadcast en red local", "info")
        
        # Escuchar respuestas
        start_time = time.time()
        print(f"\nEscuchando durante {duration} segundos...")
        
        while time.time() - start_time < duration:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                
                peer_ip = addr[0]
                peer_role = message.get("role", "UNKNOWN")
                
                # Ignorar nuestro propio beacon
                if message.get("node_id", "").startswith("diagnostic-"):
                    continue
                
                peer_info = {
                    "ip": peer_ip,
                    "role": peer_role,
                    "node_id": message.get("node_id"),
                    "port": message.get("port")
                }
                
                if peer_info not in peers_found:
                    peers_found.append(peer_info)
                    print_item(f"Peer encontrado", f"{peer_role} en {peer_ip}:{message.get('port')}", "success")
                    
            except socket.timeout:
                continue
            except json.JSONDecodeError:
                continue
        
        sock.close()
        beacon_sock.close()
        
        if not peers_found:
            print_item("Resultado", "No se detectaron otros nodos", "warning")
            print(f"\n{Colors.WARNING}Posibles causas:{Colors.ENDC}")
            print("  • El otro PC no tiene Synapse corriendo")
            print("  • Ambos PCs no están en la misma red/subred")
            print("  • Firewall bloqueando UDP puerto 54321")
            print("  • Router bloqueando broadcast")
        
        return peers_found
    
    def test_http_endpoint(self, target_ip: str, port: int = 8000) -> Dict[str, Any]:
        """Test de endpoint HTTP"""
        print_section(f"TEST 3: Conexión HTTP a {target_ip}:{port}")
        
        results = {}
        
        # Test endpoint raíz
        try:
            url = f"http://{target_ip}:{port}/"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print_item("Endpoint /", "OK", "success")
                print(f"   Respuesta: {json.dumps(data, indent=2)[:200]}")
                results["root"] = {"status": "ok", "data": data}
            else:
                print_item("Endpoint /", f"HTTP {response.status_code}", "error")
                results["root"] = {"status": "error", "code": response.status_code}
        except requests.exceptions.ConnectionError:
            print_item("Endpoint /", "No se puede conectar", "error")
            results["root"] = {"status": "connection_refused"}
        except Exception as e:
            print_item("Endpoint /", f"Error: {str(e)[:50]}", "error")
            results["root"] = {"status": "error", "error": str(e)}
        
        # Test health check
        try:
            url = f"http://{target_ip}:{port}/health"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print_item("Health Check", f"OK - Status: {data.get('status', 'unknown')}", "success")
                results["health"] = {"status": "ok", "data": data}
            else:
                print_item("Health Check", f"HTTP {response.status_code}", "error")
                results["health"] = {"status": "error", "code": response.status_code}
        except Exception as e:
            print_item("Health Check", f"Error: {str(e)[:50]}", "error")
            results["health"] = {"status": "error", "error": str(e)}
        
        # Test peers endpoint (si existe)
        try:
            url = f"http://{target_ip}:{port}/api/v1/network/peers"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                peers_count = data.get("total_peers", 0)
                print_item("Peers Endpoint", f"OK - {peers_count} peers conocidos", "success")
                results["peers"] = {"status": "ok", "peers": peers_count}
            else:
                print_item("Peers Endpoint", f"HTTP {response.status_code}", "warning")
                results["peers"] = {"status": "warning", "code": response.status_code}
        except Exception as e:
            print_item("Peers Endpoint", f"No disponible: {str(e)[:40]}", "warning")
            results["peers"] = {"status": "error", "error": str(e)}
        
        return results
    
    def test_firewall_windows(self):
        """Verifica reglas de firewall de Windows"""
        print_section("TEST 4: Firewall de Windows")
        
        ports_to_check = [8000, 8001, 54321]
        
        for port in ports_to_check:
            try:
                # Verificar si hay regla de entrada para este puerto
                result = subprocess.run(
                    ["netsh", "advfirewall", "firewall", "show", "rule", f"name=all"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output = result.stdout.lower()
                
                if str(port) in output:
                    print_item(f"Puerto {port}", "Regla de firewall detectada", "warning")
                else:
                    print_item(f"Puerto {port}", "Sin regla específica (puede estar bloqueado)", "warning")
                    
            except Exception as e:
                print_item(f"Puerto {port}", f"No se pudo verificar: {e}", "warning")
        
        print(f"\n{Colors.CYAN}Para abrir puertos en Windows:{Colors.ENDC}")
        print(f"  netsh advfirewall firewall add rule name=\"Synapse-{port}\" dir=in action=allow protocol=udp localport={port}")
    
    def test_latency(self, target_ip: str, count: int = 4) -> Dict[str, Any]:
        """Test de latencia con ping"""
        print_section(f"TEST 5: Latencia a {target_ip}")
        
        try:
            # Ping en Windows
            result = subprocess.run(
                ["ping", "-n", str(count), target_ip],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            
            # Parsear resultado
            if "TTL=" in output or "ttl=" in output:
                print_item("Ping", "Host responde", "success")
                
                # Extraer tiempos aproximados
                lines = output.split('\n')
                for line in lines:
                    if "tiempo=" in line or "time=" in line:
                        print(f"  {line.strip()}")
                
                return {"status": "ok", "output": output}
            else:
                print_item("Ping", "Host no responde a ping", "error")
                return {"status": "no_response"}
                
        except Exception as e:
            print_item("Ping", f"Error: {e}", "error")
            return {"status": "error", "error": str(e)}
    
    def run_all_tests(self, target_ip: Optional[str] = None):
        """Ejecuta todos los tests"""
        print_section("INICIANDO DIAGNÓSTICO DE RED")
        
        # Info básica
        self.results["local_ip"] = self.get_local_ip()
        print_item("IP Local", self.results["local_ip"], "info")
        print_item("Hostname", self.results["hostname"], "info")
        print_item("Timestamp", self.results["timestamp"], "info")
        
        # Test 1: Motores locales
        self.results["tests"]["local_engines"] = self.test_local_engines()
        
        # Test 2: UDP Discovery
        self.results["tests"]["udp_discovery"] = self.test_udp_discovery(duration=5)
        
        # Test 3: HTTP (si se proporcionó target)
        if target_ip:
            port = 8001 if "worker" in target_ip.lower() else 8000
            self.results["tests"]["http"] = self.test_http_endpoint(target_ip, port)
        
        # Test 4: Firewall
        self.test_firewall_windows()
        
        # Test 5: Latencia (si se proporcionó target)
        if target_ip:
            self.results["tests"]["latency"] = self.test_latency(target_ip)
        
        # Resumen
        print_section("RESUMEN DEL DIAGNÓSTICO")
        
        # Contar problemas
        issues = []
        
        # Verificar si hay motores locales
        engines = self.results["tests"].get("local_engines", {})
        if not any(e.get("status") == "online" for e in engines.values()):
            issues.append("No hay motores locales (Ollama/LM Studio) corriendo")
        
        # Verificar descubrimiento
        peers = self.results["tests"].get("udp_discovery", [])
        if not peers:
            issues.append("No se detectaron peers vía UDP (posible problema de red/firewall)")
        
        # Verificar conexión HTTP
        if target_ip:
            http_results = self.results["tests"].get("http", {})
            root_status = http_results.get("root", {}).get("status")
            if root_status != "ok":
                issues.append(f"No se pudo conectar vía HTTP a {target_ip}")
        
        if issues:
            print(f"{Colors.FAIL}⚠ Se detectaron {len(issues)} problema(s):{Colors.ENDC}")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        else:
            print(f"{Colors.GREEN}✓ No se detectaron problemas principales{Colors.ENDC}")
        
        print(f"\n{Colors.CYAN}Para guardar este reporte:{Colors.ENDC}")
        print(f"  python network_diagnostic.py > diagnostic_report.txt")

def main():
    parser = argparse.ArgumentParser(description="Diagnóstico de red Synapse Council")
    parser.add_argument("--target", "-t", help="IP del otro nodo para testear conexión HTTP")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Puerto del target (default: 8000)")
    
    args = parser.parse_args()
    
    diagnostic = NetworkDiagnostic()
    diagnostic.run_all_tests(target_ip=args.target)

if __name__ == "__main__":
    main()
