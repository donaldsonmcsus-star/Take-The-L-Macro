"""
Take The L Macro - Webhook routing proxy for Oyster Detector
"""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "TakeTheLMacro", "config.json"
)

DEFAULT_CONFIG = {
    "port": 5050,
    "routes": {
        "Biome":    {"url": "", "enabled": True,  "label": "Biomes"},
        "Aura":     {"url": "", "enabled": True,  "label": "Auras"},
        "Merchant": {"url": "", "enabled": True,  "label": "Merchants & Eden"},
        "Eden":     {"url": "", "enabled": True,  "label": "Eden → Merchant"},
        "Mari":     {"url": "", "enabled": True,  "label": "Mari"},
        "Jester":   {"url": "", "enabled": True,  "label": "Jester"},
    },
    "default_url": "",
    "log_requests": True,
}


def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


# ── HTTP handler ──────────────────────────────────────────────────────────────
_log_callback = None
_config = load_config()
_server = None


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    if _log_callback:
        _log_callback(line)


def send_to_discord(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return str(e)


def route_payload(payload):
    title = ""
    try:
        title = payload["embeds"][0]["title"]
    except (KeyError, IndexError, TypeError):
        pass

    cfg = _config
    routes = cfg.get("routes", {})

    matched_key = None
    for keyword in routes:
        if keyword.lower() in title.lower():
            matched_key = keyword
            break

    if matched_key:
        route = routes[matched_key]
        if not route.get("enabled", True):
            log(f"⏭  Skipped (disabled): {title!r}")
            return None, None

        url = route.get("url", "").strip()
        if not url and matched_key == "Eden":
            url = routes.get("Merchant", {}).get("url", "").strip()
            if url:
                log("↪  Eden → Merchant alias")

        if url:
            return url, matched_key
        else:
            log(f"⚠  No URL for '{matched_key}', using default")

    default_url = cfg.get("default_url", "").strip()
    if default_url:
        return default_url, "Default"

    log(f"✗  No destination for: {title!r}")
    return None, None


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        title = ""
        try:
            title = payload["embeds"][0]["title"]
        except Exception:
            pass

        url, matched = route_payload(payload)
        if url:
            status = send_to_discord(url, payload)
            log(f"✓  [{matched}] {title!r} → {status}")
            self.send_response(200)
        else:
            self.send_response(204)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Take The L Macro is running")


def start_server(port):
    global _server
    try:
        _server = HTTPServer(("127.0.0.1", port), WebhookHandler)
        log(f"🟢 Router started on port {port}")
        log(f"   Oyster Detector webhook URL → http://localhost:{port}/webhook")
        _server.serve_forever()
    except OSError as e:
        log(f"🔴 Failed to start: {e}")


def stop_server():
    global _server
    if _server:
        _server.shutdown()
        _server = None
        log("🔴 Router stopped")


# ── Theme ─────────────────────────────────────────────────────────────────────
# Pulled from the logo: deep navy bg, hot-pink → violet → blue gradient
BG        = "#0d1021"   # deep navy (logo background)
CARD      = "#141729"   # slightly lighter card
BORDER    = "#1e2340"   # subtle border
FG        = "#e8eaf6"   # near-white text
FG_DIM    = "#6b7299"   # muted text

# Gradient stops from logo
PINK      = "#f0319a"   # top of logo
VIOLET    = "#8b3fff"   # mid logo
BLUE      = "#3bc8f5"   # bottom of logo

# Status
GREEN     = "#4ade80"
RED       = "#f87171"
YELLOW    = "#fbbf24"

# Gradient helper — we'll fake it with a canvas strip
GRAD_START = PINK
GRAD_END   = BLUE


def hex_lerp(c1, c2, t):
    """Interpolate between two hex colors."""
    r1, g1, b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2, g2, b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    r = int(r1 + (r2-r1)*t)
    g = int(g1 + (g2-g1)*t)
    b = int(b1 + (b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"


class GradientBar(tk.Canvas):
    """A thin horizontal gradient bar (pink → violet → blue)."""
    def __init__(self, parent, height=3, **kw):
        super().__init__(parent, height=height, bd=0, highlightthickness=0,
                         bg=BG, **kw)
        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width() or 700
        stops = [PINK, VIOLET, BLUE]
        segments = len(stops) - 1
        for i in range(w):
            t_global = i / max(w - 1, 1)
            seg = min(int(t_global * segments), segments - 1)
            t_local = t_global * segments - seg
            color = hex_lerp(stops[seg], stops[seg+1], t_local)
            self.create_line(i, 0, i, self.winfo_height() or 3, fill=color)


class GradientLabel(tk.Canvas):
    """Label with gradient text via colored rectangles behind white text — 
    actually we do a simpler approach: just render the text and tint it."""
    pass


class TakeTheLMacroApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Take The L Macro")
        self.geometry("720x660")
        self.minsize(660, 580)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._server_thread = None
        self._running = False
        self._route_vars = {}

        self._build_ui()
        self._load_into_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top gradient accent bar
        GradientBar(self, height=3).pack(fill="x")

        # Header
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=22, pady=(16, 0))

        # Logo "L" shape drawn in canvas next to title
        logo_canvas = tk.Canvas(hdr, width=32, height=36, bg=BG,
                                highlightthickness=0)
        logo_canvas.pack(side="left", padx=(0, 10))
        self._draw_logo(logo_canvas)

        title_frame = tk.Frame(hdr, bg=BG)
        title_frame.pack(side="left")
        tk.Label(title_frame, text="Take The L Macro",
                 font=("Segoe UI", 17, "bold"),
                 bg=BG, fg=FG).pack(anchor="w")
        tk.Label(title_frame, text="Webhook router for Oyster Detector",
                 font=("Segoe UI", 8), bg=BG, fg=FG_DIM).pack(anchor="w")

        self._status_lbl = tk.Label(hdr, text="● Stopped",
                                    font=("Segoe UI", 10, "bold"),
                                    bg=BG, fg=RED)
        self._status_lbl.pack(side="right", pady=6)

        # Thin gradient divider
        GradientBar(self, height=1).pack(fill="x", padx=22, pady=(12, 0))

        # Port + controls
        ctrl = tk.Frame(self, bg=BG)
        ctrl.pack(fill="x", padx=22, pady=10)

        tk.Label(ctrl, text="Port", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9)).pack(side="left")

        self._port_var = tk.StringVar(value="5050")
        port_entry = tk.Entry(ctrl, textvariable=self._port_var, width=6,
                              bg=CARD, fg=FG, insertbackground=VIOLET,
                              relief="flat", font=("Segoe UI", 10),
                              highlightthickness=1,
                              highlightbackground=BORDER,
                              highlightcolor=VIOLET)
        port_entry.pack(side="left", padx=(6, 14), ipady=3)

        self._toggle_btn = tk.Button(ctrl, text="  Start Router  ",
                                     command=self._toggle_server,
                                     bg=VIOLET, fg=FG,
                                     font=("Segoe UI", 10, "bold"),
                                     relief="flat", padx=6, pady=5,
                                     cursor="hand2",
                                     activebackground=PINK,
                                     activeforeground=FG,
                                     bd=0)
        self._toggle_btn.pack(side="left")

        self._url_hint = tk.Label(ctrl, text="", bg=BG, fg=FG_DIM,
                                  font=("Segoe UI", 8))
        self._url_hint.pack(side="left", padx=12)

        # Notebook
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook", background=BG, borderwidth=0,
                        tabmargins=[0, 0, 0, 0])
        style.configure("TNotebook.Tab", background=CARD, foreground=FG_DIM,
                        padding=[16, 7], font=("Segoe UI", 10),
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", VIOLET)])
        style.configure("TNotebook", tabposition="n")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=22, pady=(0, 10))

        routes_frame = tk.Frame(nb, bg=BG)
        log_frame    = tk.Frame(nb, bg=BG)
        nb.add(routes_frame, text="  Routes  ")
        nb.add(log_frame,    text="  Log  ")

        self._build_routes_tab(routes_frame)
        self._build_log_tab(log_frame)

    def _draw_logo(self, canvas):
        """Draw a simplified 'L' shape mimicking the logo gradient."""
        colors = [PINK, VIOLET, BLUE]
        # Vertical bar of the L
        for i, y in enumerate(range(0, 24, 8)):
            t = i / 3
            c = hex_lerp(PINK, BLUE, t)
            canvas.create_rectangle(0, y, 10, y+8, fill=c, outline="")
        # Horizontal bar of the L
        for i, x in enumerate(range(0, 32, 8)):
            t = 0.6 + i * 0.1
            c = hex_lerp(VIOLET, BLUE, min(t - 0.6, 1))
            canvas.create_rectangle(x, 24, x+8, 34, fill=c, outline="")

    def _build_routes_tab(self, parent):
        # Default webhook card
        def_card = tk.Frame(parent, bg=CARD, pady=10, padx=14)
        def_card.pack(fill="x", pady=(10, 4))

        top = tk.Frame(def_card, bg=CARD)
        top.pack(fill="x")

        # Pink dot accent
        tk.Label(top, text="◆", bg=CARD, fg=PINK,
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 6))
        tk.Label(top, text="Default / Fallback",
                 bg=CARD, fg=FG, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(top, text="  reconnects, startup, close & unmatched events",
                 bg=CARD, fg=FG_DIM, font=("Segoe UI", 8)).pack(side="left")

        self._default_url_var = tk.StringVar()
        self._make_url_entry(def_card, self._default_url_var)

        # Scrollable route cards
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self._routes_inner = tk.Frame(canvas, bg=BG)

        self._routes_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._routes_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, pady=4)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Save button
        save_row = tk.Frame(parent, bg=BG)
        save_row.pack(fill="x", pady=(6, 10))
        save_btn = tk.Button(save_row, text="  Save Settings  ",
                             command=self._save_settings,
                             bg=PINK, fg=FG,
                             font=("Segoe UI", 10, "bold"),
                             relief="flat", padx=8, pady=5,
                             cursor="hand2",
                             activebackground=VIOLET,
                             activeforeground=FG, bd=0)
        save_btn.pack(side="right")

    def _dot_color(self, keyword):
        colors = {
            "Biome": BLUE, "Aura": PINK, "Merchant": VIOLET,
            "Eden": BLUE, "Mari": "#ff8c42", "Jester": "#c084fc",
        }
        return colors.get(keyword, VIOLET)

    def _add_route_card(self, keyword, route_cfg):
        card = tk.Frame(self._routes_inner, bg=CARD, pady=10, padx=14)
        card.pack(fill="x", pady=3)

        # Left accent strip
        strip = tk.Frame(card, bg=self._dot_color(keyword), width=3)
        strip.pack(side="left", fill="y", padx=(0, 10))

        inner = tk.Frame(card, bg=CARD)
        inner.pack(side="left", fill="both", expand=True)

        top = tk.Frame(inner, bg=CARD)
        top.pack(fill="x")

        enabled_var = tk.BooleanVar(value=route_cfg.get("enabled", True))
        label = route_cfg.get("label", keyword)

        ck = tk.Checkbutton(top, variable=enabled_var, bg=CARD,
                            activebackground=CARD,
                            selectcolor=BORDER,
                            fg=FG, activeforeground=FG,
                            font=("Segoe UI", 10, "bold"),
                            text=label, cursor="hand2",
                            highlightthickness=0)
        ck.pack(side="left")

        if keyword == "Eden":
            tk.Label(top, text="uses Merchant URL if blank",
                     bg=CARD, fg=FG_DIM, font=("Segoe UI", 8)).pack(side="left", padx=10)

        url_var = tk.StringVar(value=route_cfg.get("url", ""))
        self._make_url_entry(inner, url_var)

        self._route_vars[keyword] = {"url": url_var, "enabled": enabled_var}

    def _make_url_entry(self, parent, var):
        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(fill="x", pady=(5, 0))
        entry = tk.Entry(row, textvariable=var, bg="#0a0d1a", fg=FG,
                         insertbackground=VIOLET, relief="flat",
                         font=("Consolas", 9),
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         highlightcolor=VIOLET)
        entry.pack(fill="x", ipady=5)

    def _build_log_tab(self, parent):
        self._log_box = scrolledtext.ScrolledText(
            parent, bg="#080b14", fg=FG, font=("Consolas", 9),
            relief="flat", state="disabled", wrap="word",
            insertbackground=VIOLET,
            selectbackground=VIOLET,
        )
        self._log_box.pack(fill="both", expand=True, pady=(8, 4))

        # Tag colors for log lines
        self._log_box.tag_configure("ok",      foreground=GREEN)
        self._log_box.tag_configure("skip",    foreground=FG_DIM)
        self._log_box.tag_configure("warn",    foreground=YELLOW)
        self._log_box.tag_configure("err",     foreground=RED)
        self._log_box.tag_configure("info",    foreground=BLUE)

        btn_row = tk.Frame(parent, bg=BG)
        btn_row.pack(fill="x", pady=(0, 8))
        tk.Button(btn_row, text="Clear Log", command=self._clear_log,
                  bg=CARD, fg=FG_DIM, font=("Segoe UI", 9),
                  relief="flat", padx=10, pady=3, cursor="hand2",
                  activebackground=BORDER).pack(side="right")

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load_into_ui(self):
        global _config
        _config = load_config()
        self._port_var.set(str(_config.get("port", 5050)))
        self._default_url_var.set(_config.get("default_url", ""))
        for keyword, route_cfg in _config.get("routes", {}).items():
            self._add_route_card(keyword, route_cfg)

    def _save_settings(self):
        global _config
        try:
            port = int(self._port_var.get())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be a number.")
            return
        _config["port"] = port
        _config["default_url"] = self._default_url_var.get().strip()
        for keyword, vars_ in self._route_vars.items():
            if keyword in _config["routes"]:
                _config["routes"][keyword]["url"]     = vars_["url"].get().strip()
                _config["routes"][keyword]["enabled"] = vars_["enabled"].get()
        save_config(_config)
        log("💾 Settings saved")
        messagebox.showinfo("Saved", "Settings saved.")

    # ── Server ────────────────────────────────────────────────────────────────

    def _toggle_server(self):
        if self._running:
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self):
        global _config
        _config = load_config()
        try:
            port = int(self._port_var.get())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be a number.")
            return
        self._server_thread = threading.Thread(
            target=start_server, args=(port,), daemon=True)
        self._server_thread.start()
        self._running = True
        self._toggle_btn.config(text="  Stop Router  ",
                                bg=RED, activebackground="#dc2626")
        self._status_lbl.config(text="● Running", fg=GREEN)
        self._url_hint.config(
            text=f"← http://localhost:{port}/webhook  →  paste into Oyster Detector")

    def _stop_server(self):
        stop_server()
        self._running = False
        self._toggle_btn.config(text="  Start Router  ",
                                bg=VIOLET, activebackground=PINK)
        self._status_lbl.config(text="● Stopped", fg=RED)
        self._url_hint.config(text="")

    # ── Log ───────────────────────────────────────────────────────────────────

    def _append_log(self, text):
        self._log_box.configure(state="normal")
        if "✓" in text:
            tag = "ok"
        elif "⏭" in text or "↪" in text:
            tag = "skip"
        elif "⚠" in text:
            tag = "warn"
        elif "✗" in text or "🔴" in text:
            tag = "err"
        else:
            tag = "info"
        self._log_box.insert("end", text + "\n", tag)
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _on_close(self):
        if self._running:
            stop_server()
        self.destroy()


def main():
    global _log_callback
    app = TakeTheLMacroApp()
    _log_callback = lambda msg: app.after(0, app._append_log, msg)
    app.mainloop()


if __name__ == "__main__":
    main()
