"""
Take The L Macro - Webhook routing proxy for Oyster Detector
"""

import json
import math
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

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
        "Eden":     {"url": "", "enabled": True,  "label": "Eden"},
        "Mari":     {"url": "", "enabled": True,  "label": "Mari"},
        "Jester":   {"url": "", "enabled": True,  "label": "Jester"},
    },
    "default_url": "",
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


_log_callback = None
_config = load_config()
_server = None


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}]  {msg}"
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
            log(f"skipped  ·  {title}")
            return None, None
        url = route.get("url", "").strip()
        if not url and matched_key == "Eden":
            url = routes.get("Merchant", {}).get("url", "").strip()
            if url:
                log("eden → merchant")
        if url:
            return url, matched_key
        else:
            log(f"no url set for '{matched_key}'")

    default_url = cfg.get("default_url", "").strip()
    if default_url:
        return default_url, "Default"

    log(f"no route matched: {title!r}")
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
            log(f"sent  ·  {matched}  ·  {title}  ·  {status}")
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
        log(f"listening on port {port}")
        _server.serve_forever()
    except OSError as e:
        log(f"failed to start  ·  {e}")


def stop_server():
    global _server
    if _server:
        _server.shutdown()
        _server = None
        log("stopped")


# ── Theme ─────────────────────────────────────────────────────────────────────
BG       = "#080b14"
SURFACE  = "#0f1220cc"
CARD     = "#12172299"
BORDER   = "#1e2440"
FG       = "#e2e6f0"
FG2      = "#8b92aa"
FG3      = "#3d4460"

PINK     = "#f0319a"
VIOLET   = "#7c3aed"
BLUE     = "#2563eb"
CYAN     = "#06b6d4"
GREEN    = "#34d399"
RED      = "#f87171"

ROUTE_COLORS = {
    "Biome": CYAN, "Aura": PINK, "Merchant": VIOLET,
    "Eden": BLUE, "Mari": "#f59e0b", "Jester": "#a78bfa",
}


def lerp_color(c1, c2, t):
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))


def hex_to_rgb(h):
    return int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)


# ── Animated wave background ──────────────────────────────────────────────────
WAVE_COLORS = [
    "#0d0f1e",  # deep bg
    "#0f0c2e",  # dark violet
    "#0a1040",  # dark blue
    "#1a0a3a",  # purple dark
]

# Wave layers: (amplitude, frequency, speed, color, alpha_fraction)
WAVES = [
    (60,  0.008, 0.4,  "#1e1060", 0.9),
    (45,  0.012, 0.6,  "#2d1080", 0.7),
    (35,  0.018, 0.9,  "#3b12a0", 0.5),
    (50,  0.006, 0.3,  "#0d2080", 0.8),
    (30,  0.020, 1.2,  "#5b21b6", 0.4),
    (40,  0.010, 0.7,  "#1d4ed8", 0.5),
    (25,  0.025, 1.5,  "#7c3aed", 0.3),
]


class WaveCanvas(tk.Canvas):
    """Full-window animated wave background."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, highlightthickness=0, **kw)
        self._t = 0.0
        self._animating = True
        self._wave_ids = []
        self.bind("<Configure>", self._on_resize)
        self._w = 680
        self._h = 600
        self._animate()

    def _on_resize(self, event):
        self._w = event.width
        self._h = event.height

    def _animate(self):
        if not self._animating:
            return
        self._t += 0.016
        self._draw_frame()
        self.after(33, self._animate)  # ~30fps

    def _draw_frame(self):
        self.delete("wave")
        w, h = self._w, self._h
        # Waves only fill bottom ~55% of window so header area stays dark/clean
        wave_top = int(h * 0.30)

        for amp, freq, speed, color, alpha in WAVES:
            pts = []
            step = 4
            for x in range(0, w + step, step):
                y = (wave_top + amp +
                     amp * math.sin(freq * x + self._t * speed) +
                     (amp * 0.4) * math.sin(freq * 1.7 * x + self._t * speed * 1.3 + 1.2))
                pts.extend([x, y])

            # Close polygon at bottom
            pts.extend([w, h, 0, h])
            if len(pts) >= 6:
                self.create_polygon(pts, fill=color, outline="", tags="wave",
                                    smooth=True)

    def stop(self):
        self._animating = False


# ── Main App ──────────────────────────────────────────────────────────────────

class TakeTheLMacroApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Take The L Macro")
        self.geometry("680x600")
        self.minsize(600, 520)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._running = False
        self._server_thread = None
        self._route_vars = {}

        self._apply_styles()
        self._build_ui()
        self._load_into_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_styles(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
        style.configure("TNotebook.Tab",
                        background=BG, foreground=FG3,
                        padding=[20, 8], font=("Segoe UI", 9),
                        borderwidth=0, focuscolor=BG)
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", FG)])
        style.configure("Vertical.TScrollbar",
                        background=BORDER, troughcolor=BG,
                        borderwidth=0, arrowsize=0, width=3)
        style.map("Vertical.TScrollbar", background=[("active", VIOLET)])

    def _build_ui(self):
        # Wave canvas fills entire window, sits behind everything
        self._wave = WaveCanvas(self)
        self._wave.place(x=0, y=0, relwidth=1, relheight=1)

        # All content in a transparent frame placed over the wave
        content = tk.Frame(self, bg="")
        # bg="" doesn't work in all tk versions, use BG but with no border
        content = tk.Frame(self, bg=BG, bd=0)
        # Make the content frame fill window but keep bg matching so wave shows
        # We'll use a layered approach: wave canvas + overlay frame
        # The trick: set frame bg to BG but make it transparent via canvas window
        self._overlay = tk.Canvas(self, bg=BG, highlightthickness=0)
        self._overlay.place(x=0, y=0, relwidth=1, relheight=1)

        # Actually the cleanest approach in tkinter: just draw wave on main canvas
        # and pack everything normally on top with matching BG
        # The wave will be "behind" because canvas is packed first
        self._wave.place_forget()
        self._overlay.place_forget()

        # Use a single canvas as the base, draw wave, then embed frames via canvas
        self._bg_canvas = WaveCanvas(self)
        self._bg_canvas.pack(fill="both", expand=True)

        # All UI goes inside a frame that is a window on the canvas
        self._ui_frame = tk.Frame(self._bg_canvas, bg=BG)
        # We place this transparently — but tkinter doesn't do real transparency
        # So we use a semi-workaround: match bg to dark and rely on wave being visible
        # around/behind the sections that have BG color
        self._bg_canvas.create_window(0, 0, anchor="nw",
                                       window=self._ui_frame,
                                       tags="ui")
        self._bg_canvas.bind("<Configure>", self._on_resize)

        self._build_content(self._ui_frame)

    def _on_resize(self, event):
        self._bg_canvas.coords("ui", 0, 0)
        self._ui_frame.configure(width=event.width, height=event.height)

    def _build_content(self, root):
        # ── Thin gradient accent line ─────────────────────────────────────────
        bar = tk.Canvas(root, height=2, bg=BG, highlightthickness=0)
        bar.pack(fill="x")
        bar.bind("<Configure>", lambda e: self._draw_bar(bar))

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(root, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(20, 0))

        left = tk.Frame(hdr, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="Take The L Macro",
                 font=("Segoe UI", 15, "bold"),
                 bg=BG, fg=FG).pack(anchor="w")
        tk.Label(left, text="webhook router",
                 font=("Segoe UI", 9), bg=BG, fg=FG3).pack(anchor="w")

        right = tk.Frame(hdr, bg=BG)
        right.pack(side="right", anchor="n")
        self._status_dot = tk.Label(right, text="●", font=("Segoe UI", 10),
                                    bg=BG, fg=RED)
        self._status_dot.pack(side="left", padx=(0, 5))
        self._status_lbl = tk.Label(right, text="offline",
                                    font=("Segoe UI", 9), bg=BG, fg=FG3)
        self._status_lbl.pack(side="left")

        # ── Controls ──────────────────────────────────────────────────────────
        ctrl = tk.Frame(root, bg=BG)
        ctrl.pack(fill="x", padx=24, pady=(16, 0))

        tk.Label(ctrl, text="PORT", font=("Segoe UI", 8),
                 bg=BG, fg=FG3).pack(side="left")

        self._port_var = tk.StringVar(value="5050")
        port_e = tk.Entry(ctrl, textvariable=self._port_var, width=5,
                          bg="#0d1020", fg=FG, insertbackground=VIOLET,
                          relief="flat", font=("Segoe UI", 10),
                          highlightthickness=1,
                          highlightbackground=BORDER,
                          highlightcolor=VIOLET, bd=0)
        port_e.pack(side="left", padx=(8, 16), ipady=4)

        self._toggle_btn = tk.Button(ctrl, text="Start",
                                     command=self._toggle_server,
                                     bg=VIOLET, fg=FG,
                                     font=("Segoe UI", 9, "bold"),
                                     relief="flat", padx=20, pady=4,
                                     cursor="hand2", bd=0,
                                     activebackground=PINK,
                                     activeforeground=FG)
        self._toggle_btn.pack(side="left")

        self._hint = tk.Label(ctrl, text="", font=("Consolas", 8),
                              bg=BG, fg=FG3)
        self._hint.pack(side="left", padx=12)

        # ── Divider ───────────────────────────────────────────────────────────
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(16, 0))

        # ── Notebook ──────────────────────────────────────────────────────────
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)

        routes_frame = tk.Frame(nb, bg=BG)
        log_frame    = tk.Frame(nb, bg=BG)
        nb.add(routes_frame, text="Routes")
        nb.add(log_frame,    text="Log")

        self._build_routes_tab(routes_frame)
        self._build_log_tab(log_frame)

    def _draw_bar(self, canvas):
        canvas.delete("all")
        w = canvas.winfo_width() or 680
        stops = [PINK, VIOLET, BLUE, CYAN]
        n = len(stops) - 1
        for i in range(w):
            t = i / max(w-1, 1)
            seg = min(int(t * n), n-1)
            tl = t * n - seg
            c = lerp_color(stops[seg], stops[seg+1], tl)
            canvas.create_line(i, 0, i, 3, fill=c)

    def _build_routes_tab(self, parent):
        wrapper = tk.Frame(parent, bg=BG)
        wrapper.pack(fill="both", expand=True, padx=24, pady=16)

        self._default_url_var = tk.StringVar()
        self._make_row(wrapper, "Default / Fallback", self._default_url_var,
                       FG3, note="startup · reconnect · unmatched")

        tk.Frame(wrapper, bg=BORDER, height=1).pack(fill="x", pady=12)

        canvas = tk.Canvas(wrapper, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview,
                           style="Vertical.TScrollbar")
        self._inner = tk.Frame(canvas, bg=BG)
        self._inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        foot = tk.Frame(parent, bg=BG)
        foot.pack(fill="x", padx=24, pady=(0, 16))
        tk.Button(foot, text="Save", command=self._save_settings,
                  bg="#0d1020", fg=FG2, font=("Segoe UI", 9),
                  relief="flat", padx=20, pady=4, cursor="hand2", bd=0,
                  highlightthickness=1, highlightbackground=BORDER,
                  activebackground=BORDER, activeforeground=FG).pack(side="right")

    def _make_row(self, parent, label, url_var, accent=VIOLET, note="", enabled_var=None):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=4)

        top = tk.Frame(row, bg=BG)
        top.pack(fill="x", pady=(0, 4))
        tk.Frame(top, bg=accent, width=2, height=14).pack(side="left", padx=(0, 8))

        if enabled_var is not None:
            ck = tk.Checkbutton(top, variable=enabled_var, text=label,
                                bg=BG, fg=FG, activebackground=BG,
                                activeforeground=FG, selectcolor="#0d1020",
                                font=("Segoe UI", 9, "bold"),
                                highlightthickness=0, cursor="hand2")
            ck.pack(side="left")
        else:
            tk.Label(top, text=label, bg=BG, fg=FG,
                     font=("Segoe UI", 9, "bold")).pack(side="left")

        if note:
            tk.Label(top, text=note, bg=BG, fg=FG3,
                     font=("Segoe UI", 8)).pack(side="left", padx=8)

        entry = tk.Entry(row, textvariable=url_var,
                         bg="#0d1020", fg=FG2, insertbackground=VIOLET,
                         relief="flat", font=("Consolas", 8),
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         highlightcolor=VIOLET, bd=0)
        entry.pack(fill="x", ipady=5)

    def _add_route_row(self, keyword, route_cfg):
        label = route_cfg.get("label", keyword)
        accent = ROUTE_COLORS.get(keyword, VIOLET)
        url_var = tk.StringVar(value=route_cfg.get("url", ""))
        enabled_var = tk.BooleanVar(value=route_cfg.get("enabled", True))
        note = "uses Merchant URL if blank" if keyword == "Eden" else ""
        self._make_row(self._inner, label, url_var, accent, note, enabled_var)
        self._route_vars[keyword] = {"url": url_var, "enabled": enabled_var}

    def _build_log_tab(self, parent):
        self._log_box = scrolledtext.ScrolledText(
            parent, bg="#070a12", fg=FG2,
            font=("Consolas", 8), relief="flat",
            state="disabled", wrap="word",
            insertbackground=VIOLET, bd=0,
            padx=16, pady=12,
        )
        self._log_box.pack(fill="both", expand=True)
        self._log_box.tag_configure("ok",   foreground=GREEN)
        self._log_box.tag_configure("err",  foreground=RED)
        self._log_box.tag_configure("info", foreground=CYAN)
        self._log_box.tag_configure("dim",  foreground=FG3)

        foot = tk.Frame(parent, bg=BG)
        foot.pack(fill="x", padx=24, pady=8)
        tk.Button(foot, text="Clear", command=self._clear_log,
                  bg=BG, fg=FG3, font=("Segoe UI", 8),
                  relief="flat", padx=10, pady=3,
                  cursor="hand2", bd=0,
                  activebackground="#0d1020",
                  activeforeground=FG).pack(side="right")

    def _load_into_ui(self):
        global _config
        _config = load_config()
        self._port_var.set(str(_config.get("port", 5050)))
        self._default_url_var.set(_config.get("default_url", ""))
        for keyword, route_cfg in _config.get("routes", {}).items():
            self._add_route_row(keyword, route_cfg)

    def _save_settings(self):
        global _config
        try:
            port = int(self._port_var.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number.")
            return
        _config["port"] = port
        _config["default_url"] = self._default_url_var.get().strip()
        for keyword, vars_ in self._route_vars.items():
            if keyword in _config["routes"]:
                _config["routes"][keyword]["url"]     = vars_["url"].get().strip()
                _config["routes"][keyword]["enabled"] = vars_["enabled"].get()
        save_config(_config)
        log("settings saved")

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
            messagebox.showerror("Error", "Port must be a number.")
            return
        self._server_thread = threading.Thread(
            target=start_server, args=(port,), daemon=True)
        self._server_thread.start()
        self._running = True
        self._toggle_btn.config(text="Stop", bg=RED, activebackground="#dc2626")
        self._status_dot.config(fg=GREEN)
        self._status_lbl.config(text="online", fg=GREEN)
        self._hint.config(text=f"http://localhost:{port}/webhook")

    def _stop_server(self):
        stop_server()
        self._running = False
        self._toggle_btn.config(text="Start", bg=VIOLET, activebackground=PINK)
        self._status_dot.config(fg=RED)
        self._status_lbl.config(text="offline", fg=FG3)
        self._hint.config(text="")

    def _append_log(self, text):
        self._log_box.configure(state="normal")
        if "sent" in text:
            tag = "ok"
        elif "failed" in text or "error" in text or "no route" in text:
            tag = "err"
        elif "listening" in text or "saved" in text:
            tag = "info"
        else:
            tag = "dim"
        self._log_box.insert("end", text + "\n", tag)
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _on_close(self):
        self._bg_canvas.stop()
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
