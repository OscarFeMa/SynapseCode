"""
Synapse Council v2.0 - UDP Peer Discovery (Windows Compatible)
Sistema de auto-descubrimiento de nodos P2P en red local
Reparado para funcionar en Windows con broadcast/multicast
"""

import asyncio
import json
import platform
import socket
import time
from typing import Any, Dict, List, Optional

import structlog

from backend.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Constantes para broadcast
BROADCAST_ADDR = "255.255.255.255"  # Mejor que '<broadcast>' en Windows
DISCOVERY_MAGIC = "SYNAPSE_V2"  # Magic string para identificar nuestros paquetes


class DiscoveryProtocol(asyncio.DatagramProtocol):
    """Protocolo UDP para recibir y procesar beacons"""

    def __init__(self, discoverer: "NodeDiscoverer"):
        self.discoverer = discoverer

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode("utf-8"))
            self.discoverer.handle_beacon(message, addr[0])
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # Ignorar paquetes malformados


class NodeDiscoverer:
    """Gestor principal de descubrimiento P2P"""

    def __init__(self):
        self.peers: Dict[str, Dict[str, Any]] = {}
        self.peer_ttl = settings.DISCOVERY_INTERVAL * 3
        self.is_running = False
        self._broadcast_task: Optional[asyncio.Task] = None
        self._transport: Optional[asyncio.DatagramTransport] = None
        self.node_id = f"{settings.NODE_ROLE.lower()}-{int(time.time())}"

    def handle_beacon(self, message: Dict[str, Any], sender_ip: str):
        """Procesa un beacon recibido (valida magic string)"""
        # Validar que sea nuestro protocolo
        if message.get("magic") != DISCOVERY_MAGIC:
            # Ignorar paquetes que no son nuestros
            return

        node_role = message.get("role")
        node_id = message.get("node_id")

        # Ignorarnos a nosotros mismos
        if node_id == self.node_id:
            return

        if not node_role or not node_id:
            return

        is_new = node_id not in self.peers

        self.peers[node_id] = {
            "role": node_role,
            "ip": sender_ip,
            "last_seen": time.time(),
            "data": message,
        }

        if is_new:
            logger.info(
                "network.peer_discovered", node_id=node_id, role=node_role, ip=sender_ip
            )

            # Si somos MASTER y encontramos un WORKER, actualizamos la configuración
            if settings.is_master and node_role == "WORKER":
                logger.info("network.worker_linked", ip=sender_ip)
                settings.update_worker_host(sender_ip)

    def _get_broadcast_addresses(self) -> List[str]:
        """Obtiene todas las direcciones de broadcast posibles"""
        addresses = [BROADCAST_ADDR]  # Broadcast global

        try:
            # Intentar obtener broadcast de interfaces específicas
            hostname = socket.gethostname()
            local_ip = socket.getaddrinfo(hostname, None, socket.AF_INET)[0][4][0]

            # Calcular broadcast de la subred local (asume /24)
            ip_parts = local_ip.split(".")
            if len(ip_parts) == 4:
                subnet_broadcast = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
                if subnet_broadcast not in addresses:
                    addresses.append(subnet_broadcast)
        except:
            pass

        return addresses

    async def _broadcast_loop(self):
        """Bucle infinito que emite beacons periódicamente (Windows compatible)"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Configuración específica para Windows
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Permitir reusar dirección (importante para desarrollo local)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # En Windows, deshabilitar el bloqueo de broadcast en algunas interfaces
        if platform.system() == "Windows":
            try:
                # Timeout para no bloquear indefinidamente
                sock.settimeout(1.0)
            except:
                pass

        broadcast_addrs = self._get_broadcast_addresses()
        logger.info("network.broadcast_addresses", addresses=broadcast_addrs)

        while self.is_running:
            try:
                # Limpiar peers inactivos
                current_time = time.time()
                dead_peers = [
                    pid
                    for pid, peer in self.peers.items()
                    if current_time - peer["last_seen"] > self.peer_ttl
                ]
                for pid in dead_peers:
                    peer_role = self.peers[pid]["role"]
                    logger.info("network.peer_lost", node_id=pid, role=peer_role)
                    del self.peers[pid]

                    # Si perdimos al único worker, podríamos loguearlo
                    if settings.is_master and peer_role == "WORKER":
                        active_workers = [
                            p for p in self.peers.values() if p["role"] == "WORKER"
                        ]
                        if not active_workers:
                            logger.warning("network.all_workers_lost")

                # Construir beacon con magic string
                message = json.dumps(
                    {
                        "magic": DISCOVERY_MAGIC,
                        "node_id": self.node_id,
                        "role": settings.NODE_ROLE,
                        "port": settings.PORT,
                        "timestamp": time.time(),
                    }
                ).encode("utf-8")

                # Enviar a todas las direcciones de broadcast conocidas
                for addr in broadcast_addrs:
                    try:
                        sock.sendto(message, (addr, settings.DISCOVERY_PORT))
                    except Exception as e:
                        logger.debug(
                            "network.broadcast_to_failed", address=addr, error=str(e)
                        )

            except Exception as e:
                logger.error("network.broadcast_error", error=str(e))

            await asyncio.sleep(settings.DISCOVERY_INTERVAL)

        sock.close()

    async def start(self):
        """Inicia el sistema de descubrimiento (escucha y broadcast) - Windows compatible"""
        if self.is_running:
            return

        self.is_running = True
        logger.info(
            "network.discovery_starting",
            port=settings.DISCOVERY_PORT,
            node_role=settings.NODE_ROLE,
            platform=platform.system(),
        )

        loop = asyncio.get_running_loop()

        # Configurar socket de escucha
        listen_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Windows específico: algunas veces necesitamos SO_EXCLUSIVEADDRUSE
        # o simplemente manejar el bind de forma diferente
        bind_success = False
        bind_errors = []

        # Intentar diferentes formas de bind
        bind_attempts = [
            ("", settings.DISCOVERY_PORT),  # Todas las interfaces
            ("0.0.0.0", settings.DISCOVERY_PORT),  # Todas IPv4
        ]

        for bind_addr, bind_port in bind_attempts:
            try:
                listen_sock.bind((bind_addr, bind_port))
                bind_success = True
                logger.info(
                    "network.bind_success", address=bind_addr or "all", port=bind_port
                )
                break
            except OSError as e:
                bind_errors.append(f"{bind_addr}:{bind_port} - {e}")
                continue

        if not bind_success:
            logger.error("network.bind_failed_all", attempts=bind_errors)
            self.is_running = False
            return

        try:
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: DiscoveryProtocol(self), sock=listen_sock
            )
            logger.info("network.endpoint_created")
        except Exception as e:
            logger.error("network.endpoint_failed", error=str(e))
            self.is_running = False
            return

        # Iniciar broadcast con delay inicial para dejar que todo se estabilice
        await asyncio.sleep(0.5)
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("network.discovery_started")

    async def stop(self):
        """Detiene el sistema de descubrimiento"""
        if not self.is_running:
            return

        self.is_running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        if self._transport:
            self._transport.close()

        logger.info("network.discovery_stopped")

    def get_active_peers(self) -> list:
        """Devuelve la lista de peers activos formateada"""
        return [
            {
                "node_id": pid,
                "role": peer["role"],
                "ip": peer["ip"],
                "age_seconds": int(time.time() - peer["last_seen"]),
            }
            for pid, peer in self.peers.items()
        ]


# Singleton instance
node_discoverer = NodeDiscoverer()
