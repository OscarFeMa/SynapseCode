#!/usr/bin/env python3
"""
Synapse Control Center - Aplicación de Control Central
Gestiona Master, Worker y API Web para debates
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
import subprocess
import threading
import time
import json
import requests
import webbrowser
from datetime import datetime
import os

class SynapseControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Synapse Control Center v3.1")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Configuración
        self.config_file = "synapse_workers.json"
        self.workers_history = self.load_workers_history()
        
        # Estados
        self.worker_ip = None
        self.worker_connected = False
        self.master_running = False
        self.web_api_running = False
        self.ollama_worker_status = False
        self.ollama_master_status = False
        
        # Procesos
        self.master_process = None
        self.web_process = None
        
        self.setup_ui()
        self.start_monitoring()
    
    def setup_ui(self):
        """Configurar la interfaz de usuario"""
        # Notebook para pestañas
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Pestaña principal
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Control Principal")
        self.setup_main_tab(main_frame)
        
        # Pestaña de monitor
        monitor_frame = ttk.Frame(notebook)
        notebook.add(monitor_frame, text="Monitor en Vivo")
        self.setup_monitor_tab(monitor_frame)
        
        # Pestaña de logs
        logs_frame = ttk.Frame(notebook)
        notebook.add(logs_frame, text="Logs")
        self.setup_logs_tab(logs_frame)
    
    def setup_main_tab(self, parent):
        """Configurar pestaña principal"""
        # Frame principal
        main_container = ttk.Frame(parent, padding="15")
        main_container.pack(fill='both', expand=True)
        
        # Título
        title = ttk.Label(main_container, text="Synapse Control Center", 
                         font=("Arial", 18, "bold"))
        title.pack(pady=(0, 20))
        
        # Frame de Worker
        worker_frame = ttk.LabelFrame(main_container, text="Worker Control", padding="10")
        worker_frame.pack(fill='x', pady=(0, 15))
        
        # Selección de Worker
        worker_select_frame = ttk.Frame(worker_frame)
        worker_select_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(worker_select_frame, text="Worker:").pack(side='left')
        self.worker_var = tk.StringVar()
        self.worker_combo = ttk.Combobox(worker_select_frame, textvariable=self.worker_var,
                                        values=list(self.workers_history.keys()), width=20)
        self.worker_combo.pack(side='left', padx=(5, 0))
        self.worker_combo.set("makederpc")  # Default
        
        ttk.Button(worker_select_frame, text="🔄 Refrescar", 
                  command=self.refresh_worker_ip).pack(side='left', padx=(5, 0))
        
        # Estado del Worker
        self.worker_status_label = ttk.Label(worker_frame, text="🔴 Desconocido", 
                                           font=("Arial", 10, "bold"))
        self.worker_status_label.pack(anchor='w')
        
        self.worker_ip_label = ttk.Label(worker_frame, text="IP: No detectada")
        self.worker_ip_label.pack(anchor='w')
        
        self.ollama_worker_label = ttk.Label(worker_frame, text="Ollama Worker: ❌")
        self.ollama_worker_label.pack(anchor='w')
        
        # Botones principales
        buttons_frame = ttk.Frame(main_container)
        buttons_frame.pack(fill='x', pady=15)
        
        # Botón 1: Conectar Worker
        self.connect_worker_btn = ttk.Button(buttons_frame, 
                                           text="🔗 1. Conectar Worker (RDP + Ollama)",
                                           command=self.connect_worker,
                                           style="Large.TButton")
        self.connect_worker_btn.pack(fill='x', pady=(0, 10))
        
        # Botón 2: Iniciar Master + API Web
        self.start_master_btn = ttk.Button(buttons_frame,
                                          text="🚀 2. Iniciar Master + API Web",
                                          command=self.start_master_api,
                                          style="Large.TButton")
        self.start_master_btn.pack(fill='x', pady=(0, 10))
        
        # Botón 3: Abrir API Web
        self.open_web_btn = ttk.Button(buttons_frame,
                                      text="🌐 3. Abrir API Web (Debates)",
                                      command=self.open_web_api,
                                      state='disabled')
        self.open_web_btn.pack(fill='x')
        
        # Frame de Master
        master_frame = ttk.LabelFrame(main_container, text="Master Status", padding="10")
        master_frame.pack(fill='x', pady=(15, 0))
        
        self.master_status_label = ttk.Label(master_frame, text="🔴 Master: Detenido",
                                            font=("Arial", 10, "bold"))
        self.master_status_label.pack(anchor='w')
        
        self.web_api_label = ttk.Label(master_frame, text="API Web: ❌")
        self.web_api_label.pack(anchor='w')
        
        self.ollama_master_label = ttk.Label(master_frame, text="Ollama Master: ❌")
        self.ollama_master_label.pack(anchor='w')
        
        # Configurar estilos
        style = ttk.Style()
        style.configure("Large.TButton", font=("Arial", 11, "bold"), padding=10)
    
    def setup_monitor_tab(self, parent):
        """Configurar pestaña de monitor"""
        monitor_container = ttk.Frame(parent, padding="15")
        monitor_container.pack(fill='both', expand=True)
        
        # Frame de información en vivo
        info_frame = ttk.LabelFrame(monitor_container, text="Estado del Sistema", padding="10")
        info_frame.pack(fill='x', pady=(0, 15))
        
        # Crear treeview para mostrar información
        columns = ('Componente', 'Estado', 'IP/Puerto', 'Última Verificación')
        self.monitor_tree = ttk.Treeview(info_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.monitor_tree.heading(col, text=col)
            self.monitor_tree.column(col, width=150)
        
        self.monitor_tree.pack(fill='x')
        
        # Frame de acciones rápidas
        actions_frame = ttk.LabelFrame(monitor_container, text="Acciones Rápidas", padding="10")
        actions_frame.pack(fill='x')
        
        ttk.Button(actions_frame, text="🔄 Verificar Todo", 
                  command=self.full_system_check).pack(side='left', padx=(0, 10))
        ttk.Button(actions_frame, text="🧹 Limpiar Logs", 
                  command=self.clear_logs).pack(side='left', padx=(0, 10))
        ttk.Button(actions_frame, text="📊 Exportar Estado", 
                  command=self.export_status).pack(side='left')
    
    def setup_logs_tab(self, parent):
        """Configurar pestaña de logs"""
        logs_container = ttk.Frame(parent, padding="15")
        logs_container.pack(fill='both', expand=True)
        
        # Área de logs
        self.logs_text = scrolledtext.ScrolledText(logs_container, height=20, width=80)
        self.logs_text.pack(fill='both', expand=True)
        
        # Frame de control de logs
        log_controls = ttk.Frame(logs_container)
        log_controls.pack(fill='x', pady=(10, 0))
        
        ttk.Button(log_controls, text="Limpiar", 
                  command=self.clear_logs).pack(side='left')
        ttk.Button(log_controls, text="Guardar", 
                  command=self.save_logs).pack(side='left', padx=(5, 0))
        
        self.log_level_var = tk.StringVar(value="INFO")
        ttk.Label(log_controls, text="Nivel:").pack(side='left', padx=(20, 5))
        ttk.Combobox(log_controls, textvariable=self.log_level_var,
                    values=["DEBUG", "INFO", "WARNING", "ERROR"],
                    width=10).pack(side='left')
    
    def load_workers_history(self):
        """Cargar historial de workers"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {"makederpc": "192.168.1.42"}  # Default
    
    def save_workers_history(self):
        """Guardar historial de workers"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.workers_history, f, indent=2)
        except Exception as e:
            self.log(f"Error guardando historial: {e}", "ERROR")
    
    def log(self, message, level="INFO"):
        """Agregar mensaje al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        self.logs_text.insert(tk.END, log_entry)
        self.logs_text.see(tk.END)
        
        # Limitar tamaño del log
        lines = self.logs_text.get("1.0", tk.END).split('\n')
        if len(lines) > 1000:
            self.logs_text.delete("1.0", "100.0")
    
    def refresh_worker_ip(self):
        """Refrescar IP del Worker"""
        def resolve():
            try:
                hostname = self.worker_var.get() or "makederpc"
                self.log(f"Resolviendo IP para {hostname}...")
                ip = socket.gethostbyname(hostname)
                self.worker_ip = ip
                
                # Guardar en historial
                self.workers_history[hostname] = ip
                self.save_workers_history()
                
                self.root.after(0, lambda: self.update_worker_status(ip))
                self.log(f"IP resuelta: {hostname} → {ip}")
                
            except socket.gaierror:
                self.worker_ip = None
                self.root.after(0, lambda: self.update_worker_status(None))
                self.log(f"No se pudo resolver {hostname}", "ERROR")
        
        threading.Thread(target=resolve, daemon=True).start()
    
    def update_worker_status(self, ip):
        """Actualizar estado del Worker en UI"""
        if ip:
            self.worker_ip_label.config(text=f"IP: {ip}")
            self.worker_status_label.config(text="🟡 Detectado", foreground="orange")
        else:
            self.worker_ip_label.config(text="IP: No detectada")
            self.worker_status_label.config(text="🔴 No encontrado", foreground="red")
    
    def check_ollama_status(self, ip, port=11434):
        """Verificar si Ollama está corriendo"""
        try:
            response = requests.get(f"http://{ip}:{port}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return True, len(models)
            return False, 0
        except:
            return False, 0
    
    def connect_worker(self):
        """Conectar al Worker (RDP + verificar Ollama)"""
        if not self.worker_ip:
            messagebox.showerror("Error", "Primero detecta la IP del Worker")
            return
        
        self.log("Iniciando conexión RDP al Worker...")
        self.connect_worker_btn.config(state='disabled')
        
        def connect():
            try:
                # 1. Conexión RDP
                cmdkey_cmd = [
                    'cmdkey', 
                    '/generic:TERMSRV/' + self.worker_ip,
                    '/user:MAKEDER\\maked',
                    '/pass:DNIcxwcaqza4'
                ]
                
                subprocess.run(cmdkey_cmd, capture_output=True, text=True)
                
                rdp_content = f"""full address:s:{self.worker_ip}
username:s:MAKEDER\\maked
domain:s:MAKEDER
screen mode id:i:2
prompt for credentials:i:0
redirectdrives:i:1
redirectprinters:i:1
redirectclipboard:i:1
"""
                
                rdp_file = f"worker_{self.worker_ip.replace('.', '_')}.rdp"
                with open(rdp_file, 'w') as f:
                    f.write(rdp_content)
                
                subprocess.Popen(['mstsc', rdp_file])
                
                self.root.after(0, lambda: self.log(f"RDP iniciado hacia {self.worker_ip}"))
                
                # 2. Verificar Ollama
                time.sleep(3)  # Esperar a que inicie RDP
                ollama_ok, models_count = self.check_ollama_status(self.worker_ip)
                
                if ollama_ok:
                    self.root.after(0, lambda: self.ollama_worker_label.config(
                        text=f"Ollama Worker: ✅ ({models_count} modelos)"))
                    self.root.after(0, lambda: self.log(f"Ollama Worker OK: {models_count} modelos"))
                    self.worker_connected = True
                else:
                    self.root.after(0, lambda: self.ollama_worker_label.config(
                        text="Ollama Worker: ❌ (No responde)"))
                    self.root.after(0, lambda: self.log("Ollama Worker no responde", "WARNING"))
                
                self.root.after(0, lambda: self.worker_status_label.config(
                    text="🟢 Conectado", foreground="green"))
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Error conectando Worker: {e}", "ERROR"))
            
            finally:
                self.root.after(0, lambda: self.connect_worker_btn.config(state='normal'))
        
        threading.Thread(target=connect, daemon=True).start()
    
    def check_master_running(self):
        """Verificar si Master ya está corriendo"""
        try:
            response = requests.get('http://localhost:8000/health', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_master_api(self):
        """Iniciar Master + API Web"""
        # Primero verificar si ya está corriendo
        if self.check_master_running():
            result = messagebox.askyesno("Master Activo", 
                "El Master ya está corriendo en localhost:8000\n\n"
                "¿Deseas usar el Master existente?")
            if result:
                self.master_running = True
                self.web_api_running = True
                self.master_status_label.config(text="🟢 Master: Activo", foreground="green")
                self.open_web_btn.config(state='normal')
                
                # Verificar Ollama Master
                ollama_ok, models_count = self.check_ollama_status('localhost', 11434)
                if ollama_ok:
                    self.ollama_master_label.config(text=f"Ollama Master: ✅ ({models_count} modelos)")
                else:
                    self.ollama_master_label.config(text="Ollama Master: ❌")
                
                self.log("Usando Master existente")
            return
        
        if not self.worker_connected:
            result = messagebox.askyesno("Advertencia", 
                "Worker no está verificado. ¿Deseas continuar?")
            if not result:
                return
        
        self.log("Iniciando Master + API Web...")
        self.start_master_btn.config(state='disabled')
        
        def start():
            try:
                # 1. Verificar que el puerto esté libre
                self.root.after(0, lambda: self.log("Verificando puerto 8000..."))
                
                # 2. Iniciar Master (backend)
                master_cmd = [
                    'python', '-m', 'uvicorn', 
                    'backend.main:app',
                    '--host', '0.0.0.0',
                    '--port', '8000'
                ]
                
                self.master_process = subprocess.Popen(
                    master_cmd,
                    cwd='D:\\proyectos\\Synapse',
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                
                self.root.after(0, lambda: self.log("Master iniciado, esperando respuesta..."))
                
                # 3. Esperar y verificar API
                max_attempts = 10
                for attempt in range(max_attempts):
                    time.sleep(2)
                    try:
                        response = requests.get('http://localhost:8000/health', timeout=5)
                        if response.status_code == 200:
                            self.root.after(0, lambda: self.master_status_label.config(
                                text="🟢 Master: Activo", foreground="green"))
                            self.root.after(0, lambda: self.log("Master API iniciado correctamente"))
                            
                            # 4. Verificar Ollama Master
                            ollama_ok, models_count = self.check_ollama_status('localhost', 11434)
                            if ollama_ok:
                                self.root.after(0, lambda: self.ollama_master_label.config(
                                    text=f"Ollama Master: ✅ ({models_count} modelos)"))
                            else:
                                self.root.after(0, lambda: self.ollama_master_label.config(
                                    text="Ollama Master: ❌"))
                            
                            # 5. Habilitar botón de API Web
                            self.root.after(0, lambda: self.open_web_btn.config(state='normal'))
                            self.master_running = True
                            self.web_api_running = True
                            break
                    except:
                        self.root.after(0, lambda a=attempt+1: 
                            self.log(f"Intento {a}/{max_attempts} - esperando Master..."))
                
                if not self.master_running:
                    raise Exception("Master no respondió después de varios intentos")
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Error iniciando Master: {e}", "ERROR"))
                self.root.after(0, lambda: messagebox.showerror("Error", 
                    f"No se pudo iniciar el Master:\n{str(e)}"))
                if self.master_process:
                    self.master_process.terminate()
                    self.master_process = None
            
            finally:
                self.root.after(0, lambda: self.start_master_btn.config(state='normal'))
        
        threading.Thread(target=start, daemon=True).start()
    
    def open_web_api(self):
        """Abrir API Web para debates"""
        try:
            webbrowser.open('http://localhost:5173')
            self.log("API Web abierta en navegador")
        except Exception as e:
            self.log(f"Error abriendo API Web: {e}", "ERROR")
    
    def start_monitoring(self):
        """Iniciar monitor en tiempo real"""
        def monitor():
            while True:
                try:
                    # Actualizar treeview de monitor
                    self.update_monitor_tree()
                    time.sleep(5)
                except:
                    break
        
        threading.Thread(target=monitor, daemon=True).start()
        self.refresh_worker_ip()  # Iniciar verificación inicial
    
    def update_monitor_tree(self):
        """Actualizar treeview del monitor"""
        # Limpiar treeview
        for item in self.monitor_tree.get_children():
            self.monitor_tree.delete(item)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Worker
        worker_status = "🟢 Activo" if self.worker_connected else "🔴 Inactivo"
        worker_info = f"{self.worker_ip}" if self.worker_ip else "N/A"
        self.monitor_tree.insert('', 'end', values=(
            'Worker', worker_status, worker_info, timestamp
        ))
        
        # Master
        master_status = "🟢 Activo" if self.master_running else "🔴 Inactivo"
        master_info = "localhost:8000" if self.master_running else "N/A"
        self.monitor_tree.insert('', 'end', values=(
            'Master', master_status, master_info, timestamp
        ))
        
        # API Web
        api_status = "🟢 Activo" if self.web_api_running else "🔴 Inactivo"
        api_info = "localhost:5173" if self.web_api_running else "N/A"
        self.monitor_tree.insert('', 'end', values=(
            'API Web', api_status, api_info, timestamp
        ))
        
        # Ollama Worker
        ollama_w_status = "🟢 Activo" if self.ollama_worker_status else "🔴 Inactivo"
        ollama_w_info = f"{self.worker_ip}:11434" if self.worker_ip else "N/A"
        self.monitor_tree.insert('', 'end', values=(
            'Ollama Worker', ollama_w_status, ollama_w_info, timestamp
        ))
        
        # Ollama Master
        ollama_m_status = "🟢 Activo" if self.ollama_master_status else "🔴 Inactivo"
        self.monitor_tree.insert('', 'end', values=(
            'Ollama Master', ollama_m_status, "localhost:11434", timestamp
        ))
    
    def full_system_check(self):
        """Verificación completa del sistema"""
        self.log("Iniciando verificación completa del sistema...")
        
        def check():
            # Verificar Worker
            self.refresh_worker_ip()
            time.sleep(2)
            
            if self.worker_ip:
                ollama_ok, models = self.check_ollama_status(self.worker_ip)
                self.ollama_worker_status = ollama_ok
                self.log(f"Worker Ollama: {'OK' if ollama_ok else 'FAIL'} ({models} modelos)")
            
            # Verificar Master
            try:
                response = requests.get('http://localhost:8000/health', timeout=5)
                self.master_running = response.status_code == 200
                self.log(f"Master API: {'OK' if self.master_running else 'FAIL'}")
            except:
                self.master_running = False
                self.log("Master API: FAIL", "ERROR")
            
            # Verificar Ollama Master
            ollama_ok, models = self.check_ollama_status('localhost', 11434)
            self.ollama_master_status = ollama_ok
            self.log(f"Master Ollama: {'OK' if ollama_ok else 'FAIL'} ({models} modelos)")
            
            self.log("Verificación completa del sistema finalizada")
        
        threading.Thread(target=check, daemon=True).start()
    
    def clear_logs(self):
        """Limpiar logs"""
        self.logs_text.delete("1.0", tk.END)
        self.log("Logs limpiados")
    
    def save_logs(self):
        """Guardar logs a archivo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"synapse_logs_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write(self.logs_text.get("1.0", tk.END))
            self.log(f"Logs guardados en {filename}")
        except Exception as e:
            self.log(f"Error guardando logs: {e}", "ERROR")
    
    def export_status(self):
        """Exportar estado actual"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"synapse_status_{timestamp}.json"
        
        status = {
            "timestamp": timestamp,
            "worker": {
                "hostname": self.worker_var.get(),
                "ip": self.worker_ip,
                "connected": self.worker_connected,
                "ollama_status": self.ollama_worker_status
            },
            "master": {
                "running": self.master_running,
                "ollama_status": self.ollama_master_status
            },
            "api_web": {
                "running": self.web_api_running
            }
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(status, f, indent=2)
            self.log(f"Estado exportado a {filename}")
        except Exception as e:
            self.log(f"Error exportando estado: {e}", "ERROR")

def main():
    root = tk.Tk()
    app = SynapseControlApp(root)
    
    # Manejar cierre de ventana
    def on_closing():
        if app.master_process:
            app.master_process.terminate()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
