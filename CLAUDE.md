# CLAUDE.md — Quick Tools

## What this is

Single-file Windows system tray launcher. Dark popup of clickable tool cards above the taskbar. Config is a JSON list; reloaded from disk on every popup open.

Sister project of `llm_switcher` — same architecture, same UI patterns.

---

## File map

| File | Role |
|---|---|
| `quick_tools.py` | Entire app — tray, popup, launch routing |
| `add_tool.py` | Standalone terminal config editor, no shared code with main app |
| `config.json` | User tool list, lives next to the exe at runtime |
| `create_icon.py` | Generates `quick_tools.ico` (lightning bolt on dark circle) |
| `build.py` | PyInstaller → `dist/quick_tools.exe` + shortcut |

---

## Hardcoded paths (machine-specific)

These are in `quick_tools.py` and `build.py` and need updating if moving to a different machine:

```python
# quick_tools.py
ANTIGRAVITY_EXE = Path(r"C:\Users\Moritz\AppData\Local\Programs\Antigravity\Antigravity.exe")
BASE_DIR        = Path(r"D:\Coding\Apps\quick_tools")

# build.py
START_MENU_DIR  = Path(r"C:\Users\Moritz\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Torres")
```

`_open_config()` passes both `BASE_DIR` and `CONFIG_PATH` to Antigravity so it opens the project folder alongside the file.

---

## Architecture

### Thread model

```
main thread     tkinter mainloop (root.withdraw — hidden root)
pystray thread  run_detached() — tray icon event loop
daemon threads  one per tool launch (fire-and-forget)
```

pystray callbacks run on the pystray thread. All tkinter calls must be marshalled via `root.after(0, fn)`. This is the only safe bridge.

### Tray → popup flow

```
user left-clicks tray icon
  → on_click() on pystray thread
      → cursor_pos() captured immediately (before any delay)
      → load_config() reloads config.json from disk
      → root.after(0, lambda: toggle_popup(root, tools, pos))
          → toggle_popup() on main thread
              → if popup open: destroy it, return
              → else: build and show popup
```

### Popup construction

`toggle_popup()` builds the entire popup from scratch each time. No persistent widget state.

Key tkinter tricks used:
- `win.withdraw()` → build → position → `win.deiconify()` prevents the window flashing at (0,0) before being moved
- `veil` — a 1%-alpha full-screen `Toplevel` that sits behind the popup and catches outside clicks to close it
- `win.configure(bg=SEP)` + `body.pack(padx=1, pady=1)` — the 1px SEP bleed around body creates the visible border without a `relief` or `bd`
- Minimum width enforced by a zero-height spacer frame: `tk.Frame(body, bg=BG, width=280, height=0).pack()`

### Card layout

Each card uses nested frames to produce the 4px colored left accent:

```
outer  (bg=tool_color, full width)
└── mid  (bg=CARD, padx=(4,0))   ← 4px of outer bleeds through as accent
    └── row  (padx=12, pady=10)
        ├── text frame
        │   ├── name_lbl  (bold, FG)
        │   └── badge_lbl (small, MUTED)  ← type badge: PS1, BAT, URL…
        └── arrow label "›"  (MUTED, turns tool_color on hover)
```

Hover binds `<Enter>/<Leave>` to all inner widgets (`hoverable = [mid, row, text, name_lbl, badge_lbl, arrow]`). `outer` is intentionally excluded — it holds the color accent and should not change on hover.

### Launch routing (`launch_tool`)

```python
url      → webbrowser.open()
folder   → subprocess.Popen(["explorer", cmd])
.ps1     → powershell -ExecutionPolicy Bypass -File, CREATE_NEW_CONSOLE, cwd=script_dir
.bat/cmd → start "" cmd /k "...", shell=True, cwd=script_dir
.lnk     → start "" "...", shell=True, cwd=script_dir
.py      → python interpreter, CREATE_NEW_CONSOLE, cwd=script_dir
.exe (no args) → os.startfile()   ← ShellExecuteW: handles UAC, console/GUI, sets cwd to exe dir
.exe (with args) → subprocess.Popen([cmd]+args, cwd=script_dir)
```

`script_dir` is `str(Path(cmd).parent)` when the command is an absolute path and not a url/folder. Scripts run from their own directory so relative paths and sideloaded DLLs resolve correctly.

`os.startfile` is used for no-arg exe launches because `subprocess.Popen` does not trigger UAC elevation dialogs — `ShellExecuteW` does. It also correctly allocates a console for console-subsystem exes.

### Config

```python
load_config() → list[dict] | None
```

Returns `None` on first run (file didn't exist — default written, user prompted). Returns `[]` on parse error. Filters out entries where `name` starts with `"_"` (comment convention). Called once at startup and again on every popup open.

`tool_type(tool)` resolution order:
1. Explicit `"type"` field in the entry
2. URL prefix (`http://`, `https://`) → `"url"`
3. File extension → `.bat`, `.ps1`, etc.
4. Fallback → `".exe"`

---

## Build

```
python build.py
```

1. Auto-generates `quick_tools.ico` if missing
2. Cleans `dist/` and `build/`
3. Resolves tcl/tk dirs from the Python installation (required — PyInstaller doesn't bundle tkinter's data files automatically)
4. PyInstaller `--onefile --windowed` with `--add-data` for tcl/tk
5. Copies `config.json` to `dist/`
6. Creates `.lnk` shortcut in Start Menu via `win32com.client`

The `--windowed` flag suppresses the console window. The tcl/tk bundling is non-negotiable for tkinter to work in a frozen exe.

---

## Icon

`create_icon.py` generates a lightning bolt polygon on a dark circle with a white outline, saved as a multi-resolution `.ico` (16 → 256px). The same bolt shape is drawn at runtime by `create_tray_icon()` in the main app (the tray icon is generated in-memory from Pillow, not loaded from file).

Both functions use proportional coordinates (`P(x, y)` → `int(x*size), int(y*size)`) so the shape scales correctly across icon sizes.

---

## add_tool.py

Completely standalone — imports nothing from `quick_tools.py`. Shares the same `TYPE_COLORS` mapping and `detect_type` logic, duplicated intentionally to avoid coupling. Reloads config from disk before every action so it always reflects the current file state.
