"""
Synapse Council v2.0 - RDP Manager
Gestiona la conexión automática por Escritorio Remoto con el Worker.
"""
import socket
import subprocess
import os
import structlog
from typing import Optional, Dict, Any

logger = structlog.get_logger()

class RDPManager:
    """Gestiona la auto-conexión RDP a nodos Worker"""
    
    @staticmethod
    def get_ip_by_hostname(hostname: str) -> Optional[str]:
        """Obtiene la IP a partir del nombre del equipo."""
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            try:
                # Fallback nativo
                output = subprocess.check_output(f"ping -n 1 -4 {hostname}", shell=True).decode(errors='ignore')
                for line in output.splitlines():
                    if " [" in line and "] " in line:
                        return line.split(" [")[1].split("] ")[0]
            except Exception:
                pass
        return None

    @staticmethod
    def connect_to_worker(hostname: str, username: str, password: str) -> Dict[str, Any]:
        """Inyecta credenciales y abre el escritorio remoto."""
        logger.info("rdp_manager.connecting", hostname=hostname, username=username)
        
        ip = RDPManager.get_ip_by_hostname(hostname)
        if not ip:
            logger.error("rdp_manager.resolve_failed", hostname=hostname)
            return {"success": False, "message": f"No se pudo resolver la IP para {hostname}"}
            
        target = ip
        
        try:
            # 1. Limpiar credenciales previas
            subprocess.run(f'cmdkey /delete:TERMSRV/{target}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 2. Inyectar nuevas credenciales
            cmdkey_cmd = f'cmdkey /generic:TERMSRV/{target} /user:"{username}" /pass:"{password}"'
            result = subprocess.run(cmdkey_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if result.returncode != 0:
                logger.error("rdp_manager.cmdkey_failed", target=target)
                return {"success": False, "message": "Fallo al inyectar las credenciales en Windows."}
            
            # 3. Lanzar mstsc
            subprocess.Popen(['mstsc.exe', f'/v:{target}'])
            
            logger.info("rdp_manager.connected", target=target)
            return {"success": True, "message": f"Conexión RDP lanzada hacia {target}"}
            
        except Exception as e:
            logger.error("rdp_manager.exception", error=str(e))
            return {"success": False, "message": f"Error inesperado: {str(e)}"}
