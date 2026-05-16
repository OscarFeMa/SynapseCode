"""
Sistema de Heartbeat basado en Pensamiento Coral.
Permite monitorear la conectividad entre Master y Worker en tiempo real.
"""

import json
import logging
import socket
import threading
import time
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """Gestor de heartbeat para monitorear conectividad."""

    def __init__(self, role: str, interval: int = 5, timeout: int = 15):
        """
        Inicializa el gestor de heartbeat.

        Args:
            role: 'MASTER' o 'WORKER'
            interval: Intervalo entre heartbeats en segundos
            timeout: Tiempo máximo sin heartbeat antes de marcar como desconectado
        """
        self.role = role
        self.interval = interval
        self.timeout = timeout
        self.running = False
        self.last_heartbeat = None
        self.heartbeat_thread = None
        self.tcp_socket = None
        self.peer_ip: Optional[str] = None
        self.on_heartbeat_received: Optional[Callable] = None
        self.on_connection_lost: Optional[Callable] = None

    def start(self, peer_ip: Optional[str] = None):
        """
        Inicia el sistema de heartbeat.

        Args:
            peer_ip: IP del peer (Master para Worker, Worker para Master)
        """
        self.peer_ip = peer_ip
        self.running = True
        self.last_heartbeat = datetime.now()

        if self.role == "WORKER":
            # Worker envía heartbeats al Master
            self.heartbeat_thread = threading.Thread(
                target=self._send_heartbeats, daemon=True
            )
            self.heartbeat_thread.start()
            logger.info(f"Heartbeat iniciado (Worker → {peer_ip})")
        else:
            # Master escucha heartbeats del Worker
            self.heartbeat_thread = threading.Thread(
                target=self._listen_heartbeats, daemon=True
            )
            self.heartbeat_thread.start()
            logger.info("Heartbeat iniciado (Master escuchando)")

    def stop(self):
        """Detiene el sistema de heartbeat."""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
        if self.tcp_socket:
            self.tcp_socket.close()
        logger.info("Heartbeat detenido")

    def _send_heartbeats(self):
        """Envía heartbeats periódicos al Master (Worker)."""
        while self.running and self.peer_ip:
            try:
                if not self.tcp_socket:
                    self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.tcp_socket.settimeout(5)
                    try:
                        self.tcp_socket.connect((self.peer_ip, 54322))
                        logger.info(
                            f"Conexión TCP establecida con Master en {self.peer_ip}"
                        )
                    except Exception as e:
                        logger.error(f"Error conectando al Master: {e}")
                        self.tcp_socket.close()
                        self.tcp_socket = None
                        time.sleep(self.interval)
                        continue

                # Enviar heartbeat
                heartbeat_msg = {
                    "type": "HEARTBEAT",
                    "timestamp": datetime.now().isoformat(),
                    "role": "WORKER",
                }

                self.tcp_socket.send(json.dumps(heartbeat_msg).encode("utf-8"))
                logger.debug("Heartbeat enviado")

                time.sleep(self.interval)

            except Exception as e:
                logger.error(f"Error enviando heartbeat: {e}")
                if self.tcp_socket:
                    self.tcp_socket.close()
                    self.tcp_socket = None
                time.sleep(self.interval)

    def _listen_heartbeats(self):
        """Escucha heartbeats del Worker (Master)."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("0.0.0.0", 54322))
        server_socket.listen(5)
        server_socket.settimeout(1.0)

        logger.info("Escuchando heartbeats en puerto 54322")

        while self.running:
            try:
                try:
                    client_socket, addr = server_socket.accept()
                    logger.info(f"Conexión heartbeat desde {addr[0]}")

                    # Hilo para manejar esta conexión
                    threading.Thread(
                        target=self._handle_heartbeat_connection,
                        args=(client_socket, addr[0]),
                        daemon=True,
                    ).start()

                except socket.timeout:
                    # Verificar timeout de heartbeat
                    if self.last_heartbeat:
                        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
                        if elapsed > self.timeout and self.on_connection_lost:
                            logger.warning(
                                f"Worker desconectado (sin heartbeat por {elapsed}s)"
                            )
                            self.on_connection_lost()
                    continue

            except Exception as e:
                logger.error(f"Error en listener heartbeat: {e}")
                time.sleep(1)

        server_socket.close()

    def _handle_heartbeat_connection(self, client_socket: socket.socket, peer_ip: str):
        """Maneja una conexión de heartbeat entrante."""
        try:
            while self.running:
                try:
                    client_socket.settimeout(self.timeout + 5)
                    data = client_socket.recv(1024)

                    if not data:
                        break

                    try:
                        message = json.loads(data.decode("utf-8"))

                        if message.get("type") == "HEARTBEAT":
                            self.last_heartbeat = datetime.now()
                            self.peer_ip = peer_ip
                            logger.debug(f"Heartbeat recibido de {peer_ip}")

                            if self.on_heartbeat_received:
                                self.on_heartbeat_received(peer_ip)

                    except json.JSONDecodeError:
                        logger.warning("Mensaje heartbeat inválido")

                except socket.timeout:
                    break

        except Exception as e:
            logger.error(f"Error manejando conexión heartbeat: {e}")
        finally:
            client_socket.close()

    def is_alive(self) -> bool:
        """
        Verifica si el peer está vivo basado en heartbeat.

        Returns:
            True si el peer está vivo, False en caso contrario
        """
        if not self.last_heartbeat:
            return False

        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < self.timeout

    def get_last_heartbeat_time(self) -> Optional[datetime]:
        """Retorna el timestamp del último heartbeat."""
        return self.last_heartbeat

    def get_peer_ip(self) -> Optional[str]:
        """Retorna la IP del peer."""
        return self.peer_ip
