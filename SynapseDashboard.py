"""
Synapse Dashboard v2.2 - Desktop Control Center
Compilar: pyinstaller SynapseDashboard.spec
"""
import sys, os, json, time, threading, webbrowser, subprocess
from datetime import datetime
from tkinter import ttk, messagebox
import tkinter as tk
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ─── CONFIG ────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
API = "http://127.0.0.1:8000"
SERVER_CMD = [sys.executable, "-c",
    "import sys; sys.path.insert(0, '.'); from backend.main import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=8000, log_level='warning')"]

# ─── UTILS ─────────────────────────────────────────────────
def api(method, path, data=None):
    url = API + path
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers={"Content-Type":"application/json"}, method=method)
    try:
        r = urlopen(req, timeout=10)
        return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}

# ─── DASHBOARD APP ──────────────────────────────────────────
class SynapseDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Synapse Dashboard v2.2")
        self.root.geometry("1200x750")
        self.root.configure(bg="#0f172a")
        self.server_proc = None
        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        # ─── TOP BAR ───────────────────────────────────────
        top = tk.Frame(self.root, bg="#1e293b", height=50)
        top.pack(fill="x")
        tk.Label(top, text=" Synapse Council ", font=("Segoe UI", 14, "bold"),
                 fg="#f59e0b", bg="#1e293b").pack(side="left", padx=10)
        self.lbl_status = tk.Label(top, text="⏹ Detenido", font=("Segoe UI", 10),
                                   fg="#ef4444", bg="#1e293b")
        self.lbl_status.pack(side="right", padx=10)
        tk.Button(top, text="🌐 API Web", command=lambda: webbrowser.open("http://localhost:8000/docs"),
                  bg="#2563eb", fg="white", relief="flat", padx=8).pack(side="right", padx=5)
        tk.Button(top, text="📊 Admin", command=lambda: webbrowser.open("http://localhost:8000/admin"),
                  bg="#2563eb", fg="white", relief="flat", padx=8).pack(side="right", padx=5)

        # ─── CONTROL BAR ───────────────────────────────────
        ctrl = tk.Frame(self.root, bg="#0f172a")
        ctrl.pack(fill="x", padx=10, pady=5)
        self.btn_start = tk.Button(ctrl, text="▶ Iniciar Servidor", command=self.start_server,
                                   bg="#166534", fg="white", relief="flat", padx=12, font=("Segoe UI", 9, "bold"))
        self.btn_start.pack(side="left", padx=2)
        self.btn_stop = tk.Button(ctrl, text="⏹ Detener", command=self.stop_server,
                                  bg="#991b1b", fg="white", relief="flat", padx=12, state="disabled")
        self.btn_stop.pack(side="left", padx=2)
        tk.Button(ctrl, text="🔄 Refrescar", command=self.refresh_all,
                  bg="#334155", fg="white", relief="flat", padx=12).pack(side="left", padx=2)

        # ─── NOTEBOOK (TABS) ──────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e293b", borderwidth=0)
        style.configure("TNotebook.Tab", background="#334155", foreground="#cbd5e1", padding=[10, 4])
        style.map("TNotebook.Tab", background=[("selected", "#2563eb")], foreground=[("selected", "white")])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Tab 1: Monitor
        self.tab_monitor = tk.Frame(self.notebook, bg="#0f172a")
        self.notebook.add(self.tab_monitor, text="📊 Monitor")
        self._build_monitor()

        # Tab 2: Debates
        self.tab_debates = tk.Frame(self.notebook, bg="#0f172a")
        self.notebook.add(self.tab_debates, text="📋 Debates")
        self._build_debates()

        # Tab 3: Nuevo Debate
        self.tab_new = tk.Frame(self.notebook, bg="#0f172a")
        self.notebook.add(self.tab_new, text="➕ Nuevo Debate")
        self._build_new_debate()

        # Tab 4: Charts
        self.tab_charts = tk.Frame(self.notebook, bg="#0f172a")
        self.notebook.add(self.tab_charts, text="📈 Métricas")
        self._build_charts()

        # Tab 5: Worker
        self.tab_worker = tk.Frame(self.notebook, bg="#0f172a")
        self.notebook.add(self.tab_worker, text="🤖 Worker")
        self._build_worker()

        # ─── FOOTER ───────────────────────────────────────
        foot = tk.Frame(self.root, bg="#1e293b", height=25)
        foot.pack(fill="x")
        self.lbl_footer = tk.Label(foot, text="Listo", font=("Segoe UI", 8),
                                   fg="#64748b", bg="#1e293b")
        self.lbl_footer.pack(side="left", padx=10)

    def _build_monitor(self):
        canvas = tk.Canvas(self.tab_monitor, bg="#0f172a", highlightthickness=0)
        scroll = tk.Scrollbar(self.tab_monitor, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg="#0f172a")
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.monitor_frame = frame
        self.service_labels = {}

        # Grid para servicios
        self.monitor_grid = tk.Frame(frame, bg="#0f172a")
        self.monitor_grid.pack(fill="both", padx=10, pady=10)

        # Historial de debates (ultimos 10)
        tk.Label(frame, text="Últimos debates:", font=("Segoe UI", 10, "bold"),
                 fg="#e2e8f0", bg="#0f172a").pack(anchor="w", padx=10, pady=(20,5))
        self.history_tree = ttk.Treeview(frame, columns=("topic","status","turns","tokens","date"),
                                         show="headings", height=8)
        self.history_tree.heading("topic", text="Tema")
        self.history_tree.heading("status", text="Estado")
        self.history_tree.heading("turns", text="Turnos")
        self.history_tree.heading("tokens", text="Tokens")
        self.history_tree.heading("date", text="Fecha")
        self.history_tree.column("topic", width=300)
        self.history_tree.column("status", width=80)
        self.history_tree.column("turns", width=60)
        self.history_tree.column("tokens", width=80)
        self.history_tree.column("date", width=120)
        self.history_tree.pack(fill="x", padx=10, pady=5)
        self.history_tree.bind("<Double-1>", self._on_debate_click)

    def _build_debates(self):
        tk.Label(self.tab_debates, text="Historial completo de debates:",
                 font=("Segoe UI", 11, "bold"), fg="#e2e8f0", bg="#0f172a").pack(anchor="w", padx=10, pady=10)
        frame = tk.Frame(self.tab_debates, bg="#0f172a")
        frame.pack(fill="both", expand=True, padx=10)
        cols = ("topic","status","turnos","tokens","mode","creado")
        self.debates_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols:
            self.debates_tree.heading(c, text=c.capitalize())
        self.debates_tree.column("topic", width=350)
        self.debates_tree.column("status", width=80)
        self.debates_tree.column("turnos", width=60)
        self.debates_tree.column("tokens", width=80)
        self.debates_tree.column("mode", width=100)
        self.debates_tree.column("creado", width=150)
        self.debates_tree.pack(fill="both", expand=True)
        self.debates_tree.bind("<Double-1>", self._on_debate_click)

        btn_frame = tk.Frame(self.tab_debates, bg="#0f172a")
        btn_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(btn_frame, text="🔄 Recargar", command=self._load_history,
                  bg="#334155", fg="white", relief="flat").pack(side="left", padx=2)

    def _build_new_debate(self):
        frame = tk.Frame(self.tab_new, bg="#0f172a")
        frame.pack(padx=20, pady=20, anchor="nw")

        tk.Label(frame, text="Nuevo Debate", font=("Segoe UI", 14, "bold"),
                 fg="#f59e0b", bg="#0f172a").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,15))

        tk.Label(frame, text="Tema:", fg="#e2e8f0", bg="#0f172a").grid(row=1, column=0, sticky="w", pady=5)
        self.topic_entry = tk.Entry(frame, width=60, bg="#1e293b", fg="white", insertbackground="white")
        self.topic_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(frame, text="Modo:", fg="#e2e8f0", bg="#0f172a").grid(row=2, column=0, sticky="w", pady=5)
        self.mode_var = tk.StringVar(value="local_only")
        ttk.Combobox(frame, textvariable=self.mode_var,
                     values=["local_only","standard","ultra_crossing","iterative"],
                     width=20).grid(row=2, column=1, sticky="w", padx=10, pady=5)

        tk.Label(frame, text="Engine:", fg="#e2e8f0", bg="#0f172a").grid(row=3, column=0, sticky="w", pady=5)
        self.engine_var = tk.StringVar(value="groq")
        ttk.Combobox(frame, textvariable=self.engine_var,
                     values=["groq","gemini","ollama","lm_studio","huggingface"],
                     width=20).grid(row=3, column=1, sticky="w", padx=10, pady=5)

        tk.Label(frame, text="Modelo:", fg="#e2e8f0", bg="#0f172a").grid(row=4, column=0, sticky="w", pady=5)
        self.model_entry = tk.Entry(frame, width=40, bg="#1e293b", fg="white", insertbackground="white")
        self.model_entry.insert(0, "llama-3.1-8b-instant")
        self.model_entry.grid(row=4, column=1, sticky="w", padx=10, pady=5)

        tk.Button(frame, text="▶ Iniciar Debate", command=self._start_debate,
                  bg="#166534", fg="white", relief="flat", padx=20, pady=5,
                  font=("Segoe UI", 10, "bold")).grid(row=5, column=1, sticky="w", padx=10, pady=15)

        self.debate_result = tk.Text(frame, height=8, width=80, bg="#1e293b", fg="#86efac",
                                      relief="flat", font=("Consolas", 9))
        self.debate_result.grid(row=6, column=0, columnspan=2, pady=10)

    def _build_charts(self):
        tk.Label(self.tab_charts, text="Métricas de rendimiento",
                 font=("Segoe UI", 11, "bold"), fg="#e2e8f0", bg="#0f172a").pack(anchor="w", padx=10, pady=10)
        self.metrics_text = tk.Text(self.tab_charts, height=15, bg="#1e293b", fg="#cbd5e1",
                                     relief="flat", font=("Consolas", 10))
        self.metrics_text.pack(fill="both", expand=True, padx=10, pady=5)
        self._update_metrics()

    def _build_worker(self):
        frame = tk.Frame(self.tab_worker, bg="#0f172a")
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        tk.Label(frame, text="Worker Services", font=("Segoe UI", 14, "bold"),
                 fg="#f59e0b", bg="#0f172a").pack(anchor="w")

        self.worker_frame = tk.Frame(frame, bg="#0f172a")
        self.worker_frame.pack(fill="x", pady=10)

        tk.Button(frame, text="🔄 Refrescar Worker", command=self._refresh_worker,
                  bg="#334155", fg="white", relief="flat").pack(side="left", padx=2)
        tk.Button(frame, text="🚀 Lanzar todos los servicios", command=self._launch_worker_services,
                  bg="#166534", fg="white", relief="flat").pack(side="left", padx=2)

    # ─── METHODS ──────────────────────────────────────────
    def log(self, msg):
        self.lbl_footer.config(text=msg)

    def set_server_status(self, running):
        if running:
            self.lbl_status.config(text="▶ Corriendo", fg="#86efac")
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
        else:
            self.lbl_status.config(text="⏹ Detenido", fg="#ef4444")
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")

    def start_server(self):
        def run():
            self.server_proc = subprocess.Popen(SERVER_CMD, cwd=ROOT,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.root.after(100, lambda: self.set_server_status(True))
            self.log("Servidor iniciado")
        threading.Thread(target=run, daemon=True).start()

    def stop_server(self):
        if self.server_proc:
            self.server_proc.kill()
            self.server_proc = None
        self.set_server_status(False)
        self.log("Servidor detenido")

    def refresh_all(self):
        self._update_services()
        self._load_history()
        self._refresh_worker()
        self._update_metrics()
        self.root.after(30000, self.refresh_all)

    def _update_services(self):
        code, data = api("GET", "/health")
        if code == 0:
            self.set_server_status(False)
            return
        self.set_server_status(True)
        svc = data.get("services", {})

        # Limpiar grid
        for w in self.monitor_grid.winfo_children():
            w.destroy()

        row = 0
        col = 0
        for name, info in svc.items():
            card = tk.Frame(self.monitor_grid, bg="#1e293b", relief="flat", bd=1, padx=10, pady=8)
            card.grid(row=row//3, column=col, sticky="nsew", padx=5, pady=5)

            status = info.get("status", "unknown")
            color = {"healthy":"#86efac","online":"#86efac","available":"#86efac",
                     "error":"#fca5a5","unavailable":"#fca5a5","offline":"#fca5a5",
                     "skipped":"#cbd5e1","disabled":"#64748b"}.get(status, "#fde68a")

            tk.Label(card, text=name.upper(), font=("Segoe UI", 8, "bold"),
                     fg="#94a3b8", bg="#1e293b").pack(anchor="w")
            tk.Label(card, text=f"● {status}", font=("Segoe UI", 10),
                     fg=color, bg="#1e293b").pack(anchor="w")

            models = info.get("models") or info.get("free_models")
            if models:
                if isinstance(models, list) and models:
                    tk.Label(card, text=f"Modelos: {len(models)}", font=("Segoe UI", 8),
                             fg="#64748b", bg="#1e293b").pack(anchor="w")

            error = info.get("error", "")
            if error and error != "None":
                tk.Label(card, text=error[:40], font=("Segoe UI", 7),
                         fg="#fca5a5", bg="#1e293b", wraplength=200).pack(anchor="w")

            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _load_history(self):
        code, data = api("GET", "/api/v1/debates/history/list")
        sessions = data.get("sessions", []) if code == 200 else []

        # Limpiar trees
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for item in self.debates_tree.get_children():
            self.debates_tree.delete(item)

        for s in sessions[-50:]:
            vals = (s.get("topic","")[:60], s.get("status",""), s.get("total_turns",""),
                    str(s.get("total_tokens_out",0)), s.get("created_at","")[:10])
            self.history_tree.insert("", "end", values=vals)
            vals2 = (s.get("topic","")[:80], s.get("status",""), s.get("total_turns",""),
                     str(s.get("total_tokens_out",0)), s.get("mode",""), s.get("created_at","")[:16])
            self.debates_tree.insert("", "end", values=vals2)

    def _on_debate_click(self, event):
        # Abrir el debate en el admin panel
        webbrowser.open("http://localhost:8000/admin")

    def _start_debate(self):
        topic = self.topic_entry.get().strip()
        if not topic:
            messagebox.showwarning("Tema requerido", "Ingresa un tema para el debate")
            return
        data = {"topic": topic, "mode": self.mode_var.get()}
        self.debate_result.delete("1.0", "end")
        self.debate_result.insert("1.0", "Iniciando debate...\n")
        self.root.update()

        def run():
            code, resp = api("POST", "/api/v1/debates/create", data)
            self.root.after(0, lambda: self._show_result(code, resp))
        threading.Thread(target=run, daemon=True).start()

    def _show_result(self, code, resp):
        self.debate_result.delete("1.0", "end")
        if code in (200, 202):
            sid = resp.get("session_id", "?")
            self.debate_result.insert("1.0", f"✅ Debate creado\nID: {sid}\nEstado: {resp.get('status')}\nTurnos: {resp.get('total_turns')}\n\n")
            self.debate_result.insert("end", f"Ver en: http://localhost:8000/admin")
        else:
            self.debate_result.insert("1.0", f"❌ Error: {resp.get('detail', str(resp))}")

    def _refresh_worker(self):
        for w in self.worker_frame.winfo_children():
            w.destroy()
        code, data = api("GET", "/api/v1/system/worker/services")
        if code != 200:
            tk.Label(self.worker_frame, text="Worker no accesible", fg="#fca5a5",
                     bg="#0f172a").pack()
            return
        svc = data.get("services", {})
        tk.Label(self.worker_frame, text=f"IP: {data.get('worker_ip','?')}",
                 fg="#cbd5e1", bg="#0f172a").pack(anchor="w")
        for name, info in svc.items():
            st = info.get("status", "?")
            port = info.get("port", "?")
            color = "#86efac" if st == "running" else "#fca5a5"
            tk.Label(self.worker_frame, text=f"  {name}: ● {st} (:{port})",
                     fg=color, bg="#0f172a").pack(anchor="w")

    def _launch_worker_services(self):
        """Lanza todos los servicios del Worker via API"""
        def run():
            code, resp = api("POST", "/api/v1/system/worker/services/launch", {"service": "all"})
            self.root.after(0, lambda: self.log(f"Worker: {resp.get('success', 'error')}"))
            self.root.after(0, self._refresh_worker)
        threading.Thread(target=run, daemon=True).start()

    def _update_metrics(self):
        self.metrics_text.delete("1.0", "end")
        code, data = api("GET", "/api/v1/debates/history/list")
        if code != 200:
            self.metrics_text.insert("1.0", "No hay datos disponibles")
            return
        sessions = data.get("sessions", [])

        completed = [s for s in sessions if s.get("status") == "completed"]
        total_tokens = sum(s.get("total_tokens_out", 0) for s in completed)
        total_time = sum(s.get("total_latency_ms", 0) for s in completed)
        total_turns = sum(s.get("total_turns", 0) for s in completed)

        lines = [
            "═" * 50,
            f"  DEBATES COMPLETADOS:  {len(completed)}",
            f"  TOTAL TOKENS GENERADOS: {total_tokens:,}",
            f"  TOTAL TURNOS:          {total_turns}",
            f"  TIEMPO TOTAL:          {total_time/1000:.1f}s",
            f"  PROMEDIO TOKENS/TURNO: {total_tokens//max(total_turns,1):,}",
            f"  PROMEDIO TIEMPO/DEBATE: {total_time/max(len(completed),1)/1000:.1f}s",
            "═" * 50,
        ]

        if completed:
            # Top 5 debates por tokens
            top = sorted(completed, key=lambda s: s.get("total_tokens_out",0), reverse=True)[:5]
            lines.append("\n  TOP 5 DEBATES (por tokens):")
            for i, s in enumerate(top, 1):
                lines.append(f"  {i}. {s.get('topic','?')[:50]}")
                lines.append(f"     Tokens: {s.get('total_tokens_out',0):,} | Turnos: {s.get('total_turns',0)}")

        self.metrics_text.insert("1.0", "\n".join(lines))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    SynapseDashboard().run()
