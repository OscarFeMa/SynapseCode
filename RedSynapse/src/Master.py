"""
Master.py - Nodo central del sistema Pensamiento Coral.
Proporciona interfaz gráfica para control y monitoreo de workers,
gestiona descubrimiento de red, cola de tareas y distribución de carga.
"""

import socket
import threading
import json
import time
import logging
import queue
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import customtkinter as ctk
from tkinter import ttk, scrolledtext, messagebox

# Agregar el directorio src al path para importar config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    SECRET_TOKEN,
    UDP_BROADCAST_PORT,
    TCP_COMMAND_PORT,
    TCP_FILE_PORT,
    BROADCAST_ADDRESS,
    HEARTBEAT_INTERVAL,
    HEARTBEAT_TIMEOUT,
    BUFFER_SIZE,
    MAX_TASK_RETRIES,
    COMMAND_TIMEOUT,
    LOG_LEVEL,
    LOG_FORMAT,
    WORKERS_DB_FILE,
    TASKS_HISTORY_FILE
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Configuración de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class WorkerInfo:
    """
    Clase para almacenar información de un Worker.
    """
    
    def __init__(self, worker_id: str, mac_address: str, os_type: str, 
                 hostname: str, ip: str, assigned_name: str = None):
        self.worker_id = worker_id
        self.mac_address = mac_address
        self.os_type = os_type
        self.hostname = hostname
        self.ip = ip
        self.assigned_name = assigned_name or f"Worker {worker_id[:8]}"
        self.status = "Active"
        self.last_heartbeat = datetime.now()
        self.tcp_socket = None
        self.cpu_load = 0.0
        self.task_queue = queue.Queue()
        self.current_task = None
    
    def update_heartbeat(self):
        """Actualiza el timestamp del último heartbeat."""
        self.last_heartbeat = datetime.now()
        self.status = "Active"
    
    def is_alive(self) -> bool:
        """Verifica si el worker está vivo basado en el heartbeat."""
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < HEARTBEAT_TIMEOUT
    
    def to_dict(self) -> dict:
        """Convierte la información del worker a diccionario."""
        return {
            'worker_id': self.worker_id,
            'mac_address': self.mac_address,
            'os_type': self.os_type,
            'hostname': self.hostname,
            'ip': self.ip,
            'assigned_name': self.assigned_name,
            'status': self.status,
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'cpu_load': self.cpu_load
        }


class Task:
    """
    Clase para representar una tarea en la cola.
    """
    
    def __init__(self, task_id: str, command: str, priority: int = 0):
        self.task_id = task_id
        self.command = command
        self.priority = priority
        self.status = "Pending"
        self.assigned_worker = None
        self.retry_count = 0
        self.result = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> dict:
        """Convierte la tarea a diccionario."""
        return {
            'task_id': self.task_id,
            'command': self.command,
            'priority': self.priority,
            'status': self.status,
            'assigned_worker': self.assigned_worker,
            'retry_count': self.retry_count,
            'result': self.result,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class MasterGUI(ctk.CTk):
    """
    Interfaz gráfica principal del Master.
    """
    
    def __init__(self):
        super().__init__()
        
        self.title("Pensamiento Coral - Master Control")
        self.geometry("1400x900")
        
        # Inicializar el lógica del Master
        self.master_logic = MasterLogic(self)
        
        # Crear interfaz
        self._create_widgets()
        
        # Iniciar threads de monitoreo
        self._start_monitoring_threads()
    
    def _create_widgets(self):
        """Crea todos los widgets de la interfaz."""
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Panel izquierdo: Workers
        left_panel = ctk.CTkFrame(main_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=5)
        
        # Título de workers
        workers_title = ctk.CTkLabel(
            left_panel, 
            text="Workers Conectados", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        workers_title.pack(pady=10)
        
        # Botón de escaneo
        scan_button = ctk.CTkButton(
            left_panel,
            text="🔍 Escanear Red",
            command=self.master_logic.scan_network
        )
        scan_button.pack(pady=5)
        
        # Tabla de workers
        self._create_workers_table(left_panel)
        
        # Panel derecho: Terminal y Tareas
        right_panel = ctk.CTkFrame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True, padx=5)
        
        # Notebook para pestañas
        self.notebook = ctk.CTkTabview(right_panel)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Pestaña de Terminal
        self.notebook.add("Terminal")
        self._create_terminal_tab(self.notebook.tab("Terminal"))
        
        # Pestaña de Cola de Tareas
        self.notebook.add("Cola de Tareas")
        self._create_tasks_tab(self.notebook.tab("Cola de Tareas"))
        
        # Pestaña de Historial
        self.notebook.add("Historial")
        self._create_history_tab(self.notebook.tab("Historial"))
    
    def _create_workers_table(self, parent):
        """Crea la tabla de workers."""
        # Frame para la tabla
        table_frame = ctk.CTkFrame(parent)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Treeview para mostrar workers
        self.workers_tree = ttk.Treeview(
            table_frame,
            columns=("name", "status", "os", "ip", "cpu"),
            show="headings",
            height=15
        )
        
        self.workers_tree.heading("name", text="Nombre")
        self.workers_tree.heading("status", text="Estado")
        self.workers_tree.heading("os", text="OS")
        self.workers_tree.heading("ip", text="IP")
        self.workers_tree.heading("cpu", text="CPU %")
        
        self.workers_tree.column("name", width=150)
        self.workers_tree.column("status", width=100)
        self.workers_tree.column("os", width=100)
        self.workers_tree.column("ip", width=120)
        self.workers_tree.column("cpu", width=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.workers_tree.yview)
        self.workers_tree.configure(yscrollcommand=scrollbar.set)
        
        self.workers_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Frame de acciones sobre worker seleccionado
        actions_frame = ctk.CTkFrame(parent)
        actions_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(actions_frame, text="Acciones sobre Worker:").pack(side="left", padx=5)
        
        self.selected_worker_var = ctk.StringVar()
        self.worker_selector = ctk.CTkOptionMenu(
            actions_frame,
            variable=self.selected_worker_var,
            values=["Todos"]
        )
        self.worker_selector.pack(side="left", padx=5)
        
        send_cmd_button = ctk.CTkButton(
            actions_frame,
            text="Enviar Comando",
            command=self._send_command_to_selected
        )
        send_cmd_button.pack(side="left", padx=5)
    
    def _create_terminal_tab(self, parent):
        """Crea la pestaña de terminal."""
        # Frame de entrada de comando
        input_frame = ctk.CTkFrame(parent)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(input_frame, text="Comando:").pack(side="left", padx=5)
        
        self.command_entry = ctk.CTkEntry(input_frame, placeholder_text="Escribe un comando...")
        self.command_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.command_entry.bind("<Return>", lambda e: self._execute_command())
        
        execute_button = ctk.CTkButton(
            input_frame,
            text="Ejecutar",
            command=self._execute_command
        )
        execute_button.pack(side="left", padx=5)
        
        # Terminal de salida
        self.terminal = scrolledtext.ScrolledText(
            parent,
            wrap="word",
            font=("Consolas", 10),
            bg="#1a1a1a",
            fg="#00ff00"
        )
        self.terminal.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _create_tasks_tab(self, parent):
        """Crea la pestaña de cola de tareas."""
        # Frame de entrada de tarea
        input_frame = ctk.CTkFrame(parent)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(input_frame, text="Comando:").pack(side="left", padx=5)
        
        self.task_entry = ctk.CTkEntry(input_frame, placeholder_text="Comando para la cola...")
        self.task_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(input_frame, text="Prioridad:").pack(side="left", padx=5)
        
        self.priority_entry = ctk.CTkEntry(input_frame, placeholder_text="0", width=50)
        self.priority_entry.pack(side="left", padx=5)
        
        add_task_button = ctk.CTkButton(
            input_frame,
            text="Agregar Tarea",
            command=self._add_task
        )
        add_task_button.pack(side="left", padx=5)
        
        # Tabla de tareas
        self._create_tasks_table(parent)
    
    def _create_tasks_table(self, parent):
        """Crea la tabla de tareas."""
        table_frame = ctk.CTkFrame(parent)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tasks_tree = ttk.Treeview(
            table_frame,
            columns=("id", "command", "status", "worker", "priority"),
            show="headings",
            height=15
        )
        
        self.tasks_tree.heading("id", text="ID")
        self.tasks_tree.heading("command", text="Comando")
        self.tasks_tree.heading("status", text="Estado")
        self.tasks_tree.heading("worker", text="Worker")
        self.tasks_tree.heading("priority", text="Prioridad")
        
        self.tasks_tree.column("id", width=80)
        self.tasks_tree.column("command", width=300)
        self.tasks_tree.column("status", width=100)
        self.tasks_tree.column("worker", width=120)
        self.tasks_tree.column("priority", width=80)
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=scrollbar.set)
        
        self.tasks_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_history_tab(self, parent):
        """Crea la pestaña de historial."""
        self.history_tree = ttk.Treeview(
            parent,
            columns=("id", "command", "status", "worker", "completed"),
            show="headings",
            height=20
        )
        
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("command", text="Comando")
        self.history_tree.heading("status", text="Estado")
        self.history_tree.heading("worker", text="Worker")
        self.history_tree.heading("completed", text="Completado")
        
        self.history_tree.column("id", width=80)
        self.history_tree.column("command", width=300)
        self.history_tree.column("status", width=100)
        self.history_tree.column("worker", width=120)
        self.history_tree.column("completed", width=150)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", padx=5, pady=5)
    
    def _start_monitoring_threads(self):
        """Inicia los threads de monitoreo en segundo plano."""
        # Thread para actualizar GUI
        self.gui_update_thread = threading.Thread(target=self._update_gui_loop, daemon=True)
        self.gui_update_thread.start()
        
        # Thread para procesar cola de tareas
        self.task_processor_thread = threading.Thread(target=self.master_logic.process_task_queue, daemon=True)
        self.task_processor_thread.start()
    
    def _update_gui_loop(self):
        """Loop de actualización de la GUI."""
        while True:
            try:
                self.after(1000, self._update_workers_table)
                self.after(1000, self._update_tasks_table)
                self.after(1000, self._update_worker_selector)
                time.sleep(1)
            except:
                break
    
    def _update_workers_table(self):
        """Actualiza la tabla de workers."""
        # Limpiar tabla
        for item in self.workers_tree.get_children():
            self.workers_tree.delete(item)
        
        # Agregar workers
        for worker in self.master_logic.workers.values():
            self.workers_tree.insert("", "end", values=(
                worker.assigned_name,
                worker.status,
                worker.os_type,
                worker.ip,
                f"{worker.cpu_load:.1f}%"
            ))
    
    def _update_tasks_table(self):
        """Actualiza la tabla de tareas."""
        # Limpiar tabla
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        
        # Agregar tareas pendientes
        for task in self.master_logic.task_queue:
            self.tasks_tree.insert("", "end", values=(
                task.task_id[:8],
                task.command[:50],
                task.status,
                task.assigned_worker or "No asignado",
                task.priority
            ))
    
    def _update_worker_selector(self):
        """Actualiza el selector de workers."""
        worker_names = ["Todos"] + [w.assigned_name for w in self.master_logic.workers.values()]
        self.worker_selector.configure(values=worker_names)
    
    def _execute_command(self):
        """Ejecuta un comando en el worker seleccionado."""
        command = self.command_entry.get()
        if not command:
            return
        
        selected = self.selected_worker_var.get()
        
        if selected == "Todos":
            # Enviar a todos los workers activos
            for worker in self.master_logic.workers.values():
                if worker.is_alive():
                    self.master_logic.send_command_to_worker(worker.worker_id, command)
            self._log_to_terminal(f"[MASTER] Comando enviado a todos: {command}")
        else:
            # Enviar al worker específico
            worker = next((w for w in self.master_logic.workers.values() 
                          if w.assigned_name == selected), None)
            if worker and worker.is_alive():
                self.master_logic.send_command_to_worker(worker.worker_id, command)
                self._log_to_terminal(f"[MASTER] Comando enviado a {selected}: {command}")
            else:
                self._log_to_terminal(f"[ERROR] Worker no encontrado o inactivo: {selected}")
        
        self.command_entry.delete(0, "end")
    
    def _send_command_to_selected(self):
        """Envía comando al worker seleccionado."""
        self._execute_command()
    
    def _add_task(self):
        """Agrega una tarea a la cola."""
        command = self.task_entry.get()
        if not command:
            return
        
        try:
            priority = int(self.priority_entry.get() or "0")
        except ValueError:
            priority = 0
        
        self.master_logic.add_task_to_queue(command, priority)
        self._log_to_terminal(f"[MASTER] Tarea agregada a la cola: {command}")
        
        self.task_entry.delete(0, "end")
        self.priority_entry.delete(0, "end")
    
    def _log_to_terminal(self, message: str):
        """Escribe un mensaje en la terminal."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.insert("end", f"[{timestamp}] {message}\n")
        self.terminal.see("end")
    
    def log_output(self, worker_name: str, output: str):
        """Escribe la salida de un comando en la terminal."""
        self._log_to_terminal(f"[{worker_name}] {output}")


class MasterLogic:
    """
    Lógica principal del Master para gestión de workers y tareas.
    """
    
    def __init__(self, gui: MasterGUI):
        self.gui = gui
        self.workers: Dict[str, WorkerInfo] = {}
        self.task_queue: List[Task] = []
        self.task_history: List[Task] = []
        self.running = True
        self.task_counter = 0
        
        # Cargar base de datos de workers
        self._load_workers_database()
        
        # Iniciar servidor TCP
        self.tcp_server_thread = threading.Thread(target=self._start_tcp_server, daemon=True)
        self.tcp_server_thread.start()
        
        logger.info("Master iniciado")
    
    def _load_workers_database(self):
        """Carga la base de datos de workers desde archivo JSON."""
        try:
            if os.path.exists(WORKERS_DB_FILE):
                with open(WORKERS_DB_FILE, 'r') as f:
                    data = json.load(f)
                    for worker_data in data:
                        worker = WorkerInfo(
                            worker_id=worker_data['worker_id'],
                            mac_address=worker_data['mac_address'],
                            os_type=worker_data['os_type'],
                            hostname=worker_data['hostname'],
                            ip=worker_data['ip'],
                            assigned_name=worker_data.get('assigned_name')
                        )
                        worker.status = "Inactive"
                        self.workers[worker.worker_id] = worker
                logger.info(f"Cargados {len(self.workers)} workers de la base de datos")
        except Exception as e:
            logger.error(f"Error cargando base de datos: {e}")
    
    def _save_workers_database(self):
        """Guarda la base de datos de workers en archivo JSON."""
        try:
            data = [worker.to_dict() for worker in self.workers.values()]
            with open(WORKERS_DB_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando base de datos: {e}")
    
    def scan_network(self):
        """Escanea la red local buscando workers mediante UDP broadcast."""
        self.gui._log_to_terminal("[MASTER] Iniciando escaneo de red...")
        
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.settimeout(5.0)
        
        try:
            # Enviar mensaje de descubrimiento
            discovery = {
                'type': 'DISCOVERY',
                'token': SECRET_TOKEN
            }
            
            udp_socket.sendto(
                json.dumps(discovery).encode('utf-8'),
                (BROADCAST_ADDRESS, UDP_BROADCAST_PORT)
            )
            
            logger.info("Mensaje de descubrimiento enviado")
            
            # Recibir respuestas
            start_time = time.time()
            found_workers = 0
            
            while time.time() - start_time < 5.0:
                try:
                    data, addr = udp_socket.recvfrom(BUFFER_SIZE)
                    response = json.loads(data.decode('utf-8'))
                    
                    if response.get('type') == 'WORKER_RESPONSE' and response.get('token') == SECRET_TOKEN:
                        worker_id = response['worker_id']
                        mac_address = response['mac_address']
                        
                        # Verificar si el worker ya existe por MAC
                        existing_worker = next(
                            (w for w in self.workers.values() if w.mac_address == mac_address),
                            None
                        )
                        
                        if existing_worker:
                            # Actualizar worker existente
                            existing_worker.ip = response['ip']
                            existing_worker.update_heartbeat()
                            self.gui._log_to_terminal(f"[MASTER] Worker reconectado: {existing_worker.assigned_name}")
                        else:
                            # Crear nuevo worker
                            worker = WorkerInfo(
                                worker_id=worker_id,
                                mac_address=mac_address,
                                os_type=response['os'],
                                hostname=response['hostname'],
                                ip=response['ip']
                            )
                            self.workers[worker_id] = worker
                            self.gui._log_to_terminal(f"[MASTER] Nuevo worker encontrado: {worker.assigned_name}")
                        
                        found_workers += 1
                        self._save_workers_database()
                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error procesando respuesta: {e}")
            
            self.gui._log_to_terminal(f"[MASTER] Escaneo completado. Workers encontrados: {found_workers}")
        
        except Exception as e:
            logger.error(f"Error en escaneo de red: {e}")
            self.gui._log_to_terminal(f"[ERROR] Error en escaneo: {e}")
        finally:
            udp_socket.close()
    
    def _start_tcp_server(self):
        """Inicia el servidor TCP para recibir conexiones de workers."""
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            tcp_socket.bind(("", TCP_COMMAND_PORT))
            tcp_socket.listen(10)
            logger.info(f"Servidor TCP escuchando en puerto {TCP_COMMAND_PORT}")
            
            while self.running:
                try:
                    client_socket, addr = tcp_socket.accept()
                    logger.info(f"Conexión recibida de {addr[0]}")
                    
                    # Thread para manejar la conexión
                    client_thread = threading.Thread(
                        target=self._handle_client_connection,
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                
                except Exception as e:
                    logger.error(f"Error aceptando conexión: {e}")
        
        except Exception as e:
            logger.error(f"Error iniciando servidor TCP: {e}")
        finally:
            tcp_socket.close()
    
    def _handle_client_connection(self, client_socket: socket.socket, addr: tuple):
        """Maneja la conexión con un worker."""
        try:
            # Recibir handshake
            data = client_socket.recv(BUFFER_SIZE)
            handshake = json.loads(data.decode('utf-8'))
            
            if handshake.get('token') != SECRET_TOKEN:
                logger.warning("Token inválido en handshake")
                client_socket.close()
                return
            
            worker_id = handshake['worker_id']
            
            if worker_id not in self.workers:
                logger.warning(f"Worker no registrado: {worker_id}")
                response = {'status': 'REJECTED', 'reason': 'Worker not registered'}
                client_socket.send(json.dumps(response).encode('utf-8'))
                client_socket.close()
                return
            
            worker = self.workers[worker_id]
            worker.tcp_socket = client_socket
            worker.update_heartbeat()
            
            # Enviar aceptación
            response = {'status': 'ACCEPTED'}
            client_socket.send(json.dumps(response).encode('utf-8'))
            
            logger.info(f"Worker conectado: {worker.assigned_name}")
            self.gui._log_to_terminal(f"[MASTER] Worker conectado: {worker.assigned_name}")
            
            # Escuchar mensajes del worker
            while self.running:
                try:
                    data = client_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    
                    message = json.loads(data.decode('utf-8'))
                    
                    if message.get('token') != SECRET_TOKEN:
                        continue
                    
                    msg_type = message.get('type')
                    
                    if msg_type == 'HEARTBEAT':
                        worker.update_heartbeat()
                    
                    elif msg_type == 'COMMAND_RESULT':
                        self._handle_command_result(worker, message)
                    
                    elif msg_type == 'PONG':
                        pass  # Respuesta a ping
                    
                except json.JSONDecodeError:
                    logger.warning("Mensaje JSON inválido")
                except Exception as e:
                    logger.error(f"Error recibiendo mensaje: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Error manejando conexión: {e}")
        finally:
            if worker_id in self.workers:
                self.workers[worker_id].tcp_socket = None
                self.workers[worker_id].status = "Inactive"
            client_socket.close()
            logger.info(f"Conexión cerrada con worker {worker_id}")
    
    def _handle_command_result(self, worker: WorkerInfo, result: dict):
        """Maneja el resultado de un comando ejecutado por un worker."""
        command = result.get('command')
        stdout = result.get('stdout', '')
        stderr = result.get('stderr', '')
        returncode = result.get('returncode')
        
        # Mostrar en terminal
        self.gui.log_output(worker.assigned_name, f"Comando: {command}")
        if stdout:
            self.gui.log_output(worker.assigned_name, f"STDOUT:\n{stdout}")
        if stderr:
            self.gui.log_output(worker.assigned_name, f"STDERR:\n{stderr}")
        self.gui.log_output(worker.assigned_name, f"Return code: {returncode}")
        
        # Si era una tarea de la cola, actualizar estado
        if worker.current_task:
            task = worker.current_task
            task.status = "Completed" if returncode == 0 else "Failed"
            task.result = result
            task.completed_at = datetime.now()
            worker.current_task = None
            
            # Mover al historial
            self.task_history.append(task)
            if task in self.task_queue:
                self.task_queue.remove(task)
            
            # Si falló y tiene reintentos, reasignar
            if returncode != 0 and task.retry_count < MAX_TASK_RETRIES:
                task.retry_count += 1
                task.status = "Pending"
                task.assigned_worker = None
                self.task_queue.append(task)
                self.gui._log_to_terminal(f"[MASTER] Tarea reencolada para reintento ({task.retry_count}/{MAX_TASK_RETRIES})")
    
    def send_command_to_worker(self, worker_id: str, command: str):
        """Envía un comando a un worker específico."""
        if worker_id not in self.workers:
            logger.error(f"Worker no encontrado: {worker_id}")
            return False
        
        worker = self.workers[worker_id]
        
        if not worker.tcp_socket or not worker.is_alive():
            logger.error(f"Worker no disponible: {worker.assigned_name}")
            return False
        
        try:
            message = {
                'type': 'COMMAND',
                'token': SECRET_TOKEN,
                'command': command
            }
            
            worker.tcp_socket.send(json.dumps(message).encode('utf-8'))
            return True
        
        except Exception as e:
            logger.error(f"Error enviando comando: {e}")
            return False
    
    def add_task_to_queue(self, command: str, priority: int = 0):
        """Agrega una tarea a la cola de procesamiento."""
        self.task_counter += 1
        task = Task(
            task_id=f"task_{self.task_counter}",
            command=command,
            priority=priority
        )
        
        # Insertar ordenado por prioridad
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority, reverse=True)
        
        logger.info(f"Tarea agregada: {task.task_id}")
    
    def process_task_queue(self):
        """Procesa la cola de tareas asignándolas a workers disponibles."""
        while self.running:
            try:
                if self.task_queue:
                    # Buscar worker disponible
                    available_worker = next(
                        (w for w in self.workers.values() 
                         if w.is_alive() and w.tcp_socket and w.current_task is None),
                        None
                    )
                    
                    if available_worker:
                        # Asignar siguiente tarea
                        task = self.task_queue.pop(0)
                        task.assigned_worker = available_worker.assigned_name
                        task.status = "Running"
                        task.started_at = datetime.now()
                        available_worker.current_task = task
                        
                        # Enviar comando
                        if self.send_command_to_worker(available_worker.worker_id, task.command):
                            self.gui._log_to_terminal(
                                f"[MASTER] Tarea {task.task_id[:8]} asignada a {available_worker.assigned_name}"
                            )
                        else:
                            # Reencolar si falló el envío
                            task.status = "Pending"
                            task.assigned_worker = None
                            available_worker.current_task = None
                            self.task_queue.insert(0, task)
                
                time.sleep(0.5)
            
            except Exception as e:
                logger.error(f"Error procesando cola: {e}")


def main():
    """Función principal para ejecutar el Master."""
    app = MasterGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
