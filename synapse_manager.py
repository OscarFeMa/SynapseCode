#!/usr/bin/env python3
"""
Synapse Manager - Herramienta de gestión automática Master-Worker
Controla el arranque, monitoreo y sincronización entre nodos.
"""

import asyncio
import subprocess
import sys
import time
import json
import socket
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class NodeStatus:
    """Estado de un nodo (Master o Worker)"""
    name: str
    role: str  # 'master' | 'worker'
    host: str
    port: int
    status: str  # 'online' | 'offline' | 'error'
    last_seen: Optional[str] = None
    error_message: Optional[str] = None
    ollama_models: List[str] = None
    
    def __post_init__(self):
        if self.ollama_models is None:
            self.ollama_models = []


class SynapseManager:
    """
    Gestor automático de cluster Synapse Council.
    - Descubre y monitorea Master y Workers
    - Arranca servicios automáticamente
    - Sincroniza configuración
    """
    
    def __init__(self, config_path: str = ".env"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.nodes: Dict[str, NodeStatus] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self._running = False
        
    def _load_config(self) -> Dict:
        """Carga configuración desde .env"""
        config = {}
        if self.config_path.exists():
            with open(self.config_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, val = line.strip().split('=', 1)
                        config[key] = val
        return config
    
    async def start_master(self) -> bool:
        """Arranca el Master en local."""
        try:
            logger.info("manager.starting_master", port=8000)
            
            # Verificar que no esté ya corriendo
            if await self._check_port(8000):
                logger.warning("master.already_running", port=8000)
                return True
            
            # Arrancar Master
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.main:app",
                 "--host", "0.0.0.0", "--port", "8000"],
                cwd=str(self.config_path.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes['master'] = process
            
            # Esperar a que esté listo
            for i in range(30):
                await asyncio.sleep(1)
                if await self._check_http("http://localhost:8000/health"):
                    logger.info("master.started", pid=process.pid)
                    self.nodes['master'] = NodeStatus(
                        name="master-local",
                        role="master",
                        host="localhost",
                        port=8000,
                        status="online",
                        last_seen=datetime.now().isoformat()
                    )
                    return True
            
            logger.error("master.start_timeout")
            return False
            
        except Exception as e:
            logger.error("master.start_failed", error=str(e))
            return False
    
    async def check_worker(self, host: str, ollama_port: int = 11434) -> NodeStatus:
        """Verifica estado del Worker remoto."""
        try:
            # Check Ollama
            ollama_url = f"http://{host}:{ollama_port}/api/tags"
            ollama_ok = await self._check_http(ollama_url)
            
            # Get models if available
            models = []
            if ollama_ok:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(ollama_url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                models = [m['name'] for m in data.get('models', [])]
                except:
                    pass
            
            status = NodeStatus(
                name=f"worker-{host}",
                role="worker",
                host=host,
                port=ollama_port,
                status="online" if ollama_ok else "offline",
                last_seen=datetime.now().isoformat() if ollama_ok else None,
                ollama_models=models
            )
            
            self.nodes[f"worker-{host}"] = status
            return status
            
        except Exception as e:
            status = NodeStatus(
                name=f"worker-{host}",
                role="worker",
                host=host,
                port=ollama_port,
                status="error",
                error_message=str(e)
            )
            self.nodes[f"worker-{host}"] = status
            return status
    
    async def check_all_nodes(self) -> Dict[str, NodeStatus]:
        """Verifica estado de todos los nodos."""
        # Check Master
        master_ok = await self._check_http("http://localhost:8000/health")
        if 'master' in self.nodes:
            self.nodes['master'].status = "online" if master_ok else "offline"
            self.nodes['master'].last_seen = datetime.now().isoformat() if master_ok else None
        
        # Check Worker(s)
        worker_host = self.config.get('WORKER_HOST', '192.168.1.43')
        await self.check_worker(worker_host)
        
        return self.nodes
    
    async def get_cluster_status(self) -> Dict:
        """Retorna estado completo del cluster."""
        nodes = await self.check_all_nodes()
        
        online_count = sum(1 for n in nodes.values() if n.status == 'online')
        total_count = len(nodes)
        
        return {
            "cluster_status": "healthy" if online_count == total_count else "degraded",
            "online_nodes": online_count,
            "total_nodes": total_count,
            "nodes": {k: asdict(v) for k, v in nodes.items()},
            "timestamp": datetime.now().isoformat()
        }
    
    async def _check_port(self, port: int, host: str = 'localhost') -> bool:
        """Verifica si un puerto está en uso."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    async def _check_http(self, url: str, timeout: int = 5) -> bool:
        """Verifica si una URL responde."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as resp:
                    return resp.status == 200
        except:
            return False
    
    async def monitor_loop(self, interval: int = 30):
        """Loop de monitoreo continuo."""
        self._running = True
        logger.info("manager.monitoring_started", interval=interval)
        
        while self._running:
            try:
                status = await self.get_cluster_status()
                logger.info("manager.cluster_status", 
                          online=status['online_nodes'],
                          total=status['total_nodes'])
                
                # Log solo si hay cambios
                for name, node in status['nodes'].items():
                    if node['status'] != 'online':
                        logger.warning(f"node.offline", node=name, status=node['status'])
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error("manager.monitor_error", error=str(e))
                await asyncio.sleep(interval)
    
    def stop(self):
        """Detiene el manager y todos los procesos."""
        self._running = False
        
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"manager.stopped_{name}")
            except:
                process.kill()


# CLI Interface
import click

@click.group()
def cli():
    """Synapse Manager - Gestión de cluster Master-Worker"""
    pass

@cli.command()
def status():
    """Muestra estado del cluster."""
    async def _status():
        manager = SynapseManager()
        status = await manager.get_cluster_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    asyncio.run(_status())

@cli.command()
def start():
    """Arranca Master y monitorea cluster."""
    async def _start():
        manager = SynapseManager()
        
        # Start master
        ok = await manager.start_master()
        if not ok:
            print("❌ Fallo al arrancar Master")
            return
        
        print("✅ Master arrancado en http://localhost:8000")
        
        # Check worker
        worker_host = manager.config.get('WORKER_HOST', '192.168.1.43')
        worker_status = await manager.check_worker(worker_host)
        
        if worker_status.status == 'online':
            print(f"✅ Worker online en {worker_host}")
            print(f"   Modelos disponibles: {len(worker_status.ollama_models)}")
        else:
            print(f"⚠️  Worker offline en {worker_host}")
        
        # Start monitoring
        print("\n🔍 Iniciando monitoreo (Ctrl+C para detener)...")
        try:
            await manager.monitor_loop(interval=30)
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo...")
            manager.stop()
    
    asyncio.run(_start())

@cli.command()
def check():
    """Verificación rápida sin arrancar servicios."""
    async def _check():
        manager = SynapseManager()
        
        print("🔍 Verificando cluster...\n")
        
        # Check Master
        master_ok = await manager._check_http("http://localhost:8000/health")
        status_icon = "✅" if master_ok else "❌"
        print(f"{status_icon} Master (localhost:8000): {'ONLINE' if master_ok else 'OFFLINE'}")
        
        # Check Worker
        worker_host = manager.config.get('WORKER_HOST', '192.168.1.43')
        worker_port = int(manager.config.get('WORKER_OLLAMA_PORT', 11434))
        worker_ok = await manager._check_http(f"http://{worker_host}:{worker_port}/api/tags")
        status_icon = "✅" if worker_ok else "❌"
        print(f"{status_icon} Worker ({worker_host}:{worker_port}): {'ONLINE' if worker_ok else 'OFFLINE'}")
        
        print(f"\n📝 Configuración:")
        print(f"   WORKER_HOST: {worker_host}")
        print(f"   OLLAMA_PORT: {worker_port}")
        print(f"   SUPABASE: {manager.config.get('SUPABASE_ENABLED', 'false')}")
        
        if master_ok and worker_ok:
            print("\n🚀 Cluster listo para operar!")
        else:
            print("\n⚠️  Algunos nodos no están disponibles")
    
    asyncio.run(_check())


if __name__ == "__main__":
    cli()
