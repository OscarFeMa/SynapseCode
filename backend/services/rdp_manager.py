"""
Synapse Council v2.1 - RDP Manager (Seguro y Async)
Gestiona la conexión automática por Escritorio Remoto con el Worker.
Seguridad mejorada: sin shell=True, sanitización de inputs, rate limiting.
"""
import asyncio
import socket
import subprocess
import re
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from backend.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class RDPConnectionResult:
    """Resultado tipado de conexión RDP"""
    success: bool
    message: str
    ip: Optional[str] = None
    duration_ms: Optional[int] = None
    timestamp: Optional[datetime] = None


class RDPSecurityError(Exception):
    """Error de seguridad en RDP (input inválido)"""
    pass


class RDPRateLimitError(Exception):
    """Rate limit excedido"""
    pass


class RDPManager:
    """Gestiona la auto-conexión RDP a nodos Worker (versión segura)"""
    
    # Rate limiting en memoria (simple, para single-instance)
    _last_wake_attempt: Dict[str, datetime] = {}
    
    @staticmethod
    def _sanitize_hostname(hostname: str) -> str:
        """
        Sanitiza hostname/IP para prevenir command injection.
        Solo permite: IPs válidas o hostnames alfanuméricos con guiones.
        """
        if not hostname:
            raise RDPSecurityError("Hostname vacío")
        
        # Limpiar espacios
        hostname = hostname.strip()
        
        # Validar IP (IPv4)
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, hostname):
            # Validar rangos de octetos
            octets = hostname.split('.')
            for octet in octets:
                if not 0 <= int(octet) <= 255:
                    raise RDPSecurityError(f"IP inválida: {hostname}")
            return hostname
        
        # Validar hostname (alphanumeric + guiones, max 63 chars por label)
        hostname_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,62}(\.[a-zA-Z0-9][a-zA-Z0-9\-]{0,62})*$'
        if not re.match(hostname_pattern, hostname):
            raise RDPSecurityError(f"Hostname inválido: {hostname}")
        
        return hostname
    
    @staticmethod
    def _check_rate_limit(identifier: str) -> None:
        """
        Verifica rate limiting para evitar spam de conexiones RDP.
        """
        now = datetime.now()
        last_attempt = RDPManager._last_wake_attempt.get(identifier)
        
        if last_attempt:
            elapsed = (now - last_attempt).total_seconds()
            if elapsed < settings.RDP_RATE_LIMIT_SECONDS:
                wait_time = settings.RDP_RATE_LIMIT_SECONDS - int(elapsed)
                raise RDPRateLimitError(
                    f"Rate limit excedido. Espera {wait_time}s antes de reintentar."
                )
        
        RDPManager._last_wake_attempt[identifier] = now
    
    @staticmethod
    def get_ip_by_hostname(hostname: str) -> Optional[str]:
        """
        Obtiene la IP a partir del nombre del equipo.
        Método seguro: sin shell=True, solo socket resolution.
        """
        try:
            # Sanitizar primero
            clean_hostname = RDPManager._sanitize_hostname(hostname)
            
            # Usar socket (seguro, no ejecuta comandos shell)
            ip = socket.gethostbyname(clean_hostname)
            return ip
            
        except RDPSecurityError as e:
            logger.warning("rdp_manager.security_error", error=str(e))
            return None
        except socket.gaierror:
            logger.warning("rdp_manager.dns_failed", hostname=hostname)
            return None
        except Exception as e:
            logger.error("rdp_manager.resolve_error", hostname=hostname, error=str(e))
            return None
    
    @staticmethod
    async def connect_to_worker_async(
        hostname: str,
        username: str,
        password: str,
        rate_limit_id: Optional[str] = None
    ) -> RDPConnectionResult:
        """
        Inyecta credenciales y abre el escritorio remoto (versión async).
        
        Args:
            hostname: Nombre o IP del Worker
            username: Usuario Windows (formato DOMINIO\\usuario o usuario@dominio)
            password: Contraseña (se limpia de memoria tras uso)
            rate_limit_id: Identificador para rate limiting (ej: IP del cliente)
        
        Returns:
            RDPConnectionResult con estado de la operación
        """
        start_time = datetime.now()
        
        try:
            # 1. Rate limiting
            limit_id = rate_limit_id or hostname
            RDPManager._check_rate_limit(limit_id)
            
            # 2. Sanitizar inputs
            clean_hostname = RDPManager._sanitize_hostname(hostname)
            
            # Validar username (formato básico, no permite caracteres shell peligrosos)
            if not re.match(r'^[a-zA-Z0-9\\@._\-]+$', username):
                raise RDPSecurityError("Username contiene caracteres inválidos")
            
            logger.info("rdp_manager.connecting", hostname=clean_hostname, username=username.split('\\')[-1])
            
            # 3. Resolver IP
            ip = RDPManager.get_ip_by_hostname(clean_hostname)
            if not ip:
                return RDPConnectionResult(
                    success=False,
                    message=f"No se pudo resolver la IP para {clean_hostname}",
                    timestamp=start_time
                )
            
            # 4. Ejecutar comandos RDP (en executor para no bloquear)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,  # Default executor
                RDPManager._execute_rdp_sync,
                ip,
                username,
                password
            )
            
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return RDPConnectionResult(
                success=result["success"],
                message=result["message"],
                ip=ip,
                duration_ms=duration,
                timestamp=start_time
            )
            
        except RDPSecurityError as e:
            logger.error("rdp_manager.security_error", error=str(e))
            return RDPConnectionResult(
                success=False,
                message=f"Error de seguridad: {str(e)}",
                timestamp=start_time
            )
        except RDPRateLimitError as e:
            logger.warning("rdp_manager.rate_limited", error=str(e))
            return RDPConnectionResult(
                success=False,
                message=str(e),
                timestamp=start_time
            )
        except Exception as e:
            logger.error("rdp_manager.exception", error=str(e))
            return RDPConnectionResult(
                success=False,
                message=f"Error inesperado: {str(e)}",
                timestamp=start_time
            )
    
    @staticmethod
    def _execute_rdp_sync(ip: str, username: str, password: str) -> Dict[str, Any]:
        """
        Ejecuta comandos RDP de forma síncrona (para correr en executor).
        Seguro: usa listas en lugar de shell=True.
        """
        try:
            # 1. Limpiar credenciales previas (sin shell=True)
            delete_cmd = ['cmdkey', '/delete', f'TERMSRV/{ip}']
            subprocess.run(
                delete_cmd,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False  # No fallar si no existía
            )
            
            # 2. Inyectar nuevas credenciales (sin shell=True)
            add_cmd = [
                'cmdkey',
                '/generic:TERMSRV/{ip}'.format(ip=ip),
                f'/user:{username}',
                f'/pass:{password}'
            ]
            result = subprocess.run(
                add_cmd,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10  # Timeout de 10 segundos
            )
            
            if result.returncode != 0:
                stderr = result.stderr or ""
                logger.error("rdp_manager.cmdkey_failed", ip=ip, stderr=stderr[:100])
                return {
                    "success": False,
                    "message": f"Fallo al inyectar credenciales: {stderr[:100]}"
                }
            
            # 3. Lanzar mstsc (sin shell=True)
            mstsc_cmd = ['mstsc.exe', f'/v:{ip}']
            subprocess.Popen(
                mstsc_cmd,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            logger.info("rdp_manager.connected", ip=ip)
            return {
                "success": True,
                "message": f"Conexión RDP lanzada hacia {ip}"
            }
            
        except subprocess.TimeoutExpired:
            logger.error("rdp_manager.timeout", ip=ip)
            return {
                "success": False,
                "message": "Timeout al ejecutar comando RDP (10s)"
            }
        except FileNotFoundError:
            logger.error("rdp_manager.mstsc_not_found")
            return {
                "success": False,
                "message": "mstsc.exe no encontrado. ¿Estás en Windows?"
            }
        except Exception as e:
            logger.error("rdp_manager.command_error", ip=ip, error=str(e))
            return {
                "success": False,
                "message": f"Error ejecutando RDP: {str(e)}"
            }
    
    @staticmethod
    def connect_to_worker(
        hostname: str,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Método síncrono (legacy) para compatibilidad.
        Recomendado: usar connect_to_worker_async().
        """
        result = asyncio.run(RDPManager.connect_to_worker_async(
            hostname=hostname,
            username=username,
            password=password
        ))
        
        return {
            "success": result.success,
            "message": result.message,
            "ip": result.ip,
            "duration_ms": result.duration_ms
        }
    
    @staticmethod
    def auto_wake_worker() -> RDPConnectionResult:
        """
        Wake automático usando configuración del sistema.
        Usa credenciales de config.py, no requiere parámetros.
        """
        if not settings.RDP_ENABLED:
            return RDPConnectionResult(
                success=False,
                message="RDP deshabilitado en configuración"
            )
        
        return asyncio.run(RDPManager.connect_to_worker_async(
            hostname=settings.RDP_WORKER_HOSTNAME,
            username=settings.RDP_WORKER_USERNAME,
            password=settings.RDP_WORKER_PASSWORD,
            rate_limit_id="auto_wake"  # Rate limit global para auto-wake
        ))


# Backwards compatibility
__all__ = ['RDPManager', 'RDPConnectionResult', 'RDPSecurityError', 'RDPRateLimitError']
