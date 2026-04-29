"""
Worker.py - Agente de ejecución para el sistema Pensamiento Coral.
Este script se ejecuta en los nodos de carga (Windows 11 o Android/Termux).
Detecta el sistema operativo, responde al descubrimiento UDP del Master,
ejecuta comandos enviados y mantiene heartbeat activo.
"""

import socket
import threading
import platform
import subprocess
import json
import time
import logging
import uuid
import sys
import os

# Agregar el directorio src al path para importar config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    SECRET_TOKEN,
    UDP_BROADCAST_PORT,
    TCP_COMMAND_PORT,
    HEARTBEAT_INTERVAL,
    BUFFER_SIZE,
    COMMAND_TIMEOUT,
    LOG_LEVEL,
    LOG_FORMAT
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)


class Worker:
    """
    Clase principal del Worker que gestiona la comunicación con el Master
    y la ejecución de comandos.
    """
    
    def __init__(self):
        """Inicializa el Worker con información del sistema."""
        self.worker_id = str(uuid.uuid4())
        self.os_type = self._detect_os()
        self.mac_address = self._get_mac_address()
        self.hostname = platform.node()
        self.master_ip = None
        self.running = False
        self.tcp_socket = None
        self.heartbeat_thread = None
        
        logger.info(f"Worker iniciado - ID: {self.worker_id}")
        logger.info(f"Sistema Operativo: {self.os_type}")
        logger.info(f"Hostname: {self.hostname}")
        logger.info(f"Dirección MAC: {self.mac_address}")
    
    def _detect_os(self):
        """
        Detecta el sistema operativo donde se ejecuta el Worker.
        
        Returns:
            str: 'Windows', 'Linux', 'Android' o 'Unknown'
        """
        system = platform.system()
        if system == "Windows":
            return "Windows"
        elif system == "Linux":
            # Verificar si es Android (Termux)
            try:
                with open("/proc/version", "r") as f:
                    version = f.read()
                    if "Android" in version:
                        return "Android"
            except:
                pass
            return "Linux"
        else:
            return "Unknown"
    
    def _get_mac_address(self):
        """
        Obtiene la dirección MAC de la interfaz de red principal.
        
        Returns:
            str: Dirección MAC en formato XX:XX:XX:XX:XX:XX
        """
        try:
            if self.os_type == "Windows":
                # En Windows usar getmac si está disponible, o ipconfig
                result = subprocess.run(
                    ["getmac", "/fo", "csv", "/nh"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                if result.returncode == 0:
                    mac = result.stdout.split(',')[0].strip('"')
                    return mac
                else:
                    # Fallback a ipconfig
                    result = subprocess.run(
                        ["ipconfig", "/all"],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                    for line in result.stdout.split('\n'):
                        if "Physical Address" in line:
                            mac = line.split(':')[-1].strip()
                            return mac
            else:
                # En Linux/Android usar ifconfig o ip link
                result = subprocess.run(
                    ["ip", "link", "show"],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if "link/ether" in line:
                        mac = line.split()[1]
                        return mac
            
            # Si todo falla, retornar un ID basado en hostname
            return f"UNKNOWN-{self.hostname}"
        except Exception as e:
            logger.error(f"Error obteniendo dirección MAC: {e}")
            return f"UNKNOWN-{self.hostname}"
    
    def _get_local_ip(self):
        """
        Obtiene la dirección IP local del Worker.
        
        Returns:
            str: Dirección IP local
        """
        try:
            # Crear socket UDP para obtener IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.error(f"Error obteniendo IP local: {e}")
            return "127.0.0.1"
    
    def start_udp_listener(self):
        """
        Inicia el listener UDP para responder a mensajes de descubrimiento del Master.
        """
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # En Windows necesitamos permitir broadcast
            if self.os_type == "Windows":
                udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            udp_socket.bind(("", UDP_BROADCAST_PORT))
            logger.info(f"Escuchando en puerto UDP {UDP_BROADCAST_PORT} para descubrimiento")
            
            while self.running:
                try:
                    udp_socket.settimeout(1.0)
                    data, addr = udp_socket.recvfrom(BUFFER_SIZE)
                    
                    try:
                        message = json.loads(data.decode('utf-8'))
                        
                        # Verificar que sea un mensaje de descubrimiento válido
                        if message.get('type') == 'DISCOVERY' and message.get('token') == SECRET_TOKEN:
                            logger.info(f"Mensaje de descubrimiento recibido de {addr[0]}")
                            
                            # Responder con información del Worker
                            response = {
                                'type': 'WORKER_RESPONSE',
                                'token': SECRET_TOKEN,
                                'worker_id': self.worker_id,
                                'os': self.os_type,
                                'hostname': self.hostname,
                                'mac_address': self.mac_address,
                                'ip': self._get_local_ip()
                            }
                            
                            udp_socket.sendto(
                                json.dumps(response).encode('utf-8'),
                                addr
                            )
                            logger.info(f"Respuesta enviada a {addr[0]}")
                    
                    except json.JSONDecodeError:
                        logger.warning("Mensaje JSON inválido recibido")
                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error en listener UDP: {e}")
        
        except Exception as e:
            logger.error(f"Error iniciando listener UDP: {e}")
        finally:
            udp_socket.close()
    
    def connect_to_master(self, master_ip):
        """
        Establece conexión TCP con el Master.
        
        Args:
            master_ip (str): Dirección IP del Master
        
        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario
        """
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(COMMAND_TIMEOUT)
            self.tcp_socket.connect((master_ip, TCP_COMMAND_PORT))
            
            # Enviar handshake con token de autenticación
            handshake = {
                'type': 'HANDSHAKE',
                'token': SECRET_TOKEN,
                'worker_id': self.worker_id,
                'os': self.os_type,
                'hostname': self.hostname,
                'mac_address': self.mac_address,
                'ip': self._get_local_ip()
            }
            
            self.tcp_socket.send(json.dumps(handshake).encode('utf-8'))
            
            # Esperar confirmación del Master
            response = self.tcp_socket.recv(BUFFER_SIZE).decode('utf-8')
            response_data = json.loads(response)
            
            if response_data.get('status') == 'ACCEPTED':
                self.master_ip = master_ip
                logger.info(f"Conexión establecida con Master en {master_ip}")
                return True
            else:
                logger.error("Conexión rechazada por el Master")
                return False
        
        except Exception as e:
            logger.error(f"Error conectando al Master: {e}")
            return False
    
    def send_heartbeat(self):
        """
        Envía heartbeat periódico al Master para mantener la conexión activa.
        """
        while self.running and self.tcp_socket:
            try:
                heartbeat = {
                    'type': 'HEARTBEAT',
                    'token': SECRET_TOKEN,
                    'worker_id': self.worker_id
                }
                
                self.tcp_socket.send(json.dumps(heartbeat).encode('utf-8'))
                logger.debug("Heartbeat enviado")
                time.sleep(HEARTBEAT_INTERVAL)
            
            except Exception as e:
                logger.error(f"Error enviando heartbeat: {e}")
                break
    
    def execute_command(self, command):
        """
        Ejecuta un comando en el sistema local y retorna el resultado.
        
        Args:
            command (str): Comando a ejecutar
        
        Returns:
            dict: Resultado de la ejecución con stdout, stderr y returncode
        """
        logger.info(f"Ejecutando comando: {command}")
        
        try:
            # Determinar el shell según el OS
            if self.os_type == "Windows":
                shell = True
            else:
                shell = True  # Para Linux/Android usar shell=True
            
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT
            )
            
            response = {
                'type': 'COMMAND_RESULT',
                'token': SECRET_TOKEN,
                'worker_id': self.worker_id,
                'command': command,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
            logger.info(f"Comando ejecutado - Return code: {result.returncode}")
            return response
        
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout ejecutando comando: {command}")
            return {
                'type': 'COMMAND_RESULT',
                'token': SECRET_TOKEN,
                'worker_id': self.worker_id,
                'command': command,
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timeout',
                'success': False
            }
        except Exception as e:
            logger.error(f"Error ejecutando comando: {e}")
            return {
                'type': 'COMMAND_RESULT',
                'token': SECRET_TOKEN,
                'worker_id': self.worker_id,
                'command': command,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }
    
    def listen_for_commands(self):
        """
        Escucha comandos enviados por el Master a través de TCP.
        """
        while self.running and self.tcp_socket:
            try:
                data = self.tcp_socket.recv(BUFFER_SIZE)
                if not data:
                    logger.warning("Conexión cerrada por el Master")
                    break
                
                message = json.loads(data.decode('utf-8'))
                
                # Verificar token
                if message.get('token') != SECRET_TOKEN:
                    logger.warning("Token inválido recibido")
                    continue
                
                msg_type = message.get('type')
                
                if msg_type == 'COMMAND':
                    # Ejecutar comando y enviar resultado
                    command = message.get('command')
                    result = self.execute_command(command)
                    self.tcp_socket.send(json.dumps(result).encode('utf-8'))
                
                elif msg_type == 'PING':
                    # Responder a ping
                    pong = {
                        'type': 'PONG',
                        'token': SECRET_TOKEN,
                        'worker_id': self.worker_id
                    }
                    self.tcp_socket.send(json.dumps(pong).encode('utf-8'))
                
                elif msg_type == 'DISCONNECT':
                    logger.info("Solicitud de desconexión recibida")
                    break
                
                else:
                    logger.warning(f"Tipo de mensaje desconocido: {msg_type}")
            
            except json.JSONDecodeError:
                logger.warning("Mensaje JSON inválido recibido")
            except Exception as e:
                logger.error(f"Error escuchando comandos: {e}")
                break
    
    def start(self, master_ip=None):
        """
        Inicia el Worker.
        
        Args:
            master_ip (str, optional): IP del Master para conectar directamente.
                                       Si es None, solo escucha descubrimiento UDP.
        """
        self.running = True
        
        # Iniciar listener UDP para descubrimiento
        udp_thread = threading.Thread(target=self.start_udp_listener, daemon=True)
        udp_thread.start()
        
        # Si se proporcionó IP del Master, conectar directamente
        if master_ip:
            if self.connect_to_master(master_ip):
                # Iniciar thread de heartbeat
                self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
                self.heartbeat_thread.start()
                
                # Escuchar comandos
                self.listen_for_commands()
        
        # Mantener el Worker corriendo
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupción recibida")
        finally:
            self.stop()
    
    def stop(self):
        """
        Detiene el Worker y cierra todas las conexiones.
        """
        logger.info("Deteniendo Worker...")
        self.running = False
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        logger.info("Worker detenido")


def main():
    """
    Función principal para ejecutar el Worker desde línea de comandos.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Worker para sistema Pensamiento Coral')
    parser.add_argument('--master', type=str, help='IP del Master para conectar directamente')
    args = parser.parse_args()
    
    worker = Worker()
    worker.start(master_ip=args.master)


if __name__ == "__main__":
    main()
