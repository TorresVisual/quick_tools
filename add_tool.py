"""Interactive terminal editor for quick_tools config.json."""
import json
import os
from collections import OrderedDict
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

R = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
CYAN = "\033[36m"
GRN  = "\033[32m"
YEL  = "\033[33m"
RED  = "\033[31m"

TYPE_COLORS = {
    ".bat": "#f59e0b", ".cmd": "#f59e0b",
    ".ps1": "#3b82f6",
    ".exe": "#10b981",
    ".py":  "#eab308",
    ".lnk": "#8b5cf6",
    "url":    "#6366f1",
    "folder": "#f97316",
}

def detect_type(cmd: str) -> str:
    if cmd.startswith(("http://", "https://")):
        return "url"
    ext = Path(cmd).suffix.lower()
    if ext in (".bat", ".cmd", ".ps1", ".exe", ".py", ".lnk"):
        return ext  # keep the dot, e.g. ".ps1"
    return ".exe"

def default_color(ttype: str) -> str:
    return TYPE_COLORS.get(ttype, "#6b7280")

def badge(ttype: str) -> str:
    return ttype.lstrip(".").upper() if ttype not in ("url", "folder") else ttype.upper()

def hr(char="─", n=52):
    print(DIM + char * n + R)

def load() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"tools": []}
    except Exception as e:
        print(f"{RED}Error reading config: {e}{R}")
        raise SystemExit(1)

def save(data: dict):
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def ask(prompt: str, default: str = "") -> str:
    hint = f" {DIM}[{default}]{R}" if default else ""
    val  = input(f"  {BOLD}{prompt}{R}{hint}: ").strip()
    return val if val else default

def print_tools(tools: list):
    if not tools:
        print(f"  {DIM}(no tools yet){R}")
        return
    grouped: dict = OrderedDict()
    for i, t in enumerate(tools):
        cat = t.get("category") or ""
        grouped.setdefault(cat, []).append((i, t))
    for cat, items in grouped.items():
        if cat:
            print(f"\n  {DIM}{cat.upper()}{R}")
        for idx, t in items:
            cmd = t.get("command", "")
            ttype = t.get("type") or detect_type(cmd)
            cmd_short = (cmd[:34] + "…") if len(cmd) > 35 else cmd
            print(f"  {CYAN}[{idx+1:2d}]{R}  {BOLD}{t.get('name','?'):<20}{R}  {DIM}{cmd_short:<36}{R}  {YEL}{badge(ttype)}{R}")

def do_add(data: dict) -> dict:
    tools = data.get("tools", [])
    print(f"\n{BOLD}Add Tool{R}")
    hr("·")

    name = ask("Name")
    if not name:
        print(f"  {RED}Name is required.{R}")
        return data

    cmd = ask("Command  (path, URL, or exe name)")
    if not cmd:
        print(f"  {RED}Command is required.{R}")
        return data

    ttype    = detect_type(cmd)
    dc       = default_color(ttype)
    type_str = ttype.lstrip(".")
    print(f"  {DIM}→ type: {YEL}{type_str.upper()}{R}  {DIM}default color: {dc}{R}")

    explicit_type = ask("Type override  (blank = keep detected)", "")

    existing_cats = sorted({t.get("category") for t in tools if t.get("category")})
    cat_hint      = "  ".join(existing_cats) if existing_cats else "none yet"
    category      = ask(f"Category  ({cat_hint})", "")

    color = ask("Color (hex)", dc)

    args_str = ask("Args  (space-separated, blank = none)", "")

    tool: dict = {"name": name, "command": cmd}
    if explicit_type:
        tool["type"] = explicit_type
    tool["color"] = color
    if category:
        tool["category"] = category
    if args_str:
        tool["args"] = args_str.split()

    tools.append(tool)
    data["tools"] = tools
    save(data)
    print(f"\n  {GRN}✓  Added \"{name}\"{R}\n")
    return data

def do_delete(data: dict) -> dict:
    tools = data.get("tools", [])
    if not tools:
        print(f"  {DIM}Nothing to delete.{R}")
        return data
    idx_str = ask("Number to delete  (blank = cancel)", "")
    if not idx_str:
        return data
    try:
        idx = int(idx_str) - 1
        if not 0 <= idx < len(tools):
            raise ValueError
    except ValueError:
        print(f"  {RED}Invalid number.{R}")
        return data
    removed = tools.pop(idx)
    data["tools"] = tools
    save(data)
    print(f"\n  {RED}✗  Removed \"{removed.get('name')}\"{R}\n")
    return data

def main():
    os.system("")  # enable ANSI on Windows

    print(f"\n{BOLD}Quick Tools — Config Editor{R}  {DIM}{CONFIG_PATH}{R}")

    while True:
        hr()
        data  = load()
        tools = data.get("tools", [])
        print(f"{BOLD}Tools ({len(tools)}){R}")
        print_tools(tools)
        print(f"\n  {GRN}[A]{R} Add   {RED}[D]{R} Delete   {DIM}[Q]{R} Quit")
        choice = input("\n> ").strip().lower()

        if choice == "q":
            break
        elif choice == "a":
            data = do_add(data)
        elif choice == "d":
            data = do_delete(data)
        else:
            print(f"  {DIM}Unknown command.{R}")

if __name__ == "__main__":
    main()
