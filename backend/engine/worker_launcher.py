"""
WorkerServiceManager - Detección y lanzamiento remoto de servicios en Worker.
Verifica: Ollama (:11434), LM Studio (:1234/:1235), Jan (:1337).
Intenta lanzarlos vía WinRM, RDP + script, o alerta al usuario.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

from backend.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class WorkerService:
    """Representa un servicio en el Worker"""

    name: str
    port: int
    alt_ports: list[int] = field(default_factory=list)
    process_name: str = ""
    winrm_command: str = ""
    rdp_script: str = ""
    is_running: bool = False
    running_on_port: int | None = None


# Definición de servicios conocidos
SERVICES = {
    "ollama": WorkerService(
        name="Ollama",
        port=settings.WORKER_OLLAMA_PORT,
        process_name="ollama",
        winrm_command="ollama serve",
        rdp_script="start /B ollama serve",
    ),
    "lm_studio": WorkerService(
        name="LM Studio",
        port=settings.WORKER_LM_STUDIO_PORT,
        alt_ports=[1235],
        process_name="LM Studio",
        winrm_command=('start "" "C:\\Users\\maked\\AppData\\Local\\LM Studio\\LM Studio.exe"'),
        rdp_script=('start "" "C:\\Users\\maked\\AppData\\Local\\LM Studio\\LM Studio.exe"'),
    ),
    "jan": WorkerService(
        name="Jan",
        port=settings.WORKER_JAN_PORT,
        process_name="jan",
        winrm_command=('start "" "C:\\Users\\maked\\AppData\\Local\\jan\\jan.exe"'),
        rdp_script=('start "" "C:\\Users\\maked\\AppData\\Local\\jan\\jan.exe"'),
    ),
}


class WorkerServiceManager:
    """
    Gestiona detección y lanzamiento de servicios en el Worker remoto.
    Usa múltiples estrategias: WinRM (primario), RDP (fallback), PsExec (fallback).
    """

    def __init__(self):
        self._worker_ip: str | None = None
        self._services: dict[str, WorkerService] = {k: WorkerService(**v.__dict__) for k, v in SERVICES.items()}
        self._check_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl = 15  # segundos

    async def resolve_worker_ip(self) -> str | None:
        """Resuelve la IP del Worker"""
        if self._worker_ip:
            return self._worker_ip
        try:
            ip = settings.get_worker_host()
            self._worker_ip = ip
            logger.info("worker_launcher.ip_resolved", ip=ip)
            return ip
        except Exception as e:
            logger.error("worker_launcher.ip_resolution_failed", error=str(e))
            return None

    async def check_port(self, host: str, port: int, timeout: float = 2.0) -> bool:
        """Verifica si un puerto TCP está abierto en el Worker"""
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, asyncio.TimeoutError, ConnectionRefusedError):
            return False

    async def check_http_health(self, base_url: str, timeout: float = 3.0) -> bool:
        """Verifica servicio vía HTTP health endpoint"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{base_url}/models")
                return resp.status_code == 200
        except Exception:
            return False

    async def check_all_services(self) -> dict[str, dict[str, Any]]:
        """Verifica el estado de todos los servicios en el Worker"""
        import time

        now = time.time()
        if self._check_cache and (now - self._get_cache_time()) < self._cache_ttl:
            return self._check_cache

        host = await self.resolve_worker_ip()
        if not host:
            return {name: {"status": "unknown", "error": "Worker IP no resuelta"} for name in self._services}

        results = {}
        for name, svc in self._services.items():
            svc.is_running = False
            svc.running_on_port = None

            # Check primary port on resolved worker IP
            if await self.check_port(host, svc.port):
                svc.is_running = True
                svc.running_on_port = svc.port
                results[name] = {"status": "running", "port": svc.port}
                continue

            # Fallback: HTTP health check (for services that bind to localhost on worker)
            if name == "jan":
                jan_url = f"http://{host}:{svc.port}/v1"
                if await self.check_http_health(jan_url):
                    svc.is_running = True
                    svc.running_on_port = svc.port
                    results[name] = {
                        "status": "running",
                        "port": svc.port,
                        "via": "http_health",
                    }
                    continue

            # Check alternate ports
            found = False
            for alt_port in svc.alt_ports:
                if await self.check_port(host, alt_port):
                    svc.is_running = True
                    svc.running_on_port = alt_port
                    results[name] = {"status": "running", "port": alt_port}
                    found = True
                    break

            if not found:
                results[name] = {"status": "stopped", "port": svc.port}

        self._check_cache = results
        self._cache_timestamp = now
        return results

    def _get_cache_time(self) -> float:
        return getattr(self, "_cache_timestamp", 0.0)

    async def launch_service_winrm(self, service_name: str) -> dict[str, Any]:
        """
        Intenta lanzar un servicio vía WinRM.
        Requiere: Worker en TrustedHosts y WinRM habilitado.
        """
        svc = self._services.get(service_name)
        if not svc:
            return {"success": False, "error": f"Servicio desconocido: {service_name}"}

        host = await self.resolve_worker_ip()
        if not host:
            return {"success": False, "error": "Worker IP no resuelta"}

        try:
            import subprocess

            ps_script = f"""
            $process = Get-Process -Name "{svc.process_name}" -ErrorAction SilentlyContinue
            if (-not $process) {{
                {svc.winrm_command}
                Write-Output "Launched: {svc.name}"
            }} else {{
                Write-Output "Already running: PID $($process.Id)"
            }}
            """
            cmd = [
                "powershell",
                "-Command",
                f"Invoke-Command -ComputerName {host} -ScriptBlock {{ {ps_script} }}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(
                    "worker_launcher.winrm_success",
                    service=service_name,
                    output=result.stdout.strip(),
                )
                return {"success": True, "output": result.stdout.strip()}
            else:
                logger.warning(
                    "worker_launcher.winrm_failed",
                    service=service_name,
                    error=result.stderr.strip(),
                )
                return {"success": False, "error": result.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "WinRM timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def launch_service_rdp(self, service_name: str) -> dict[str, Any]:
        """
        Intenta lanzar un servicio conectando vía RDP al Worker.
        La conexión RDP despierta la máquina; los servicios deben estar
        configurados para auto-iniciar en el Worker (ver worker_autostart.bat).
        """
        svc = self._services.get(service_name)
        if not svc:
            return {"success": False, "error": f"Servicio desconocido: {service_name}"}

        if not settings.RDP_ENABLED:
            return {"success": False, "error": "RDP no habilitado en config"}

        try:
            from backend.services.rdp_manager import RDPManager

            result = await RDPManager.connect_to_worker_async(
                hostname=settings.RDP_WORKER_HOSTNAME,
                username=settings.RDP_WORKER_USERNAME,
                password=settings.RDP_WORKER_PASSWORD,
                rate_limit_id=f"launch_{service_name}",
            )

            logger.info(
                "worker_launcher.rdp_launch_attempted",
                service=service_name,
                success=result.success,
            )
            return {"success": result.success, "message": result.message}

        except Exception as e:
            logger.error("worker_launcher.rdp_launch_failed", service=service_name, error=str(e))
            return {"success": False, "error": str(e)}

    async def ensure_service_running(self, service_name: str) -> dict[str, Any]:
        """
        Asegura que un servicio esté corriendo.
        Intenta: WinRM (si disponible) -> RDP -> Alerta
        """
        # 1. Verificar estado actual
        status = await self.check_all_services()
        svc_status = status.get(service_name, {})

        if svc_status.get("status") == "running":
            return {
                "success": True,
                "service": service_name,
                "action": "already_running",
                "port": svc_status.get("port"),
            }

        winrm_result = {"success": False, "error": "no_attempted"}
        rdp_result = {"success": False, "error": "no_attempted"}

        # 2. Intentar WinRM solo si el comando es ejecutable
        try:
            import subprocess

            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-Item WSMan:\\localhost\\Client\\TrustedHosts",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info("worker_launcher.try_winrm", service=service_name)
                winrm_result = await self.launch_service_winrm(service_name)
                await asyncio.sleep(3)
                status = await self.check_all_services()
                if status.get(service_name, {}).get("status") == "running":
                    return {
                        "success": True,
                        "service": service_name,
                        "action": "launched_via_winrm",
                    }
        except Exception as e:
            logger.debug("worker_launcher.winrm_unavailable", error=str(e)[:60])

        # 3. Fallback: RDP (solo si habilitado)
        if settings.RDP_ENABLED:
            logger.info("worker_launcher.try_rdp", service=service_name)
            try:
                rdp_result = await asyncio.wait_for(self.launch_service_rdp(service_name), timeout=10)
                await asyncio.sleep(3)
                status = await self.check_all_services()
                if status.get(service_name, {}).get("status") == "running":
                    return {
                        "success": True,
                        "service": service_name,
                        "action": "launched_via_rdp",
                    }
            except asyncio.TimeoutError:
                rdp_result = {"success": False, "error": "timeout"}
        else:
            rdp_result = {"success": False, "error": "RDP disabled"}

        # 4. Fallback general
        return {
            "success": False,
            "service": service_name,
            "action": "failed",
            "winrm_result": winrm_result,
            "rdp_result": rdp_result,
        }

    async def ensure_all_services(self) -> dict[str, dict[str, Any]]:
        """Asegura que todos los servicios estén corriendo"""
        status = await self.check_all_services()
        results = {}

        for service_name in self._services:
            if status.get(service_name, {}).get("status") != "running":
                results[service_name] = await self.ensure_service_running(service_name)
            else:
                results[service_name] = {
                    "success": True,
                    "service": service_name,
                    "action": "already_running",
                    "port": status[service_name].get("port"),
                }

        return results

    def get_status_summary(self, status: dict[str, dict[str, Any]]) -> str:
        """Genera resumen legible del estado de servicios"""
        lines = ["=== Worker Services Status ==="]
        for name, info in status.items():
            s = info.get("status", "unknown")
            port = info.get("port", "?")
            icon = {
                "running": "RUNNING",
                "stopped": "STOPPED",
                "unknown": "UNKNOWN",
            }.get(s, "?")
            lines.append(f"  [{icon}] {name.capitalize()} (:{port})")
        return "\n".join(lines)


# Instancia global
worker_service_manager = WorkerServiceManager()
