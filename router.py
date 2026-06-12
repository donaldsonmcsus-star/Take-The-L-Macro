"""
Take The L Macro - Sol's RNG auto crafter + detector
"""

import json, os, sys, re, threading, time, glob, math
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from pynput import mouse, keyboard
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key, KeyCode

# ── Paths ─────────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "TakeTheLMacro", "config.json"
)
ROBLOX_LOG_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Roblox", "logs"
)

DEFAULT_CONFIG = {
    "theme": "dark",
    "webhooks": {"biome": "", "aura": "", "merchant": "", "default": ""},
    "macro": {
        "hotkey": "f2",
        "click1": [820, 750],
        "click2": [1100, 750],
        "delay_between": 0.3,
        "delay_loop": 0.5,
    }
}

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    if kk not in data[k]:
                        data[k][kk] = vv
        return data
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ── Themes ────────────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":      "#0f1117",
        "surface": "#181b24",
        "border":  "#252a38",
        "fg":      "#e8eaf0",
        "fg2":     "#7a8099",
        "fg3":     "#3d4260",
        "accent":  "#7c3aed",
        "accent2": "#f0319a",
        "green":   "#34d399",
        "red":     "#f87171",
        "yellow":  "#fbbf24",
        "cyan":    "#06b6d4",
        "entry":   "#0c0e16",
    },
    "light": {
        "bg":      "#f4f5f9",
        "surface": "#ffffff",
        "border":  "#dde0ea",
        "fg":      "#1a1d2e",
        "fg2":     "#5a6080",
        "fg3":     "#aab0c8",
        "accent":  "#7c3aed",
        "accent2": "#f0319a",
        "green":   "#059669",
        "red":     "#dc2626",
        "yellow":  "#d97706",
        "cyan":    "#0891b2",
        "entry":   "#eceef5",
    }
}

# ── Logging ───────────────────────────────────────────────────────────────────
_log_cb = None
def log(msg, tag="dim"):
    ts = datetime.now().strftime("%H:%M:%S")
    if _log_cb:
        _log_cb(f"[{ts}]  {msg}", tag)

# ── Discord ───────────────────────────────────────────────────────────────────
def send_webhook(url, title, description, color=0x7c3aed):
    if not url:
        return
    payload = {"embeds": [{"title": title, "description": description,
                            "color": color,
                            "timestamp": datetime.utcnow().isoformat()}]}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f"webhook error: {e}", "err")

# ── Log watcher ───────────────────────────────────────────────────────────────
BIOME_PAT    = re.compile(r"\[BloxstrapRPC\].*?biome.*?\"([^\"]+)\"", re.IGNORECASE)
AURA_PAT     = re.compile(r"\[BloxstrapRPC\].*?aura.*?\"([^\"]+)\"", re.IGNORECASE)
MERCHANT_PAT = re.compile(r"\[BloxstrapRPC\].*?(merchant|mari|jester|eden)", re.IGNORECASE)

class LogWatcher:
    def __init__(self, cfg_fn):
        self._cfg = cfg_fn
        self._running = False
        self._last_pos = 0
        self._last_file = None

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()
        log("log watcher started", "info")

    def stop(self):
        self._running = False

    def _latest(self):
        files = glob.glob(os.path.join(ROBLOX_LOG_DIR, "*.log"))
        return max(files, key=os.path.getmtime) if files else None

    def _loop(self):
        while self._running:
            try:
                f = self._latest()
                if not f:
                    time.sleep(3); continue
                if f != self._last_file:
                    self._last_file = f
                    self._last_pos = 0
                    log(f"watching {os.path.basename(f)}", "info")
                with open(f, encoding="utf-8", errors="ignore") as fh:
                    fh.seek(self._last_pos)
                    text = fh.read()
                    self._last_pos = fh.tell()
                if text:
                    self._process(text)
            except Exception as e:
                log(f"watcher error: {e}", "err")
            time.sleep(1)

    def _process(self, text):
        wh = self._cfg().get("webhooks", {})
        for m in BIOME_PAT.finditer(text):
            n = m.group(1).strip()
            log(f"biome: {n}", "ok")
            threading.Thread(target=send_webhook,
                args=(wh.get("biome") or wh.get("default",""),
                      f"🌍 Biome: {n}", "A new biome appeared!", 0x2563eb),
                daemon=True).start()
        for m in AURA_PAT.finditer(text):
            n = m.group(1).strip()
            log(f"aura: {n}", "ok")
            threading.Thread(target=send_webhook,
                args=(wh.get("aura") or wh.get("default",""),
                      f"✨ Aura: {n}", "An aura was equipped!", 0xf0319a),
                daemon=True).start()
        for m in MERCHANT_PAT.finditer(text):
            n = m.group(1).strip().title()
            log(f"merchant: {n}", "ok")
            threading.Thread(target=send_webhook,
                args=(wh.get("merchant") or wh.get("default",""),
                      f"🛒 {n}", f"{n} appeared!", 0x7c3aed),
                daemon=True).start()

# ── Auto crafter ──────────────────────────────────────────────────────────────
class AutoCrafter:
    def __init__(self, cfg_fn):
        self._cfg = cfg_fn
        self._running = False
        self._mouse = MouseController()
        self._on_change = None

    def set_callback(self, fn):
        self._on_change = fn

    def toggle(self):
        if self._running: self.stop()
        else: self.start()

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()
        log("macro started", "ok")
        if self._on_change: self._on_change(True)

    def stop(self):
        self._running = False
        log("macro stopped", "dim")
        if self._on_change: self._on_change(False)

    def _loop(self):
        while self._running:
            try:
                m = self._cfg().get("macro", {})
                c1 = m.get("click1", [820, 750])
                c2 = m.get("click2", [1100, 750])
                d1 = m.get("delay_between", 0.3)
                d2 = m.get("delay_loop", 0.5)
                self._mouse.position = (c1[0], c1[1])
                time.sleep(0.05)
                self._mouse.click(Button.left)
                time.sleep(d1)
                if not self._running: break
                self._mouse.position = (c2[0], c2[1])
                time.sleep(0.05)
                self._mouse.click(Button.left)
                time.sleep(d2)
            except Exception as e:
                log(f"macro error: {e}", "err")
                time.sleep(1)

# ── Hotkey listener ───────────────────────────────────────────────────────────
class HotkeyListener:
    def __init__(self, cfg_fn, toggle_fn):
        self._cfg = cfg_fn
        self._toggle = toggle_fn

    def start(self):
        kb = keyboard.Listener(on_press=self._on_press)
        kb.daemon = True
        kb.start()

    def _on_press(self, key):
        hk = self._cfg().get("macro", {}).get("hotkey", "f2").lower()
        pressed = None
        try: pressed = key.char.lower() if key.char else None
        except: pass
        if pressed is None:
            try: pressed = key.name.lower()
            except: pass
        if pressed and pressed == hk:
            self._toggle()

# ── App ───────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Take The L Macro")
        self.geometry("720x580")
        self.minsize(640, 500)
        self.resizable(True, True)

        self._cfg = load_config()
        self._theme = self._cfg.get("theme", "dark")
        self._T = THEMES[self._theme]

        self._webhook_vars = {}
        self._hotkey_var       = tk.StringVar(value=self._cfg["macro"]["hotkey"])
        self._delay_btn_var    = tk.StringVar(value=str(self._cfg["macro"]["delay_between"]))
        self._delay_loop_var   = tk.StringVar(value=str(self._cfg["macro"]["delay_loop"]))
        self._click1x_var      = tk.StringVar(value=str(self._cfg["macro"]["click1"][0]))
        self._click1y_var      = tk.StringVar(value=str(self._cfg["macro"]["click1"][1]))
        self._click2x_var      = tk.StringVar(value=str(self._cfg["macro"]["click2"][0]))
        self._click2y_var      = tk.StringVar(value=str(self._cfg["macro"]["click2"][1]))

        self._crafter = AutoCrafter(lambda: self._cfg)
        self._crafter.set_callback(self._on_macro_change)

        self._watcher = LogWatcher(lambda: self._cfg)
        self._watcher.start()

        HotkeyListener(lambda: self._cfg, self._crafter.toggle).start()

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self):
        T = self._T
        self.configure(bg=T["bg"])

        # Top bar
        topbar = tk.Frame(self, bg=T["bg"])
        topbar.pack(fill="x", padx=24, pady=(18, 0))

        # Hand icon
        icon = tk.Canvas(topbar, width=28, height=32, bg=T["bg"],
                         highlightthickness=0)
        icon.pack(side="left", padx=(0, 10))
        self._draw_hand(icon, T["fg"])

        tk.Label(topbar, text="Take The L Macro",
                 font=("Segoe UI", 14, "bold"),
                 bg=T["bg"], fg=T["fg"]).pack(side="left")

        # Theme toggle
        self._theme_btn = tk.Button(topbar,
                                    text="☀" if self._theme == "dark" else "☾",
                                    command=self._toggle_theme,
                                    bg=T["surface"], fg=T["fg2"],
                                    font=("Segoe UI", 11),
                                    relief="flat", padx=8, pady=2,
                                    cursor="hand2", bd=0,
                                    activebackground=T["border"],
                                    activeforeground=T["fg"])
        self._theme_btn.pack(side="right")

        self._macro_badge = tk.Label(topbar, text="● OFF",
                                     font=("Segoe UI", 9),
                                     bg=T["bg"], fg=T["fg3"])
        self._macro_badge.pack(side="right", padx=(0, 12))

        # Divider
        tk.Frame(self, bg=T["border"], height=1).pack(fill="x", padx=24, pady=(14, 0))

        # Notebook
        self._style = ttk.Style(self)
        self._style.theme_use("default")
        self._apply_tab_style()

        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True)

        self._tab_macro    = tk.Frame(self._nb, bg=T["bg"])
        self._tab_webhooks = tk.Frame(self._nb, bg=T["bg"])
        self._tab_log      = tk.Frame(self._nb, bg=T["bg"])
        self._nb.add(self._tab_macro,    text="  Macro  ")
        self._nb.add(self._tab_webhooks, text="  Webhooks  ")
        self._nb.add(self._tab_log,      text="  Log  ")

        self._build_macro(self._tab_macro)
        self._build_webhooks(self._tab_webhooks)
        self._build_log(self._tab_log)

    def _draw_hand(self, canvas, color):
        """Draw a simple L-hand (index + thumb out) icon."""
        # Palm base
        canvas.create_rounded_rectangle = lambda *a, **k: None  # no built-in
        # Use polygon for palm
        canvas.create_polygon(
            5,32, 5,16, 8,16, 8,10, 12,10, 12,16,
            16,16, 16,32,
            fill=color, outline="")
        # Index finger (tall, slightly left of center)
        canvas.create_polygon(
            8,16, 8,2, 12,2, 12,16,
            fill=color, outline="")
        # Thumb (pointing out-left, lower)
        canvas.create_polygon(
            5,22, 1,18, 1,22, 5,24,
            fill=color, outline="")

    def _apply_tab_style(self):
        T = self._T
        self._style.configure("TNotebook", background=T["bg"], borderwidth=0, tabmargins=0)
        self._style.configure("TNotebook.Tab",
                              background=T["bg"], foreground=T["fg3"],
                              padding=[18, 8], font=("Segoe UI", 9),
                              borderwidth=0, focuscolor=T["bg"])
        self._style.map("TNotebook.Tab",
                        background=[("selected", T["bg"])],
                        foreground=[("selected", T["fg"])])
        self._style.configure("Vertical.TScrollbar",
                              background=T["border"], troughcolor=T["bg"],
                              borderwidth=0, arrowsize=0, width=3)
        self._style.map("Vertical.TScrollbar",
                        background=[("active", T["accent"])])

    # ── Macro tab ─────────────────────────────────────────────────────────────
    def _build_macro(self, parent):
        T = self._T
        pad = tk.Frame(parent, bg=T["bg"])
        pad.pack(fill="both", expand=True, padx=28, pady=20)

        # Start/stop + hotkey
        row = tk.Frame(pad, bg=T["bg"])
        row.pack(fill="x", pady=(0, 20))

        self._start_btn = tk.Button(row, text="Start Macro",
                                    command=self._crafter.toggle,
                                    bg=T["accent"], fg="#ffffff",
                                    font=("Segoe UI", 10, "bold"),
                                    relief="flat", padx=22, pady=6,
                                    cursor="hand2", bd=0,
                                    activebackground=T["accent2"],
                                    activeforeground="#ffffff")
        self._start_btn.pack(side="left")

        tk.Label(row, text="hotkey", bg=T["bg"], fg=T["fg3"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(16, 6))

        self._entry(row, self._hotkey_var, width=6).pack(side="left", ipady=4)
        self._hotkey_var.trace_add("write", lambda *_: self._quick_save())

        # Divider
        tk.Frame(pad, bg=T["border"], height=1).pack(fill="x", pady=(0, 16))

        # Click positions
        self._section(pad, "CLICK POSITIONS")

        self._coord_row(pad, "Button 1 — Add Everything",
                        self._click1x_var, self._click1y_var, T["cyan"])
        tk.Frame(pad, bg=T["bg"], height=6).pack()
        self._coord_row(pad, "Button 2 — Craft",
                        self._click2x_var, self._click2y_var, T["accent2"])

        tk.Frame(pad, bg=T["border"], height=1).pack(fill="x", pady=16)

        # Timing
        self._section(pad, "TIMING")
        self._timing_row(pad, "Delay between clicks (s)", self._delay_btn_var)
        self._timing_row(pad, "Delay between cycles (s)", self._delay_loop_var)

        tk.Frame(pad, bg=T["bg"], height=12).pack()
        tk.Button(pad, text="Save", command=self._save_all,
                  bg=T["surface"], fg=T["fg2"],
                  font=("Segoe UI", 9), relief="flat",
                  padx=20, pady=5, cursor="hand2", bd=0,
                  highlightthickness=1,
                  highlightbackground=T["border"],
                  activebackground=T["border"],
                  activeforeground=T["fg"]).pack(side="right")

    def _section(self, parent, text):
        T = self._T
        tk.Label(parent, text=text, font=("Segoe UI", 8),
                 bg=T["bg"], fg=T["fg3"]).pack(anchor="w", pady=(0, 8))

    def _coord_row(self, parent, label, x_var, y_var, accent):
        T = self._T
        row = tk.Frame(parent, bg=T["bg"])
        row.pack(fill="x", pady=3)
        tk.Frame(row, bg=accent, width=2, height=16).pack(side="left", padx=(0, 10))
        info = tk.Frame(row, bg=T["bg"])
        info.pack(side="left")
        tk.Label(info, text=label, font=("Segoe UI", 9, "bold"),
                 bg=T["bg"], fg=T["fg"]).pack(anchor="w")
        coords = tk.Frame(info, bg=T["bg"])
        coords.pack(anchor="w")
        tk.Label(coords, text="X", font=("Segoe UI", 8),
                 bg=T["bg"], fg=T["fg3"]).pack(side="left")
        self._entry(coords, x_var, width=6).pack(side="left", padx=(4,10), ipady=3)
        tk.Label(coords, text="Y", font=("Segoe UI", 8),
                 bg=T["bg"], fg=T["fg3"]).pack(side="left")
        self._entry(coords, y_var, width=6).pack(side="left", padx=(4,0), ipady=3)

    def _timing_row(self, parent, label, var):
        T = self._T
        row = tk.Frame(parent, bg=T["bg"])
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, font=("Segoe UI", 9),
                 bg=T["bg"], fg=T["fg2"], width=34, anchor="w").pack(side="left")
        self._entry(row, var, width=6).pack(side="left", ipady=3)

    def _entry(self, parent, var, width=30):
        T = self._T
        return tk.Entry(parent, textvariable=var, width=width,
                        bg=T["entry"], fg=T["fg"],
                        insertbackground=T["accent"],
                        relief="flat", font=("Consolas", 9),
                        highlightthickness=1,
                        highlightbackground=T["border"],
                        highlightcolor=T["accent"],
                        bd=0, justify="left")

    # ── Webhooks tab ──────────────────────────────────────────────────────────
    def _build_webhooks(self, parent):
        T = self._T
        pad = tk.Frame(parent, bg=T["bg"])
        pad.pack(fill="both", expand=True, padx=28, pady=20)

        rows = [
            ("biome",    "Biomes",    T["cyan"]),
            ("aura",     "Auras",     T["accent2"]),
            ("merchant", "Merchants", T["accent"]),
            ("default",  "Default",   T["fg3"]),
        ]
        wh = self._cfg.get("webhooks", {})
        for key, label, accent in rows:
            var = tk.StringVar(value=wh.get(key, ""))
            self._webhook_vars[key] = var

            row = tk.Frame(pad, bg=T["bg"])
            row.pack(fill="x", pady=7)

            top = tk.Frame(row, bg=T["bg"])
            top.pack(fill="x", pady=(0, 4))
            tk.Frame(top, bg=accent, width=2, height=14).pack(side="left", padx=(0, 8))
            tk.Label(top, text=label, font=("Segoe UI", 9, "bold"),
                     bg=T["bg"], fg=T["fg"]).pack(side="left")

            self._entry(row, var).pack(fill="x", ipady=5)

        tk.Frame(pad, bg=T["border"], height=1).pack(fill="x", pady=16)
        tk.Button(pad, text="Save", command=self._save_all,
                  bg=T["surface"], fg=T["fg2"],
                  font=("Segoe UI", 9), relief="flat",
                  padx=20, pady=5, cursor="hand2", bd=0,
                  highlightthickness=1, highlightbackground=T["border"],
                  activebackground=T["border"],
                  activeforeground=T["fg"]).pack(side="right")

    # ── Log tab ───────────────────────────────────────────────────────────────
    def _build_log(self, parent):
        T = self._T
        self._log_box = scrolledtext.ScrolledText(
            parent, bg=T["surface"], fg=T["fg2"],
            font=("Consolas", 8), relief="flat",
            state="disabled", wrap="word",
            insertbackground=T["accent"], bd=0,
            padx=16, pady=12,
        )
        self._log_box.pack(fill="both", expand=True)
        self._log_box.tag_configure("ok",   foreground=T["green"])
        self._log_box.tag_configure("err",  foreground=T["red"])
        self._log_box.tag_configure("info", foreground=T["cyan"])
        self._log_box.tag_configure("dim",  foreground=T["fg3"])
        self._log_box.tag_configure("warn", foreground=T["yellow"])

        foot = tk.Frame(parent, bg=T["bg"])
        foot.pack(fill="x", padx=24, pady=8)
        tk.Button(foot, text="Clear", command=self._clear_log,
                  bg=T["bg"], fg=T["fg3"],
                  font=("Segoe UI", 8), relief="flat",
                  padx=10, pady=3, cursor="hand2", bd=0,
                  activebackground=T["surface"],
                  activeforeground=T["fg"]).pack(side="right")

    # ── Theme toggle ──────────────────────────────────────────────────────────
    def _toggle_theme(self):
        self._theme = "light" if self._theme == "dark" else "dark"
        self._cfg["theme"] = self._theme
        save_config(self._cfg)
        # Rebuild UI
        for w in self.winfo_children():
            w.destroy()
        self._T = THEMES[self._theme]
        self._build()
        # Re-attach log callback
        global _log_cb
        _log_cb = lambda msg, tag="dim": self.after(0, self._append_log, msg, tag)

    # ── Save ──────────────────────────────────────────────────────────────────
    def _quick_save(self):
        self._cfg["macro"]["hotkey"] = self._hotkey_var.get().strip().lower()
        save_config(self._cfg)

    def _save_all(self):
        try:
            self._cfg["macro"]["click1"]         = [int(self._click1x_var.get()), int(self._click1y_var.get())]
            self._cfg["macro"]["click2"]         = [int(self._click2x_var.get()), int(self._click2y_var.get())]
            self._cfg["macro"]["delay_between"]  = float(self._delay_btn_var.get())
            self._cfg["macro"]["delay_loop"]     = float(self._delay_loop_var.get())
            self._cfg["macro"]["hotkey"]         = self._hotkey_var.get().strip().lower()
        except ValueError:
            messagebox.showerror("Error", "Coordinates and delays must be numbers.")
            return
        for key, var in self._webhook_vars.items():
            self._cfg["webhooks"][key] = var.get().strip()
        save_config(self._cfg)
        log("settings saved", "info")

    # ── Log helpers ───────────────────────────────────────────────────────────
    def _append_log(self, text, tag="dim"):
        try:
            self._log_box.configure(state="normal")
            self._log_box.insert("end", text + "\n", tag)
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        except Exception:
            pass

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    # ── Macro status ──────────────────────────────────────────────────────────
    def _on_macro_change(self, active):
        T = self._T
        def _update():
            try:
                self._macro_badge.config(
                    text="● ON" if active else "● OFF",
                    fg=T["green"] if active else T["fg3"]
                )
                self._start_btn.config(
                    text="Stop Macro" if active else "Start Macro",
                    bg=T["red"] if active else T["accent"],
                    activebackground=T["accent"] if active else T["accent2"]
                )
            except Exception:
                pass
        self.after(0, _update)

    def _close(self):
        self._watcher.stop()
        self._crafter.stop()
        self.destroy()


def main():
    global _log_cb
    app = App()
    _log_cb = lambda msg, tag="dim": app.after(0, app._append_log, msg, tag)
    app.mainloop()

if __name__ == "__main__":
    main()
