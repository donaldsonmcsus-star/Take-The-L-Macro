"""
Take The L Macro - Sol's RNG auto crafter + biome/aura/merchant detector
"""

import json, math, os, sys, re, threading, time, glob
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
    "webhooks": {
        "biome":    "",
        "aura":     "",
        "merchant": "",
        "default":  "",
    },
    "macro": {
        "enabled":       False,
        "hotkey":        "f2",
        "click1":        [820, 750],   # "Add Everything" button
        "click2":        [1100, 750],  # "Craft" button
        "delay_between": 0.3,    # seconds between click1 and click2
        "delay_loop":    0.5,    # seconds between craft cycles
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


# ── Logging ───────────────────────────────────────────────────────────────────
_log_cb = None

def log(msg, tag="dim"):
    ts = datetime.now().strftime("%H:%M:%S")
    if _log_cb:
        _log_cb(f"[{ts}]  {msg}", tag)


# ── Discord webhook ───────────────────────────────────────────────────────────
def send_webhook(url, title, description, color=0x7c3aed):
    if not url:
        return
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f"webhook error: {e}", "err")


# ── Roblox log watcher ────────────────────────────────────────────────────────
# Sol's RNG writes events to Roblox log files
# These are the patterns used by Oyster Detector
BIOME_PATTERN    = re.compile(r"\[BloxstrapRPC\].*?biome.*?\"([^\"]+)\"", re.IGNORECASE)
AURA_PATTERN     = re.compile(r"\[BloxstrapRPC\].*?aura.*?\"([^\"]+)\"", re.IGNORECASE)
MERCHANT_PATTERN = re.compile(r"\[BloxstrapRPC\].*?(merchant|mari|jester|eden)", re.IGNORECASE)

# Broader patterns as fallback
BIOME_ALT    = re.compile(r"biome[:\s]+([A-Za-z ]+)", re.IGNORECASE)
AURA_ALT     = re.compile(r"equipped aura[:\s]+([A-Za-z ]+)", re.IGNORECASE)

BIOME_COLORS    = 0x2563eb
AURA_COLORS     = 0xf0319a
MERCHANT_COLORS = 0x7c3aed


class LogWatcher:
    def __init__(self, config_getter):
        self._get_cfg = config_getter
        self._running = False
        self._thread  = None
        self._last_pos = 0
        self._last_file = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()
        log("log watcher started", "info")

    def stop(self):
        self._running = False
        log("log watcher stopped", "dim")

    def _get_latest_log(self):
        pattern = os.path.join(ROBLOX_LOG_DIR, "*.log")
        files = glob.glob(pattern)
        if not files:
            return None
        return max(files, key=os.path.getmtime)

    def _watch(self):
        while self._running:
            try:
                log_file = self._get_latest_log()
                if not log_file:
                    time.sleep(3)
                    continue

                if log_file != self._last_file:
                    self._last_file = log_file
                    self._last_pos = 0
                    log(f"watching: {os.path.basename(log_file)}", "info")

                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(self._last_pos)
                    new_lines = f.read()
                    self._last_pos = f.tell()

                if new_lines:
                    self._process(new_lines)

            except Exception as e:
                log(f"log watcher error: {e}", "err")

            time.sleep(1)

    def _process(self, text):
        cfg = self._get_cfg()
        webhooks = cfg.get("webhooks", {})

        for match in BIOME_PATTERN.finditer(text):
            name = match.group(1).strip()
            log(f"biome detected: {name}", "ok")
            url = webhooks.get("biome") or webhooks.get("default", "")
            threading.Thread(target=send_webhook,
                args=(url, f"🌍 Biome: {name}", f"A new biome has appeared!", BIOME_COLORS),
                daemon=True).start()

        for match in AURA_PATTERN.finditer(text):
            name = match.group(1).strip()
            log(f"aura detected: {name}", "ok")
            url = webhooks.get("aura") or webhooks.get("default", "")
            threading.Thread(target=send_webhook,
                args=(url, f"✨ Aura: {name}", f"An aura was equipped!", AURA_COLORS),
                daemon=True).start()

        for match in MERCHANT_PATTERN.finditer(text):
            name = match.group(1).strip().title()
            log(f"merchant detected: {name}", "ok")
            url = webhooks.get("merchant") or webhooks.get("default", "")
            threading.Thread(target=send_webhook,
                args=(url, f"🛒 Merchant: {name}", f"{name} has appeared!", MERCHANT_COLORS),
                daemon=True).start()


# ── Auto crafter macro ────────────────────────────────────────────────────────
class AutoCrafter:
    def __init__(self, config_getter):
        self._get_cfg = config_getter
        self._running = False
        self._thread  = None
        self._mouse   = MouseController()
        self._status_cb = None

    def set_status_callback(self, cb):
        self._status_cb = cb

    def _set_status(self, active):
        if self._status_cb:
            self._status_cb(active)

    def toggle(self):
        if self._running:
            self.stop()
        else:
            self.start()

    def start(self):
        cfg = self._get_cfg()
        macro = cfg.get("macro", {})
        c1 = macro.get("click1", [820, 750])
        c2 = macro.get("click2", [1100, 750])
        if not c1 or not c2:
            log("set both click positions first!", "err")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log("macro started", "ok")
        self._set_status(True)

    def stop(self):
        self._running = False
        log("macro stopped", "dim")
        self._set_status(False)

    def _loop(self):
        cfg = self._get_cfg()
        macro = cfg.get("macro", {})
        c1 = macro.get("click1", [820, 750])
        c2 = macro.get("click2", [1100, 750])
        delay_between = macro.get("delay_between", 0.3)
        delay_loop    = macro.get("delay_loop", 0.5)

        while self._running:
            try:
                # Click button 1 (Add Everything)
                self._mouse.position = (c1[0], c1[1])
                time.sleep(0.05)
                self._mouse.click(Button.left)
                time.sleep(delay_between)

                if not self._running:
                    break

                # Click button 2 (Craft)
                self._mouse.position = (c2[0], c2[1])
                time.sleep(0.05)
                self._mouse.click(Button.left)
                time.sleep(delay_loop)

            except Exception as e:
                log(f"macro error: {e}", "err")
                time.sleep(1)


# ── Hotkey listener ───────────────────────────────────────────────────────────
class HotkeyListener:
    def __init__(self, config_getter, toggle_cb):
        self._get_cfg   = config_getter
        self._toggle_cb = toggle_cb
        self._listener  = None

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def _on_press(self, key):
        cfg = self._get_cfg()
        hotkey_str = cfg.get("macro", {}).get("hotkey", "f2").lower()
        pressed = None
        try:
            pressed = key.char.lower() if hasattr(key, "char") and key.char else None
        except Exception:
            pass
        if pressed is None:
            try:
                pressed = key.name.lower()
            except Exception:
                pass
        if pressed and pressed == hotkey_str:
            self._toggle_cb()


# ── Theme ─────────────────────────────────────────────────────────────────────
BG      = "#080b14"
BORDER  = "#1e2440"
FG      = "#e2e6f0"
FG2     = "#8b92aa"
FG3     = "#3d4460"
PINK    = "#f0319a"
VIOLET  = "#7c3aed"
BLUE    = "#2563eb"
CYAN    = "#06b6d4"
GREEN   = "#34d399"
RED     = "#f87171"
YELLOW  = "#fbbf24"

CARD    = "#0e1120"

def lerp(c1, c2, t):
    r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(int(r1+(r2-r1)*t),int(g1+(g2-g1)*t),int(b1+(b2-b1)*t))

WAVES = [
    (60, 0.008, 0.4,  "#1e1060"),
    (45, 0.012, 0.6,  "#2d1080"),
    (35, 0.018, 0.9,  "#3b12a0"),
    (50, 0.006, 0.3,  "#0d2080"),
    (30, 0.020, 1.2,  "#5b21b6"),
    (40, 0.010, 0.7,  "#1d4ed8"),
    (25, 0.025, 1.5,  "#7c3aed"),
]

class WaveCanvas(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, highlightthickness=0, **kw)
        self._t = 0.0
        self._alive = True
        self._w = 800
        self._h = 650
        self.bind("<Configure>", lambda e: setattr(self, '_w', e.width) or setattr(self, '_h', e.height))
        self._tick()

    def _tick(self):
        if not self._alive:
            return
        self._t += 0.016
        self.delete("wave")
        w, h = self._w, self._h
        top = int(h * 0.28)
        import math
        for amp, freq, speed, color in WAVES:
            pts = []
            for x in range(0, w+4, 4):
                y = (top + amp +
                     amp * math.sin(freq*x + self._t*speed) +
                     amp*0.4 * math.sin(freq*1.7*x + self._t*speed*1.3 + 1.2))
                pts += [x, y]
            pts += [w, h, 0, h]
            if len(pts) >= 6:
                self.create_polygon(pts, fill=color, outline="", tags="wave", smooth=True)
        self.after(33, self._tick)

    def stop(self):
        self._alive = False


# ── Main App ──────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Take The L Macro")
        self.geometry("800x650")
        self.minsize(700, 560)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._cfg = load_config()
        self._webhook_vars = {}
        self._hotkey_var = tk.StringVar(value=self._cfg.get("macro", {}).get("hotkey", "f2"))
        self._delay_between_var = tk.StringVar(value=str(self._cfg.get("macro", {}).get("delay_between", 0.3)))
        self._delay_loop_var    = tk.StringVar(value=str(self._cfg.get("macro", {}).get("delay_loop", 0.5)))

        self._crafter = AutoCrafter(lambda: self._cfg)
        self._crafter.set_status_callback(self._on_macro_status)

        self._watcher = LogWatcher(lambda: self._cfg)

        self._hotkey_listener = HotkeyListener(lambda: self._cfg, self._crafter.toggle)
        self._hotkey_listener.start()

        self._apply_styles()
        self._build_ui()
        self._watcher.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_styles(self):
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
        s.configure("TNotebook.Tab", background=BG, foreground=FG3,
                    padding=[18,8], font=("Segoe UI", 9), borderwidth=0, focuscolor=BG)
        s.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", FG)])
        s.configure("Vertical.TScrollbar", background=BORDER, troughcolor=BG,
                    borderwidth=0, arrowsize=0, width=3)
        s.map("Vertical.TScrollbar", background=[("active", VIOLET)])

    def _build_ui(self):
        self._wave = WaveCanvas(self)
        self._wave.pack(fill="both", expand=True)

        self._ui = tk.Frame(self._wave, bg=BG)
        self._wave.create_window(0, 0, anchor="nw", window=self._ui, tags="ui")
        self._wave.bind("<Configure>", lambda e: (
            self._wave.coords("ui", 0, 0),
            self._ui.configure(width=e.width, height=e.height)
        ))
        self._build_content(self._ui)

    def _build_content(self, root):
        # Gradient line
        bar = tk.Canvas(root, height=2, bg=BG, highlightthickness=0)
        bar.pack(fill="x")
        bar.bind("<Configure>", lambda e, b=bar: self._draw_bar(b))

        # Header
        hdr = tk.Frame(root, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(18, 0))
        tk.Label(hdr, text="Take The L Macro", font=("Segoe UI", 15, "bold"),
                 bg=BG, fg=FG).pack(side="left")

        self._macro_badge = tk.Label(hdr, text="● MACRO OFF", font=("Segoe UI", 9),
                                     bg=BG, fg=FG3)
        self._macro_badge.pack(side="right")

        # Notebook
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(14, 0))
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, pady=(0, 0))

        tab_macro    = tk.Frame(nb, bg=BG)
        tab_webhooks = tk.Frame(nb, bg=BG)
        tab_log      = tk.Frame(nb, bg=BG)
        nb.add(tab_macro,    text="  Macro  ")
        nb.add(tab_webhooks, text="  Webhooks  ")
        nb.add(tab_log,      text="  Log  ")

        self._build_macro_tab(tab_macro)
        self._build_webhooks_tab(tab_webhooks)
        self._build_log_tab(tab_log)

    def _draw_bar(self, canvas):
        canvas.delete("all")
        w = canvas.winfo_width() or 800
        stops = [PINK, VIOLET, BLUE, CYAN]
        n = len(stops)-1
        for i in range(w):
            t = i/max(w-1,1)
            seg = min(int(t*n), n-1)
            c = lerp(stops[seg], stops[seg+1], t*n-seg)
            canvas.create_line(i, 0, i, 3, fill=c)

    # ── Macro tab ─────────────────────────────────────────────────────────────
    def _build_macro_tab(self, parent):
        pad = tk.Frame(parent, bg=BG)
        pad.pack(fill="both", expand=True, padx=28, pady=20)

        # Status + toggle
        status_row = tk.Frame(pad, bg=BG)
        status_row.pack(fill="x", pady=(0, 20))

        self._toggle_btn = tk.Button(status_row, text="Start Macro",
                                     command=self._crafter.toggle,
                                     bg=VIOLET, fg=FG,
                                     font=("Segoe UI", 10, "bold"),
                                     relief="flat", padx=24, pady=6,
                                     cursor="hand2", bd=0,
                                     activebackground=PINK, activeforeground=FG)
        self._toggle_btn.pack(side="left")

        tk.Label(status_row, text="or press", bg=BG, fg=FG3,
                 font=("Segoe UI", 9)).pack(side="left", padx=10)

        hotkey_entry = tk.Entry(status_row, textvariable=self._hotkey_var,
                                width=6, bg=CARD, fg=FG,
                                insertbackground=VIOLET, relief="flat",
                                font=("Consolas", 10),
                                highlightthickness=1, highlightbackground=BORDER,
                                highlightcolor=VIOLET, bd=0,
                                justify="center")
        hotkey_entry.pack(side="left", ipady=4)
        self._hotkey_var.trace_add("write", lambda *_: self._save_hotkey())

        tk.Label(status_row, text="to toggle", bg=BG, fg=FG3,
                 font=("Segoe UI", 9)).pack(side="left", padx=8)

        # Divider
        tk.Frame(pad, bg=BORDER, height=1).pack(fill="x", pady=(0, 16))

        # Click positions
        tk.Label(pad, text="CLICK POSITIONS", font=("Segoe UI", 8),
                 bg=BG, fg=FG3).pack(anchor="w", pady=(0, 8))

        macro = self._cfg.get("macro", {})
        c1 = macro.get("click1", [820, 750])
        c2 = macro.get("click2", [1100, 750])

        self._click1_x = tk.StringVar(value=str(c1[0]))
        self._click1_y = tk.StringVar(value=str(c1[1]))
        self._click2_x = tk.StringVar(value=str(c2[0]))
        self._click2_y = tk.StringVar(value=str(c2[1]))

        self._make_coord_input(pad, "Button 1  (Add Everything)", self._click1_x, self._click1_y, CYAN)
        tk.Frame(pad, bg=BG, height=6).pack()
        self._make_coord_input(pad, "Button 2  (Craft)", self._click2_x, self._click2_y, PINK)

        # Divider
        tk.Frame(pad, bg=BORDER, height=1).pack(fill="x", pady=16)

        # Timing
        tk.Label(pad, text="TIMING", font=("Segoe UI", 8),
                 bg=BG, fg=FG3).pack(anchor="w", pady=(0, 8))

        timing = tk.Frame(pad, bg=BG)
        timing.pack(fill="x")

        self._make_delay_input(timing, "Delay between clicks (s)",
                               self._delay_between_var)
        self._make_delay_input(timing, "Delay between cycles (s)",
                               self._delay_loop_var)

        # Save button
        tk.Frame(pad, bg=BG, height=10).pack()
        tk.Button(pad, text="Save Settings", command=self._save_all,
                  bg=CARD, fg=FG2, font=("Segoe UI", 9),
                  relief="flat", padx=20, pady=5, cursor="hand2", bd=0,
                  highlightthickness=1, highlightbackground=BORDER,
                  activebackground=BORDER, activeforeground=FG).pack(side="right")

    def _make_coord_input(self, parent, label, x_var, y_var, accent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=3)
        tk.Frame(row, bg=accent, width=2, height=16).pack(side="left", padx=(0,10))
        info = tk.Frame(row, bg=BG)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=label, font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=FG).pack(anchor="w")
        coords = tk.Frame(info, bg=BG)
        coords.pack(anchor="w")
        tk.Label(coords, text="X", font=("Segoe UI", 8), bg=BG, fg=FG3).pack(side="left")
        tk.Entry(coords, textvariable=x_var, width=6,
                 bg=CARD, fg=FG, insertbackground=VIOLET,
                 relief="flat", font=("Consolas", 9),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=VIOLET, bd=0, justify="center").pack(side="left", padx=(4,12), ipady=3)
        tk.Label(coords, text="Y", font=("Segoe UI", 8), bg=BG, fg=FG3).pack(side="left")
        tk.Entry(coords, textvariable=y_var, width=6,
                 bg=CARD, fg=FG, insertbackground=VIOLET,
                 relief="flat", font=("Consolas", 9),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=VIOLET, bd=0, justify="center").pack(side="left", padx=(4,0), ipady=3)

    def _make_delay_input(self, parent, label, var):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, font=("Segoe UI", 9),
                 bg=BG, fg=FG2, width=32, anchor="w").pack(side="left")
        e = tk.Entry(row, textvariable=var, width=6,
                     bg=CARD, fg=FG, insertbackground=VIOLET,
                     relief="flat", font=("Consolas", 9),
                     highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=VIOLET, bd=0, justify="center")
        e.pack(side="left", ipady=3)

    def _save_hotkey(self):
        self._cfg["macro"]["hotkey"] = self._hotkey_var.get().strip().lower()
        save_config(self._cfg)

    def _save_all(self):
        try:
            self._cfg["macro"]["delay_between"] = float(self._delay_between_var.get())
            self._cfg["macro"]["delay_loop"]    = float(self._delay_loop_var.get())
            self._cfg["macro"]["click1"] = [int(self._click1_x.get()), int(self._click1_y.get())]
            self._cfg["macro"]["click2"] = [int(self._click2_x.get()), int(self._click2_y.get())]
        except ValueError:
            messagebox.showerror("Error", "Coordinates and delays must be numbers.")
            return
        self._cfg["macro"]["hotkey"] = self._hotkey_var.get().strip().lower()

        for key, var in self._webhook_vars.items():
            self._cfg["webhooks"][key] = var.get().strip()

        save_config(self._cfg)
        log("settings saved", "info")

    # ── Webhooks tab ──────────────────────────────────────────────────────────
    def _build_webhooks_tab(self, parent):
        pad = tk.Frame(parent, bg=BG)
        pad.pack(fill="both", expand=True, padx=28, pady=20)

        webhooks = self._cfg.get("webhooks", {})
        entries = [
            ("biome",    "Biomes",          BLUE),
            ("aura",     "Auras",           PINK),
            ("merchant", "Merchants",       VIOLET),
            ("default",  "Default / Other", FG3),
        ]

        for key, label, accent in entries:
            var = tk.StringVar(value=webhooks.get(key, ""))
            self._webhook_vars[key] = var

            row = tk.Frame(pad, bg=BG)
            row.pack(fill="x", pady=6)

            top = tk.Frame(row, bg=BG)
            top.pack(fill="x", pady=(0,4))
            tk.Frame(top, bg=accent, width=2, height=14).pack(side="left", padx=(0,8))
            tk.Label(top, text=label, font=("Segoe UI", 9, "bold"),
                     bg=BG, fg=FG).pack(side="left")

            e = tk.Entry(row, textvariable=var,
                         bg=CARD, fg=FG2, insertbackground=VIOLET,
                         relief="flat", font=("Consolas", 8),
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=VIOLET, bd=0)
            e.pack(fill="x", ipady=5)

        tk.Frame(pad, bg=BORDER, height=1).pack(fill="x", pady=16)

        tk.Button(pad, text="Save Webhooks", command=self._save_all,
                  bg=CARD, fg=FG2, font=("Segoe UI", 9),
                  relief="flat", padx=20, pady=5, cursor="hand2", bd=0,
                  highlightthickness=1, highlightbackground=BORDER,
                  activebackground=BORDER, activeforeground=FG).pack(side="right")

    # ── Log tab ───────────────────────────────────────────────────────────────
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
        self._log_box.tag_configure("warn", foreground=YELLOW)

        foot = tk.Frame(parent, bg=BG)
        foot.pack(fill="x", padx=24, pady=8)
        tk.Button(foot, text="Clear", command=self._clear_log,
                  bg=BG, fg=FG3, font=("Segoe UI", 8),
                  relief="flat", padx=10, pady=3, cursor="hand2", bd=0,
                  activebackground=CARD, activeforeground=FG).pack(side="right")

    def _append_log(self, text, tag="dim"):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", text + "\n", tag)
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _on_macro_status(self, active):
        self.after(0, lambda: (
            self._macro_badge.config(
                text="● MACRO ON" if active else "● MACRO OFF",
                fg=GREEN if active else FG3
            ),
            self._toggle_btn.config(
                text="Stop Macro" if active else "Start Macro",
                bg=RED if active else VIOLET,
                activebackground="#dc2626" if active else PINK
            )
        ))

    def _on_close(self):
        self._wave.stop()
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
