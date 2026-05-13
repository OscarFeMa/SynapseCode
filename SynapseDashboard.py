"""
Synapse Dashboard v2.2 - Desktop Control Center
Monitor en tiempo real de Master + Worker
Compilar: pyinstaller SynapseDashboard.spec
"""
import sys, os, json, time, threading, webbrowser, subprocess
from datetime import datetime
from tkinter import ttk, messagebox
import tkinter as tk
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT = os.path.dirname(os.path.abspath(__file__))
API = "http://127.0.0.1:8000"

# Detectar si estamos compilados (PyInstaller) o en desarrollo
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Compilado como .exe - buscar python en PATH o ubicaciones comunes
    _python = None
    for _p in [os.environ.get('PYTHONPATH', ''), 
               r'C:\Users\usuario\AppData\Local\Programs\Python\Python312\python.exe',
               r'C:\Users\maked\AppData\Local\Programs\Python\Python312\python.exe',
               r'C:\Python312\python.exe',
               r'C:\Python311\python.exe']:
        if _p and os.path.exists(_p):
            _python = _p
            break
    if not _python:
        # Intentar buscar python en PATH
        import shutil
        _python = shutil.which('python') or shutil.which('python3') or 'python'
    _py = _python
else:
    _py = sys.executable

SERVER_CMD = [_py, "-c",
    "import sys; sys.path.insert(0, '.'); from backend.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000, log_level='warning')"]

def api(method, path, data=None, timeout=5):
    url = API + path
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers={"Content-Type":"application/json"}, method=method)
    try:
        r = urlopen(req, timeout=timeout)
        return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}

class StatusCard(tk.Frame):
    """Tarjeta de estado para un servicio"""
    def __init__(self, parent, title, **kw):
        super().__init__(parent, bg="#1e293b", padx=12, pady=8, **kw)
        self.title = title
        tk.Label(self, text=title, font=("Segoe UI", 8, "bold"),
                 fg="#94a3b8", bg="#1e293b").pack(anchor="w")
        self.lbl_status = tk.Label(self, text="⏳ Verificando...", font=("Segoe UI", 10),
                                   fg="#cbd5e1", bg="#1e293b")
        self.lbl_status.pack(anchor="w")
        self.lbl_detail = tk.Label(self, text="", font=("Segoe UI", 7),
                                   fg="#64748b", bg="#1e293b", wraplength=250)
        self.lbl_detail.pack(anchor="w")

    def set_status(self, status, detail=""):
        colors = {"ok":"#86efac","online":"#86efac","running":"#86efac","healthy":"#86efac",
                  "error":"#fca5a5","offline":"#fca5a5","stopped":"#fca5a5",
                  "warning":"#fde68a","pending":"#fde68a","checking":"#cbd5e1"}
        c = colors.get(status, "#fca5a5")
        icons = {"ok":"✅","online":"✅","running":"✅","healthy":"✅",
                 "error":"❌","offline":"❌","stopped":"❌",
                 "warning":"⚠️","pending":"⏳","checking":"🔄"}
        icon = icons.get(status, "❓")
        self.lbl_status.config(text=f"{icon} {status.upper()}", fg=c)
        self.lbl_detail.config(text=detail[:80] if detail else "")


class SynapseDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Synapse Dashboard v2.2")
        self.root.geometry("1300x800")
        self.root.configure(bg="#0f172a")
        self.server_proc = None
        self._server_ready = False
        self._monitor_active = False
        self._build_ui()
        self.after_id = None
        self.start_monitor()

    def _build_ui(self):
        # ─── TOP BAR ───────────────────────────────────────
        top = tk.Frame(self.root, bg="#1e293b", height=48)
        top.pack(fill="x")
        tk.Label(top, text="  Synapse Council", font=("Segoe UI", 16, "bold"),
                 fg="#f59e0b", bg="#1e293b").pack(side="left", padx=10)

        self.lbl_master = tk.Label(top, text="Master: ⏳", font=("Segoe UI", 9, "bold"),
                                   fg="#cbd5e1", bg="#1e293b")
        self.lbl_master.pack(side="left", padx=15)
        self.lbl_worker = tk.Label(top, text="Worker: ⏳", font=("Segoe UI", 9, "bold"),
                                   fg="#cbd5e1", bg="#1e293b")
        self.lbl_worker.pack(side="left", padx=15)

        tk.Button(top, text="🌐 API", command=lambda: webbrowser.open("http://localhost:8000/docs"),
                  bg="#2563eb", fg="white", relief="flat", padx=10).pack(side="right", padx=5)
        tk.Button(top, text="📊 Admin", command=lambda: webbrowser.open("http://localhost:8000/admin"),
                  bg="#2563eb", fg="white", relief="flat", padx=10).pack(side="right", padx=5)

        # ─── CONTROL BAR ───────────────────────────────────
        ctrl = tk.Frame(self.root, bg="#0f172a")
        ctrl.pack(fill="x", padx=10, pady=5)
        self.btn_start = tk.Button(ctrl, text="▶ Iniciar Servidor", command=self.start_server,
                                   bg="#166534", fg="white", relief="flat", padx=14, font=("Segoe UI", 9, "bold"))
        self.btn_start.pack(side="left", padx=2)
        self.btn_stop = tk.Button(ctrl, text="⏹ Detener", command=self.stop_server,
                                  bg="#991b1b", fg="white", relief="flat", padx=14, state="disabled")
        self.btn_stop.pack(side="left", padx=2)
        tk.Button(ctrl, text="🔄 Refrescar", command=self.refresh_all,
                  bg="#334155", fg="white", relief="flat", padx=12).pack(side="left", padx=2)

        self.lbl_status = tk.Label(ctrl, text="Detenido", fg="#64748b", bg="#0f172a",
                                    font=("Segoe UI", 8))
        self.lbl_status.pack(side="right", padx=10)

        # ─── NOTEBOOK ─────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e293b", borderwidth=0)
        style.configure("TNotebook.Tab", background="#334155", foreground="#cbd5e1", padding=[10, 4])
        style.map("TNotebook.Tab", background=[("selected", "#2563eb")], foreground=[("selected", "white")])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Tab 1: Monitor principal
        self.tab_monitor = tk.Frame(self.notebook, bg="#0f172a")
        self.notebook.add(self.tab_monitor, text="📊 Monitor")

        # Grid de servicios Master
        tk.Label(self.tab_monitor, text="MASTER", font=("Segoe UI", 12, "bold"),
                 fg="#f59e0b", bg="#0f172a").pack(anchor="w", padx=10, pady=(10,5))
        self.master_frame = tk.Frame(self.tab_monitor, bg="#0f172a")
        self.master_frame.pack(fill="x", padx=10)

        self.cards = {}
        services = [
            ("server","Servidor API"), ("database","Base de Datos"),
            ("groq","Groq Cloud"), ("gemini","Gemini"),
            ("openrouter","OpenRouter"), ("web_agent","Web Agent"),
        ]
        row_frame = None
        for i, (key, label) in enumerate(services):
            if i % 3 == 0:
                row_frame = tk.Frame(self.master_frame, bg="#0f172a")
                row_frame.pack(fill="x", pady=2)
            card = StatusCard(row_frame, label)
            card.pack(side="left", padx=4, fill="x", expand=True)
            self.cards[key] = card

        # Worker section
        tk.Label(self.tab_monitor, text="WORKER", font=("Segoe UI", 12, "bold"),
                 fg="#f59e0b", bg="#0f172a").pack(anchor="w", padx=10, pady=(20,5))
        self.worker_frame = tk.Frame(self.tab_monitor, bg="#0f172a")
        self.worker_frame.pack(fill="x", padx=10)

        worker_services = [
            ("ollama","Ollama"), ("lm_studio","LM Studio"),
            ("jan","Jan"), ("worker_ip","Worker IP"),
        ]
        row_frame = None
        for i, (key, label) in enumerate(worker_services):
            if i % 4 == 0:
                row_frame = tk.Frame(self.worker_frame, bg="#0f172a")
                row_frame.pack(fill="x", pady=2)
            card = StatusCard(row_frame, label)
            card.pack(side="left", padx=4, fill="x", expand=True)
            self.cards[key] = card

        # Botones Worker
        btn_frame = tk.Frame(self.tab_monitor, bg="#0f172a")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="🚀 Lanzar todos los servicios en Worker",
                  command=self._launch_worker_services,
                  bg="#166534", fg="white", relief="flat", padx=20, pady=6).pack()

        # ─── TAB 2: DEBATES ──────────────────────────────
        self.tab_debates = tk.Frame(self.notebook, bg="#0f172a")
        self.notebook.add(self.tab_debates, text="📋 Debates")

        tk.Label(self.tab_debates, text="Historial de debates:", font=("Segoe UI", 11, "bold"),
                 fg="#e2e8f0", bg="#0f172a").pack(anchor="w", padx=10, pady=10)

        cols = ("topic","status","turnos","tokens","mode","fecha")
        self.debates_tree = ttk.Treeview(self.tab_debates, columns=cols, show="headings", height=20)
        for c in cols:
            self.debates_tree.heading(c, text=c.capitalize())
        self.debates_tree.column("topic", width=400)
        self.debates_tree.column("status", width=80)
        self.debates_tree.column("turnos", width=60)
        self.debates_tree.column("tokens", width=80)
        self.debates_tree.column("mode", width=100)
        self.debates_tree.column("fecha", width=160)
        self.debates_tree.pack(fill="both", expand=True, padx=10)

        # ─── TAB 3: NUEVO DEBATE ─────────────────────────
        self.tab_new = tk.Frame(self.notebook, bg="#0f172a")
        self.notebook.add(self.tab_new, text="➕ Nuevo Debate")

        f = tk.Frame(self.tab_new, bg="#0f172a")
        f.pack(padx=20, pady=20, anchor="nw")

        tk.Label(f, text="Tema:", fg="#e2e8f0", bg="#0f172a").grid(row=0, column=0, sticky="w", pady=5)
        self.topic_entry = tk.Entry(f, width=60, bg="#1e293b", fg="white", insertbackground="white")
        self.topic_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(f, text="Modo:", fg="#e2e8f0", bg="#0f172a").grid(row=1, column=0, sticky="w", pady=5)
        self.mode_var = tk.StringVar(value="local_only")
        ttk.Combobox(f, textvariable=self.mode_var,
                     values=["local_only","standard","ultra_crossing","iterative"],
                     width=20).grid(row=1, column=1, sticky="w", padx=10, pady=5)

        tk.Label(f, text="Engine:", fg="#e2e8f0", bg="#0f172a").grid(row=2, column=0, sticky="w", pady=5)
        self.engine_var = tk.StringVar(value="groq")
        ttk.Combobox(f, textvariable=self.engine_var,
                     values=["groq","gemini","ollama","lm_studio","huggingface"],
                     width=20).grid(row=2, column=1, sticky="w", padx=10, pady=5)

        tk.Label(f, text="Modelo:", fg="#e2e8f0", bg="#0f172a").grid(row=3, column=0, sticky="w", pady=5)
        self.model_entry = tk.Entry(f, width=40, bg="#1e293b", fg="white", insertbackground="white")
        self.model_entry.insert(0, "llama-3.1-8b-instant")
        self.model_entry.grid(row=3, column=1, sticky="w", padx=10, pady=5)

        btn = tk.Button(f, text="▶ Iniciar Debate", command=self._start_debate,
                        bg="#166534", fg="white", relief="flat", padx=20, pady=5,
                        font=("Segoe UI", 10, "bold"))
        btn.grid(row=4, column=1, sticky="w", padx=10, pady=15)

        self.debate_result = tk.Text(f, height=8, width=80, bg="#1e293b", fg="#86efac",
                                      relief="flat", font=("Consolas", 9))
        self.debate_result.grid(row=5, column=0, columnspan=2, pady=10)

        # ─── TAB 4: MÉTRICAS ─────────────────────────────
        self.tab_charts = tk.Frame(self.notebook, bg="#0f172a")
        self.notebook.add(self.tab_charts, text="📈 Métricas")
        self.metrics_text = tk.Text(self.tab_charts, height=20, bg="#1e293b", fg="#cbd5e1",
                                     relief="flat", font=("Consolas", 10))
        self.metrics_text.pack(fill="both", expand=True, padx=10, pady=10)

        # ─── FOOTER ───────────────────────────────────────
        foot = tk.Frame(self.root, bg="#1e293b", height=24)
        foot.pack(fill="x")
        self.lbl_footer = tk.Label(foot, text="Iniciando monitoreo...", font=("Segoe UI", 8),
                                   fg="#64748b", bg="#1e293b")
        self.lbl_footer.pack(side="left", padx=10)

    # ═══════════════════════════════════════════════════
    # MONITOR EN TIEMPO REAL
    # ═══════════════════════════════════════════════════
    def start_monitor(self):
        """Inicia el loop de monitoreo en tiempo real"""
        self._monitor_active = True
        self._monitor_loop()

    def _monitor_loop(self):
        if not self._monitor_active:
            return
        try:
            self._check_master()
            self._check_worker()
            self._load_history()
            self._update_metrics_text()
        except:
            pass
        self.after_id = self.root.after(5000, self._monitor_loop)

    def _set_master_status(self, status, detail=""):
        colors = {"ok":"#86efac","error":"#fca5a5","checking":"#fde68a"}
        c = colors.get(status, "#cbd5e1")
        self.lbl_master.config(text=f"Master: {'●' if status=='ok' else '○'} {status.upper()}", fg=c)

    def _set_worker_status(self, status, detail=""):
        colors = {"ok":"#86efac","error":"#fca5a5","checking":"#fde68a"}
        c = colors.get(status, "#cbd5e1")
        self.lbl_worker.config(text=f"Worker: {'●' if status=='ok' else '○'} {status.upper()}", fg=c)

    def _check_master(self):
        code, data = api("GET", "/health")
        if code != 200:
            self._set_master_status("error", "Servidor no responde")
            for k in self.cards:
                if k in ("ollama","lm_studio","jan","worker_ip"):
                    continue
                self.cards[k].set_status("error", "Servidor detenido")
            self._server_ready = False
            return

        self._server_ready = True
        self._set_master_status("ok", "Corriendo")

        svc = data.get("services", {})
        self.cards["server"].set_status("ok", f"v{data.get('version','?')} | {data.get('status','?')}")
        self.cards["database"].set_status(svc.get("database",{}).get("status","error"), "SQLite")

        for engine in ["groq","gemini","openrouter"]:
            info = svc.get(engine, {})
            st = info.get("status", "error")
            detail = info.get("error","") or ""
            if st == "online":
                self.cards[engine].set_status("ok", "API key valida")
            elif st == "skipped" or st == "unconfigured":
                self.cards[engine].set_status("warning", info.get("error","No configurado"))
            else:
                self.cards[engine].set_status("error", detail[:50])

        wa = svc.get("web_agent", {})
        self.cards["web_agent"].set_status("ok" if wa.get("status")=="available" else "warning",
                                           f"{len(wa.get('sites',[]))} sitios" if wa.get("sites") else wa.get("error",""))

    def _check_worker(self):
        if not self._server_ready:
            self._set_worker_status("error", "Master no disponible")
            return

        code, data = api("GET", "/api/v1/system/worker/services")
        if code != 200:
            self._set_worker_status("error", "No se pudo contactar Worker")
            for k in ["ollama","lm_studio","jan","worker_ip"]:
                self.cards[k].set_status("error", "Sin conexion")
            return

        svc = data.get("services", {})
        ip = data.get("worker_ip", "?")
        self.cards["worker_ip"].set_status("ok" if ip != "?" else "error", f"IP: {ip}")

        all_ok = True
        for name, info in svc.items():
            st = info.get("status", "?")
            port = info.get("port", "?")
            if name in self.cards:
                if st == "running":
                    self.cards[name].set_status("ok", f"Puerto :{port}")
                else:
                    self.cards[name].set_status("error", f"Puerto :{port}")
                    all_ok = False

        self._set_worker_status("ok" if all_ok else "error", ip)

    def _launch_worker_services(self):
        def run():
            self.lbl_footer.config(text="Lanzando servicios del Worker...")
            code, resp = api("POST", "/api/v1/system/worker/services/launch",
                           {"service": "all"}, timeout=30)
            self.root.after(0, lambda: self.lbl_footer.config(
                text=f"Worker: {'OK' if resp.get('success') else 'Fallos detectados'}"))
            self.root.after(1000, self._check_worker)
        threading.Thread(target=run, daemon=True).start()

    # ═══════════════════════════════════════════════════
    # CONTROL DEL SERVIDOR
    # ═══════════════════════════════════════════════════
    def start_server(self):
        self.lbl_status.config(text="Iniciando...", fg="#fde68a")
        self.btn_start.config(state="disabled")
        self.cards["server"].set_status("pending", "Arrancando...")
        def run():
            self.server_proc = subprocess.Popen(SERVER_CMD, cwd=ROOT,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Esperar a que el servidor arranque (hasta 15s)
            for _ in range(15):
                try:
                    urlopen("http://127.0.0.1:8000/health", timeout=1)
                    break
                except:
                    time.sleep(1)
            self.root.after(0, self._post_start)
        threading.Thread(target=run, daemon=True).start()

    def _post_start(self):
        self.lbl_status.config(text="Corriendo", fg="#86efac")
        self.btn_stop.config(state="normal")
        self._check_master()
        self._check_worker()

    def stop_server(self):
        if self.server_proc:
            self.server_proc.kill()
            self.server_proc = None
        self._server_ready = False
        self.lbl_status.config(text="Detenido", fg="#64748b")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self._set_master_status("error", "Detenido")
        self._set_worker_status("error", "Detenido")

    def refresh_all(self):
        self._check_master()
        self._check_worker()
        self._load_history()
        self._update_metrics_text()

    # ═══════════════════════════════════════════════════
    # DEBATES
    # ═══════════════════════════════════════════════════
    def _load_history(self):
        code, data = api("GET", "/api/v1/debates/history/list")
        sessions = data.get("sessions", []) if code == 200 else []
        for item in self.debates_tree.get_children():
            self.debates_tree.delete(item)
        for s in sessions[-100:]:
            self.debates_tree.insert("", "end", values=(
                s.get("topic","")[:80], s.get("status",""), s.get("total_turns",""),
                str(s.get("total_tokens_out",0)), s.get("mode",""), s.get("created_at","")[:16]
            ))

    def _start_debate(self):
        topic = self.topic_entry.get().strip()
        if not topic:
            messagebox.showwarning("Tema requerido", "Ingresa un tema")
            return
        data = {"topic": topic, "mode": self.mode_var.get()}
        self.debate_result.delete("1.0", "end")
        self.debate_result.insert("1.0", "Iniciando debate...\n")
        def run():
            code, resp = api("POST", "/api/v1/debates/create", data, timeout=15)
            self.root.after(0, lambda: self._show_result(code, resp))
        threading.Thread(target=run, daemon=True).start()

    def _show_result(self, code, resp):
        self.debate_result.delete("1.0", "end")
        if code in (200, 202):
            self.debate_result.insert("1.0", f"✅ Debate creado\nID: {resp.get('session_id')}\nEstado: {resp.get('status')}\nTurnos: {resp.get('total_turns')}")
        else:
            self.debate_result.insert("1.0", f"❌ Error: {resp.get('detail', str(resp)[:200])}")

    def _update_metrics_text(self):
        code, data = api("GET", "/api/v1/debates/history/list")
        if code != 200:
            self.metrics_text.delete("1.0", "end")
            self.metrics_text.insert("1.0", "Esperando servidor...")
            return
        sessions = data.get("sessions", [])
        completed = [s for s in sessions if s.get("status") == "completed"]
        total_tokens = sum(s.get("total_tokens_out", 0) for s in completed)
        total_time = sum(s.get("total_latency_ms", 0) for s in completed)
        total_turns = sum(s.get("total_turns", 0) for s in completed)

        lines = [
            "═" * 55,
            "  S Y N A P S E   M E T R I C S",
            "═" * 55,
            f"  Debates completados:  {len(completed)}",
            f"  Total tokens:         {total_tokens:,}",
            f"  Total turnos:         {total_turns}",
            f"  Tiempo total:         {total_time/1000:.1f}s",
            f"  Promedio tokens/turno: {total_tokens//max(total_turns,1):,}",
            f"  Promedio tiempo/debate: {total_time/max(len(completed),1)/1000:.1f}s",
            "═" * 55,
        ]
        if completed:
            top = sorted(completed, key=lambda s: s.get("total_tokens_out",0), reverse=True)[:5]
            lines.append("\n  TOP 5 DEBATES (por tokens):")
            for i, s in enumerate(top, 1):
                lines.append(f"  {i}. {s.get('topic','?')[:55]}")
                lines.append(f"     Tokens: {s.get('total_tokens_out',0):,} | Turnos: {s.get('total_turns',0)}")
        self.metrics_text.delete("1.0", "end")
        self.metrics_text.insert("1.0", "\n".join(lines))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    SynapseDashboard().run()
