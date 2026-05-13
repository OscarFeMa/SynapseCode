"""
Synapse Dashboard v2.2 - Modo standalone
Usar SOLO para monitorear servidor ya iniciado.
Iniciar servidor aparte con: python backend/main.py
Compilar: pyinstaller --onefile --noconsole SynapseDashboard.py
"""
import sys, os, json, time, threading, webbrowser, subprocess, socket
from tkinter import ttk, messagebox
import tkinter as tk
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

API = "http://127.0.0.1:8000"

def server_alive():
    """Verifica si el puerto 8000 esta abierto (rapido, sin esperar health check)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        r = s.connect_ex(("127.0.0.1", 8000))
        s.close()
        return r == 0
    except:
        return False

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
    def __init__(self, parent, title, **kw):
        super().__init__(parent, bg="#1e293b", padx=10, pady=6, **kw)
        tk.Label(self, text=title, font=("Segoe UI", 8, "bold"),
                 fg="#94a3b8", bg="#1e293b").pack(anchor="w")
        self.lbl = tk.Label(self, text="⏳", font=("Segoe UI", 10),
                            fg="#cbd5e1", bg="#1e293b")
        self.lbl.pack(anchor="w")
        self.detail = tk.Label(self, text="", font=("Segoe UI", 7),
                               fg="#64748b", bg="#1e293b", wraplength=250)
        self.detail.pack(anchor="w")

    def set(self, status, text=""):
        c = {"ok":"#86efac","online":"#86efac","running":"#86efac","healthy":"#86efac",
             "error":"#fca5a5","offline":"#fca5a5","warning":"#fde68a","skip":"#cbd5e1"}
        self.lbl.config(text=f"{'✅' if status in ('ok','online','running','healthy') else '❌' if status in ('error','offline') else '⚠️'} {status.upper()}", fg=c.get(status,"#fca5a5"))
        self.detail.config(text=str(text)[:80])


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Synapse Dashboard v2.2")
        self.root.geometry("1200x750")
        self.root.configure(bg="#0f172a")
        self._build()
        self._loop()

    def _build(self):
        top = tk.Frame(self.root, bg="#1e293b", height=44)
        top.pack(fill="x")
        tk.Label(top, text=" Synapse Council", font=("Segoe UI", 15, "bold"),
                 fg="#f59e0b", bg="#1e293b").pack(side="left", padx=10)

        self.master_lbl = tk.Label(top, text="Master: ⏳", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b")
        self.master_lbl.pack(side="left", padx=12)
        self.worker_lbl = tk.Label(top, text="Worker: ⏳", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b")
        self.worker_lbl.pack(side="left", padx=12)

        tk.Button(top, text="🌐 API", command=lambda: webbrowser.open("http://localhost:8000/docs"),
                  bg="#2563eb", fg="white", relief="flat", padx=10).pack(side="right", padx=3)
        tk.Button(top, text="📊 Admin", command=lambda: webbrowser.open("http://localhost:8000/admin"),
                  bg="#2563eb", fg="white", relief="flat", padx=10).pack(side="right", padx=3)

        # ─── STATUS BAR ───────────────────────────────────
        bar = tk.Frame(self.root, bg="#0f172a")
        bar.pack(fill="x", padx=10, pady=5)

        self.srv_btn = tk.Button(bar, text="🔄 Verificar servidor", command=self.force_refresh,
                                 bg="#2563eb", fg="white", relief="flat", padx=12)
        self.srv_btn.pack(side="left", padx=2)

        self.status_lbl = tk.Label(bar, text="Verificando...", fg="#cbd5e1", bg="#0f172a", font=("Segoe UI", 8))
        self.status_lbl.pack(side="right", padx=10)

        # ─── NOTEBOOK ────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e293b", borderwidth=0)
        style.configure("TNotebook.Tab", background="#334155", foreground="#cbd5e1", padding=[10, 4])
        style.map("TNotebook.Tab", background=[("selected", "#2563eb")], foreground=[("selected", "white")])

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=5)

        # TAB 1: MONITOR
        t1 = tk.Frame(nb, bg="#0f172a")
        nb.add(t1, text="📊 Monitor")

        self.cards = {}
        for section, services in [
            ("MASTER", [("server","API Server"), ("db","Base Datos"), ("groq","Groq"), ("gemini","Gemini"), ("openrouter","OpenRouter"), ("webagent","Web Agent")]),
            ("WORKER", [("ollama","Ollama"), ("lmstudio","LM Studio"), ("jan","Jan"), ("ip","Worker IP")]),
        ]:
            tk.Label(t1, text=section, font=("Segoe UI", 11, "bold"), fg="#f59e0b", bg="#0f172a").pack(anchor="w", padx=10, pady=(10,2))
            row = tk.Frame(t1, bg="#0f172a")
            row.pack(fill="x", padx=10)
            for key, label in services:
                c = StatusCard(row, label)
                c.pack(side="left", padx=3, fill="x", expand=True)
                self.cards[key] = c

        # TAB 2: DEBATES
        t2 = tk.Frame(nb, bg="#0f172a")
        nb.add(t2, text="📋 Debates")
        tk.Label(t2, text="Historial de debates:", font=("Segoe UI", 11, "bold"),
                 fg="#e2e8f0", bg="#0f172a").pack(anchor="w", padx=10, pady=8)
        cols = ("topic","status","turns","tokens","mode","date")
        self.tree = ttk.Treeview(t2, columns=cols, show="headings", height=22)
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
        self.tree.column("topic", width=380)
        self.tree.column("status", width=80)
        self.tree.column("turns", width=50)
        self.tree.column("tokens", width=70)
        self.tree.column("mode", width=90)
        self.tree.column("date", width=140)
        self.tree.pack(fill="both", expand=True, padx=10)

        # TAB 3: METRICAS
        t3 = tk.Frame(nb, bg="#0f172a")
        nb.add(t3, text="📈 Metricas")
        self.metrics = tk.Text(t3, bg="#1e293b", fg="#cbd5e1", relief="flat", font=("Consolas", 10))
        self.metrics.pack(fill="both", expand=True, padx=10, pady=10)

        # FOOTER
        foot = tk.Frame(self.root, bg="#1e293b", height=22)
        foot.pack(fill="x")
        self.footer = tk.Label(foot, text="Dashboard solo lectura - Inicia el servidor aparte", font=("Segoe UI", 7), fg="#64748b", bg="#1e293b")
        self.footer.pack(side="left", padx=8)

    # ─── LOGICA ──────────────────────────────────────────
    def _status(self, key, status, text=""):
        if key in self.cards:
            self.cards[key].set(status, text)

    def _master(self, status, text=""):
        c = {"ok":"#86efac","error":"#fca5a5","checking":"#fde68a"}
        self.master_lbl.config(text=f"Master: {'●' if status=='ok' else '○'} {status.upper()}", fg=c.get(status,"#cbd5e1"))

    def _worker(self, status, text=""):
        c = {"ok":"#86efac","error":"#fca5a5","checking":"#fde68a"}
        self.worker_lbl.config(text=f"Worker: {'●' if status=='ok' else '○'} {status.upper()}", fg=c.get(status,"#cbd5e1"))

    def _refresh(self):
        alive = server_alive()
        if not alive:
            self._master("error", "Servidor no responde")
            self._worker("error", "Sin conexion")
            self.status_lbl.config(text="Servidor no responde", fg="#fca5a5")
            for k in self.cards:
                self.cards[k].set("error", "Desconectado")
            return

        self._master("ok")
        self.status_lbl.config(text="Conectado", fg="#86efac")

        # Health
        _, h = api("GET", "/health")
        svc = h.get("services", {})
        self._status("server", "ok", f"v{h.get('version','?')}")
        self._status("db", svc.get("database",{}).get("status","error"))

        for e in ["groq","gemini","openrouter"]:
            info = svc.get(e, {})
            st = info.get("status","error")
            if st == "online": self._status(e, "ok")
            elif st in ("skipped","unconfigured"): self._status(e, "skip", info.get("error","No config"))
            else: self._status(e, "error", info.get("error","")[:50])

        wa = svc.get("web_agent",{})
        self._status("webagent", "ok" if wa.get("status")=="available" else "skip")

        # Worker
        _, w = api("GET", "/api/v1/system/worker/services")
        ws = w.get("services", {})
        ip = w.get("worker_ip","?")
        self._status("ip", "ok" if ip!="?" else "error", f"IP: {ip}")

        all_ok = ip != "?"
        for name, key in [("ollama","ollama"),("lm_studio","lmstudio"),("jan","jan")]:
            info = ws.get(name, {})
            st = info.get("status","?")
            if st == "running":
                self._status(key, "ok", f"Puerto :{info.get('port','?')}")
            else:
                self._status(key, "error", f"Puerto :{info.get('port','?')}")
                all_ok = False

        self._worker("ok" if all_ok else "error", ip)

        # Debates
        _, d = api("GET", "/api/v1/debates/history/list")
        sessions = d.get("sessions", []) if d else []
        for item in self.tree.get_children():
            self.tree.delete(item)
        for s in sessions[-100:]:
            self.tree.insert("", "end", values=(
                s.get("topic","")[:80], s.get("status",""), s.get("total_turns",""),
                str(s.get("total_tokens_out",0)), s.get("mode",""), s.get("created_at","")[:16]
            ))

        # Metricas
        completed = [s for s in sessions if s.get("status")=="completed"]
        tt = sum(s.get("total_tokens_out",0) for s in completed)
        tm = sum(s.get("total_latency_ms",0) for s in completed)
        self.metrics.delete("1.0","end")
        self.metrics.insert("1.0", "\n".join([
            "═"*55, "  S Y N A P S E   M E T R I C S", "═"*55,
            f"  Debates completados: {len(completed)}",
            f"  Tokens totales: {tt:,}",
            f"  Tiempo total: {tm/1000:.1f}s",
            "═"*55]))

    def _loop(self):
        self._refresh()
        self.root.after(5000, self._loop)

    def force_refresh(self):
        self.status_lbl.config(text="Verificando...", fg="#fde68a")
        self._refresh()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    App().run()
