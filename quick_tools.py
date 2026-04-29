"""
Quick Tools — Windows system tray launcher for scripts, shortcuts, and tools.
Left-click the tray icon to open the launcher; right-click for options.

Config: config.json (created automatically on first run)
  List of tools with name, command, optional color and category.
  Supported types (auto-detected from extension): bat, cmd, ps1, exe, py, lnk, url, folder.
"""
import os
import sys
import json
import subprocess
import ctypes
import webbrowser
import threading
from collections import OrderedDict
from pathlib import Path
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem, Menu
import tkinter as tk

APP_DIR     = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
CONFIG_PATH = APP_DIR / "config.json"
ANTIGRAVITY_EXE = Path(r"C:\Users\Moritz\AppData\Local\Programs\Antigravity\Antigravity.exe")
BASE_DIR = Path(r"D:\Coding\Apps\quick_tools")

BG     = "#0d0d1b"
CARD   = "#161628"
HOVER  = "#1e1e3a"
HEADER = "#09091a"
FG     = "#ddddf5"
MUTED  = "#5a5a90"
SEP    = "#1e1e38"

TYPE_COLORS = {
    ".bat":   "#f59e0b",
    ".cmd":   "#f59e0b",
    ".ps1":   "#3b82f6",
    ".exe":   "#10b981",
    ".py":    "#eab308",
    ".lnk":   "#8b5cf6",
    "url":    "#6366f1",
    "folder": "#f97316",
}
DEFAULT_COLOR = "#6b7280"


# ── ctypes helpers ─────────────────────────────────────────────────────────────

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def cursor_pos():
    pt = _POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def alert(msg):
    ctypes.windll.user32.MessageBoxW(0, msg, "Quick Tools", 0x10)


# ── Config ────────────────────────────────────────────────────────────────────

def load_config():
    if not CONFIG_PATH.exists():
        _write_default_config()
        return None  # first run
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return [t for t in data.get("tools", []) if not str(t.get("name", "")).startswith("_")]
    except Exception as e:
        alert(f"Failed to load config.json:\n{e}")
        return []

def _write_default_config():
    CONFIG_PATH.write_text(json.dumps({
        "_info": (
            "Quick Tools config. Each entry needs 'name' and 'command'. "
            "Optional: 'color' (hex), 'category' (string), 'args' (list), "
            "'type' (bat/cmd/ps1/exe/py/lnk/url/folder — auto-detected from extension if omitted)."
        ),
        "tools": [
            {"name": "Notepad",     "command": "notepad.exe",                         "color": "#10b981", "category": "Apps"},
            {"name": "PowerShell",  "command": "powershell.exe",                      "color": "#3b82f6", "category": "Apps"},
            {"name": "Calculator",  "command": "calc.exe",                            "color": "#8b5cf6", "category": "Apps"},
            {"name": "Downloads",   "command": "%USERPROFILE%\\Downloads",            "type": "folder", "color": "#f97316", "category": "Folders"},
            {"name": "Desktop",     "command": "%USERPROFILE%\\Desktop",              "type": "folder", "color": "#f97316", "category": "Folders"},
            {"name": "GitHub",      "command": "https://github.com",                  "color": "#6366f1", "category": "Web"},
        ],
    }, indent=2), encoding="utf-8")


# ── Tool type / launch ────────────────────────────────────────────────────────

def tool_type(tool: dict) -> str:
    t = tool.get("type", "").lower().strip()
    if t:
        return t if t.startswith(".") or t in ("url", "folder") else f".{t}"
    cmd = tool.get("command", "")
    if cmd.startswith(("http://", "https://")):
        return "url"
    ext = Path(cmd).suffix.lower()
    return ext if ext else ".exe"

def tool_color(tool: dict) -> str:
    return tool.get("color") or TYPE_COLORS.get(tool_type(tool), DEFAULT_COLOR)

def tool_badge(ttype: str) -> str:
    if ttype in ("url", "folder"):
        return ttype.upper()
    return ttype.lstrip(".").upper()

def launch_tool(tool: dict):
    cmd   = os.path.expandvars(tool.get("command", ""))
    args  = tool.get("args", [])
    ttype = tool_type(tool)
    # Run from the file's own directory so relative paths and sideloaded DLLs resolve correctly
    p = Path(cmd)
    script_dir = str(p.parent) if p.is_absolute() and ttype not in ("url", "folder") else None
    try:
        if ttype == "url":
            webbrowser.open(cmd)
        elif ttype == "folder":
            subprocess.Popen(["explorer", cmd])
        elif ttype == ".ps1":
            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", cmd] + args,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=script_dir,
            )
        elif ttype in (".bat", ".cmd"):
            subprocess.Popen(f'start "" cmd /k "{cmd}"', shell=True, cwd=script_dir)
        elif ttype == ".lnk":
            subprocess.Popen(f'start "" "{cmd}"', shell=True, cwd=script_dir)
        elif ttype == ".py":
            python = sys.executable if not getattr(sys, "frozen", False) else "python"
            subprocess.Popen([python, cmd] + args, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=script_dir)
        elif not args:
            # os.startfile = ShellExecuteW: handles UAC elevation, console vs GUI, cwd=exe dir
            os.startfile(cmd)
        else:
            subprocess.Popen([cmd] + args, cwd=script_dir)
    except Exception as e:
        alert(f"Failed to launch '{tool.get('name')}':\n{e}")


# ── Tray icon ─────────────────────────────────────────────────────────────────



def create_tray_icon() -> Image.Image:
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)

    # === Background circle (reduced padding = bigger icon) ===
    pad = 4
    d.ellipse(
        (pad, pad, size - pad, size - pad),
        fill=(20, 20, 35, 255),
        outline=(255, 255, 255, 255),
        width=3
    )

    # === Bigger, chunkier bolt ===
    def P(x, y):
        return (int(x * size), int(y * size))

    bolt = [
        P(0.58, 0.12),  # higher
        P(0.28, 0.58),  # more left
        P(0.48, 0.58),
        P(0.38, 0.88),  # lower
        P(0.78, 0.40),  # more right
        P(0.58, 0.40),
    ]

    d.polygon(bolt, fill=(255, 255, 255, 255))

    return img


# ── Popup ─────────────────────────────────────────────────────────────────────

_popup = [None]

def _set_bg(widgets, color):
    for w in widgets:
        try:
            w.config(bg=color)
        except Exception:
            pass

def toggle_popup(root, tools, click_xy):
    if _popup[0] is not None:
        try:
            _popup[0].destroy()
        except tk.TclError:
            pass
        _popup[0] = None
        return

    win = tk.Toplevel(root)
    win.withdraw()
    _popup[0] = win
    win.overrideredirect(True)
    win.configure(bg=SEP)
    win.attributes("-topmost", True)
    win.resizable(False, False)

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    def close(*_):
        _popup[0] = None
        for w in (win, veil):
            try:
                w.destroy()
            except Exception:
                pass

    # Transparent full-screen veil catches clicks outside the popup
    veil = tk.Toplevel(root)
    veil.overrideredirect(True)
    veil.attributes("-alpha", 0.01)
    veil.geometry(f"{sw}x{sh}+0+0")
    veil.attributes("-topmost", True)
    veil.bind("<Button-1>", close)
    win.bind("<Escape>", close)

    body = tk.Frame(win, bg=BG)
    body.pack(padx=1, pady=1)
    tk.Frame(body, bg=BG, width=280, height=0).pack()  # minimum width

    # Header
    hdr = tk.Frame(body, bg=HEADER)
    hdr.pack(fill="x")
    tk.Label(hdr, text="  Quick Tools", bg=HEADER, fg=FG,
             font=("Segoe UI", 11, "bold"), anchor="w").pack(side="left", pady=11)
    x_btn = tk.Label(hdr, text="×", bg=HEADER, fg=MUTED,
                     font=("Segoe UI", 16), cursor="hand2", padx=14)
    x_btn.pack(side="right", pady=6)
    x_btn.bind("<Button-1>", close)
    x_btn.bind("<Enter>", lambda e: x_btn.config(fg=FG))
    x_btn.bind("<Leave>", lambda e: x_btn.config(fg=MUTED))

    tk.Frame(body, bg=SEP, height=1).pack(fill="x")

    # Tool cards — optionally grouped by category
    if not tools:
        tk.Label(body, text="No tools configured.\nEdit config.json to add tools.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9), pady=20).pack()
    else:
        grouped: dict = OrderedDict()
        for tool in tools:
            cat = tool.get("category") or None
            grouped.setdefault(cat, []).append(tool)

        cards_frame = tk.Frame(body, bg=BG, padx=10, pady=8)
        cards_frame.pack(fill="x")

        first = True
        for cat, cat_tools in grouped.items():
            if not first:
                tk.Frame(cards_frame, bg=SEP, height=1).pack(fill="x", pady=(4, 0))
            if cat is not None:
                tk.Label(cards_frame, text=cat.upper(), bg=BG, fg=MUTED,
                         font=("Segoe UI", 7, "bold"), anchor="w").pack(
                             fill="x", pady=(6 if not first else 2, 2))
            first = False
            for tool in cat_tools:
                _make_card(cards_frame, tool, close)

    # Footer
    tk.Frame(body, bg=SEP, height=1).pack(fill="x")
    tk.Button(body, text="Edit Config", command=lambda: (close(), _open_config()),
              bg=HEADER, fg=MUTED, relief="flat", font=("Segoe UI", 8),
              activebackground=CARD, activeforeground=FG,
              cursor="hand2", bd=0, padx=12, pady=9).pack(fill="x")

    # Position: above cursor, horizontally centered on it
    win.update_idletasks()
    pw, ph = win.winfo_reqwidth(), win.winfo_reqheight()
    cx, cy = click_xy
    x = max(0, min(cx - pw // 2, sw - pw))
    y = cy - ph - 8
    if y < 0:
        y = cy + 20
    win.geometry(f"+{x}+{y}")
    win.deiconify()

    veil.lift()
    win.lift()
    win.focus_force()


def _make_card(parent, tool, close_fn):
    ttype = tool_type(tool)
    color = tool_color(tool)
    name  = tool.get("name", "Unnamed")
    badge = tool_badge(ttype)

    outer = tk.Frame(parent, bg=color, cursor="hand2")
    outer.pack(fill="x", pady=3)

    mid = tk.Frame(outer, bg=CARD)
    mid.pack(fill="x", padx=(4, 0))

    row = tk.Frame(mid, bg=CARD)
    row.pack(fill="x", padx=12, pady=10)

    text = tk.Frame(row, bg=CARD)
    text.pack(side="left", fill="x", expand=True)

    name_lbl = tk.Label(text, text=name, fg=FG, bg=CARD,
                        font=("Segoe UI", 10, "bold"), anchor="w")
    name_lbl.pack(fill="x")

    badge_lbl = tk.Label(text, text=badge, fg=MUTED, bg=CARD,
                         font=("Segoe UI", 8), anchor="w")
    badge_lbl.pack(fill="x")

    arrow = tk.Label(row, text="›", fg=MUTED, bg=CARD, font=("Segoe UI", 16))
    arrow.pack(side="right", padx=(8, 0))

    hoverable = [mid, row, text, name_lbl, badge_lbl, arrow]

    def on_enter(_e, ws=hoverable, arr=arrow, c=color):
        _set_bg(ws, HOVER)
        arr.config(fg=c)

    def on_leave(_e, ws=hoverable, arr=arrow):
        _set_bg(ws, CARD)
        arr.config(fg=MUTED)

    def on_click(_e, t=tool):
        close_fn()
        threading.Thread(target=launch_tool, args=(t,), daemon=True).start()

    for w in hoverable:
        w.bind("<Enter>",    on_enter)
        w.bind("<Leave>",    on_leave)
        w.bind("<Button-1>", on_click)


def _open_config():
    try:
        subprocess.Popen([str(ANTIGRAVITY_EXE), str(BASE_DIR), str(CONFIG_PATH)])
    except Exception as e:
        alert(f"Cannot open config:\n{e}")


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def main():
    tools = load_config()
    if tools is None:
        alert(
            f"Config created at:\n{CONFIG_PATH}\n\n"
            "Edit it to add your tools, then restart Quick Tools."
        )
        _open_config()
        return

    root = tk.Tk()
    root.withdraw()

    def on_click(_icon, _item):
        pos = cursor_pos()
        current = load_config() or []  # reload on each open
        root.after(0, lambda: toggle_popup(root, current, pos))

    def on_exit(icon, _item):
        icon.stop()
        root.after(0, root.quit)

    tray = pystray.Icon(
        "Quick Tools",
        create_tray_icon(),
        "Quick Tools",
        Menu(
            MenuItem("Open Quick Tools", on_click, default=True),
            Menu.SEPARATOR,
            MenuItem("Edit Config", lambda i, it: _open_config()),
            MenuItem("Exit", on_exit),
        ),
    )
    tray.run_detached()
    root.mainloop()


if __name__ == "__main__":
    main()
