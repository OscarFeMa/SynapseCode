"""
Sistema de Handshake TCP basado en Pensamiento Coral.
Establece conexión directa TCP entre Master y Worker con autenticación.
"""

import json
import logging
import socket
from typing import Any

logger = logging.getLogger(__name__)


class TCPHandshake:
    """Gestor de handshake TCP para conexión Master-Worker."""

    def __init__(self, role: str, secret_token: str = "synapse_coral_2024"):
        """
        Inicializa el gestor de handshake.

        Args:
            role: 'MASTER' o 'WORKER'
            secret_token: Token secreto para autenticación
        """
        self.role = role
        self.secret_token = secret_token
        self.tcp_socket: socket.socket | None = None
        self.peer_info: dict[str, Any] | None = None

    def connect_to_master(self, master_ip: str, port: int = 54322, worker_info: dict[str, Any] = None) -> bool:
        """
        Worker se conecta al Master vía TCP.

        Args:
            master_ip: IP del Master
            port: Puerto TCP del Master
            worker_info: Información del Worker (worker_id, mac, hostname, etc.)

        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(10)
            self.tcp_socket.connect((master_ip, port))

            # Enviar handshake con información del Worker
            handshake = {
                "type": "HANDSHAKE",
                "token": self.secret_token,
                "role": "WORKER",
                **(worker_info or {}),
            }

            self.tcp_socket.send(json.dumps(handshake).encode("utf-8"))
            logger.info(f"Handshake enviado a Master en {master_ip}")

            # Esperar confirmación del Master
            response = self.tcp_socket.recv(4096).decode("utf-8")
            response_data = json.loads(response)

            if response_data.get("status") == "ACCEPTED":
                self.peer_info = response_data.get("master_info", {})
                logger.info(f"Conexión TCP establecida con Master en {master_ip}")
                return True
            else:
                logger.error(f"Conexión rechazada por Master: {response_data.get('message')}")
                return False

        except Exception as e:
            logger.error(f"Error conectando al Master: {e}")
            return False

    def accept_worker(self, port: int = 54322) -> dict[str, Any] | None:
        """
        Master acepta conexión de un Worker.

        Args:
            port: Puerto TCP para escuchar

        Returns:
            Información del Worker si la conexión fue exitosa, None en caso contrario
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("0.0.0.0", port))  # nosec B104 - Required for TCP handshake protocol
        server_socket.listen(5)
        server_socket.settimeout(30)  # Timeout de 30 segundos

        logger.info(f"Escuchando conexiones TCP en puerto {port}")

        try:
            client_socket, addr = server_socket.accept()
            logger.info(f"Conexión recibida de {addr[0]}")

            # Recibir handshake del Worker
            data = client_socket.recv(4096).decode("utf-8")
            handshake_data = json.loads(data)

            # Verificar handshake
            if (
                handshake_data.get("type") == "HANDSHAKE"
                and handshake_data.get("token") == self.secret_token
                and handshake_data.get("role") == "WORKER"
            ):
                # Aceptar conexión
                response = {
                    "type": "HANDSHAKE_RESPONSE",
                    "status": "ACCEPTED",
                    "message": "Connection accepted",
                    "master_info": {"role": "MASTER", "ip": self._get_local_ip()},
                }

                client_socket.send(json.dumps(response).encode("utf-8"))

                # Guardar socket y info del worker
                self.tcp_socket = client_socket
                self.peer_info = handshake_data

                logger.info(f"Worker aceptado: {handshake_data.get('worker_id')}")
                return handshake_data
            else:
                # Rechazar conexión
                response = {
                    "type": "HANDSHAKE_RESPONSE",
                    "status": "REJECTED",
                    "message": "Invalid handshake",
                }
                client_socket.send(json.dumps(response).encode("utf-8"))
                client_socket.close()
                logger.warning("Handshake inválido, conexión rechazada")
                return None

        except socket.timeout:
            logger.warning("Timeout esperando conexión de Worker")
            return None
        except Exception as e:
            logger.error(f"Error aceptando conexión: {e}")
            return None
        finally:
            server_socket.close()

    def send_command(self, command: str) -> str | None:
        """
        Envía un comando al peer y retorna la respuesta.

        Args:
            command: Comando a enviar

        Returns:
            Respuesta del peer o None si falla
        """
        if not self.tcp_socket:
            logger.error("No hay conexión TCP establecida")
            return None

        try:
            message = {"type": "COMMAND", "command": command}

            self.tcp_socket.send(json.dumps(message).encode("utf-8"))

            response = self.tcp_socket.recv(4096).decode("utf-8")
            response_data = json.loads(response)

            return response_data.get("output")

        except Exception as e:
            logger.error(f"Error enviando comando: {e}")
            return None

    def close(self):
        """Cierra la conexión TCP."""
        if self.tcp_socket:
            self.tcp_socket.close()
            self.tcp_socket = None
            logger.info("Conexión TCP cerrada")

    def _get_local_ip(self) -> str:
        """Obtiene la IP local."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    def is_connected(self) -> bool:
        """Verifica si hay conexión TCP activa."""
        return self.tcp_socket is not None

    def get_peer_info(self) -> dict[str, Any] | None:
        """Retorna información del peer."""
        return self.peer_info
