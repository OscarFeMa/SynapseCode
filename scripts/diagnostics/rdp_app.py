#!/usr/bin/env python3
"""
RDP Worker Connector - Aplicación Simple
Conecta automáticamente al Worker vía RDP con IP dinámica
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
import socket
import subprocess
import threading
import time

class RDPWorkerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RDP Worker Connector")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # Configuración (usar variables de entorno en producción)
        self.worker_hostname = "makederpc"
        self.username = os.environ.get("WORKER_USERNAME", "<WORKER_USERNAME>")
        self.password = os.environ.get("WORKER_PASSWORD", "<WORKER_PASSWORD>")
        
        # Variables
        self.current_ip = None
        self.is_connecting = False
        
        self.setup_ui()
        self.resolve_ip()
    
    def setup_ui(self):
        """Configurar la interfaz de usuario"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Título
        title_label = ttk.Label(main_frame, text="RDP Worker Connector", 
                                font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Información del Worker
        info_frame = ttk.LabelFrame(main_frame, text="Información del Worker", padding="10")
        info_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Hostname
        ttk.Label(info_frame, text="Hostname:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.hostname_label = ttk.Label(info_frame, text=self.worker_hostname, 
                                       font=("Arial", 10, "bold"))
        self.hostname_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # IP
        ttk.Label(info_frame, text="IP:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.ip_label = ttk.Label(info_frame, text="Resolviendo...", 
                                 font=("Arial", 10, "bold"), foreground="orange")
        self.ip_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Estado
        ttk.Label(info_frame, text="Estado:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.status_label = ttk.Label(info_frame, text="Listo", 
                                     font=("Arial", 10, "bold"), foreground="green")
        self.status_label.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Botón de conexión
        self.connect_button = ttk.Button(main_frame, text="🖥️ Conectar al Worker", 
                                        command=self.connect_worker,
                                        style="Accent.TButton")
        self.connect_button.grid(row=2, column=0, columnspan=2, pady=20, sticky=(tk.W, tk.E))
        
        # Botón de refrescar IP
        refresh_button = ttk.Button(main_frame, text="🔄 Refrescar IP", 
                                   command=self.resolve_ip)
        refresh_button.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        # Configurar estilo del botón principal
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 12, "bold"), padding=10)
        
        # Barra de estado
        self.status_bar = ttk.Label(main_frame, text="Listo para conectar", 
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def resolve_ip(self):
        """Resolver IP del Worker"""
        def resolve():
            try:
                self.update_status("Resolviendo IP...", "orange")
                ip = socket.gethostbyname(self.worker_hostname)
                self.current_ip = ip
                self.root.after(0, lambda: self.ip_label.config(text=ip, foreground="green"))
                self.root.after(0, lambda: self.update_status(f"IP resuelta: {ip}", "green"))
            except socket.gaierror:
                self.current_ip = None
                self.root.after(0, lambda: self.ip_label.config(text="No encontrado", foreground="red"))
                self.root.after(0, lambda: self.update_status("No se pudo resolver el hostname", "red"))
        
        # Ejecutar en hilo separado para no bloquear la UI
        threading.Thread(target=resolve, daemon=True).start()
    
    def connect_worker(self):
        """Conectar al Worker vía RDP"""
        if self.is_connecting:
            return
        
        if not self.current_ip:
            messagebox.showerror("Error", "No se pudo resolver la IP del Worker")
            return
        
        self.is_connecting = True
        self.connect_button.config(state="disabled")
        self.update_status("Conectando...", "orange")
        
        def connect():
            try:
                # Guardar credenciales
                cmdkey_cmd = [
                    'cmdkey', 
                    '/generic:TERMSRV/' + self.current_ip,
                    '/user:' + self.username,
                    '/pass:' + self.password
                ]
                
                result = subprocess.run(cmdkey_cmd, capture_output=True, text=True)
                
                # Crear archivo .rdp
                rdp_content = f"""full address:s:{self.current_ip}
username:s:{self.username}
domain:s:MAKEDER
screen mode id:i:2
use multimon:i:1
session bpp:i:32
authentication level:i:2
prompt for credentials:i:0
redirectdrives:i:1
redirectprinters:i:1
redirectclipboard:i:1
"""
                
                rdp_file = f"worker_{self.current_ip.replace('.', '_')}.rdp"
                with open(rdp_file, 'w') as f:
                    f.write(rdp_content)
                
                # Abrir RDP
                subprocess.Popen(['mstsc', rdp_file])
                
                self.root.after(0, lambda: self.update_status(f"Conectado a {self.current_ip}", "green"))
                self.root.after(0, lambda: messagebox.showinfo("Éxito", 
                    f"Conexión RDP iniciada hacia {self.current_ip}\n\n"
                    f"Deberías ver la ventana de Escritorio Remoto."))
                
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"Error: {str(e)}", "red"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"No se pudo conectar: {str(e)}"))
            
            finally:
                self.is_connecting = False
                self.root.after(0, lambda: self.connect_button.config(state="normal"))
        
        # Ejecutar en hilo separado
        threading.Thread(target=connect, daemon=True).start()
    
    def update_status(self, message, color="black"):
        """Actualizar barra de estado"""
        self.status_bar.config(text=message)
        if color == "green":
            self.status_label.config(text="Conectado", foreground="green")
        elif color == "orange":
            self.status_label.config(text="Procesando", foreground="orange")
        elif color == "red":
            self.status_label.config(text="Error", foreground="red")
        else:
            self.status_label.config(text="Listo", foreground="green")

def main():
    root = tk.Tk()
    app = RDPWorkerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
