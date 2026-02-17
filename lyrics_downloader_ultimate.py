import os
import re
import sys
import json
import threading
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
import webbrowser
import queue

# ------------------ App / Config ------------------

APP_NAME = "Synced Lyrics Downloader"
CONFIG_FILE = str(Path(__file__).with_name("lyrics_gui_config.json"))
DEFAULT_GITHUB_URL = "https://github.com/type0dev/synced-lyrics-downloader"
SYNCEDLYRICS_URL = "https://pypi.org/project/syncedlyrics/"

ALL_PROVIDERS = ["Lrclib", "Musixmatch", "Megalobiz", "NetEase", "Genius"]

CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")
TS_RE = re.compile(r"^\s*\[\d{1,2}:\d{2}(?:\.\d{1,3})?\]")
ICON_STRIP_RE = re.compile(r"^[\U00000080-\U0010ffff\ufe0f]+\s*")


def strip_icon(s: str) -> str:
    return ICON_STRIP_RE.sub("", s).strip()


# ------------------ Thread-safe UI queue ------------------

ui_q = queue.Queue()


def ui_call(fn, *args):
    ui_q.put((fn, args))


def pump_ui_queue():
    try:
        while True:
            fn, args = ui_q.get_nowait()
            try:
                fn(*args)
            except:
                pass
    except queue.Empty:
        pass
    root.after(50, pump_ui_queue)


# ------------------ Popup positioning ------------------

def popup_over_root(win: tk.Toplevel, width=560, height=180):
    win.update_idletasks()
    try:
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        rw = root.winfo_width()
        rh = root.winfo_height()
        x = rx + (rw // 2) - (width // 2)
        y = ry + (rh // 2) - (height // 2)
        win.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
    except:
        win.geometry(f"{width}x{height}")

    win.transient(root)
    win.lift()
    win.focus_force()
    try:
        win.attributes("-topmost", True)
        win.after(150, lambda: win.attributes("-topmost", False))
    except:
        pass


# ------------------ Config ------------------

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except:
        pass


config = load_config()

# Defaults
config.setdefault("music_dir", "")
config.setdefault("theme", "dark")

config.setdefault("providers_order", ["Lrclib", "Musixmatch", "Megalobiz", "NetEase", "Genius"])
default_enabled = {p: True for p in ALL_PROVIDERS}
default_enabled["Genius"] = False
config.setdefault("providers_enabled", default_enabled)

config.setdefault("lang", "en")
config.setdefault("allow_plain_fallback", False)
config.setdefault("upgrade_plain_to_synced", True)  # Ask to upgrade plain lyrics
config.setdefault("strip_cjk", True)
config.setdefault("reject_non_ascii", True)
config.setdefault("reject_non_ascii_ratio", 0.15)

# optional (can be slower on network drives)
config.setdefault("show_lyrics_status", False)

save_config(config)

MUSIC_DIR = config.get("music_dir", "")

# ------------------ Themes ------------------

THEMES = {
    "light": {
        "bg": "#f5f5f5",
        "panel": "#ffffff",
        "fg": "#111111",
        "btn_bg": "#e8e8e8",
        "btn_fg": "#111111",
        "sel_bg": "#2b6cff",
        "sel_fg": "#ffffff",
        "log_bg": "#ffffff",
        "log_fg": "#111111",
        "border": "#d0d0d0",
        "status_bg": "#eeeeee",
        "status_fg": "#111111",
        "link_fg": "#0b57d0",
        "legend_bg": "#f0f0f0",
        "legend_border": "#d0d0d0",
        "ok": "#167d2a",
        "warn": "#b26a00",
        "none": "#666666",
        "plain": "#2563eb",
        "incomp": "#c2410c",
    },
    "dark": {
        "bg": "#141414",
        "panel": "#1c1c1c",
        "fg": "#eaeaea",
        "btn_bg": "#2a2a2a",
        "btn_fg": "#eaeaea",
        "sel_bg": "#3b82f6",
        "sel_fg": "#ffffff",
        "log_bg": "#101010",
        "log_fg": "#eaeaea",
        "border": "#303030",
        "status_bg": "#1a1a1a",
        "status_fg": "#eaeaea",
        "link_fg": "#4ea1ff",
        "legend_bg": "#181818",
        "legend_border": "#303030",
        "ok": "#4ade80",
        "warn": "#fbbf24",
        "none": "#9ca3af",
        "plain": "#60a5fa",
        "incomp": "#fb923c",
    },
}

# ------------------ Windows Titlebar Theme ------------------

def set_titlebar_theme(is_dark: bool):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1 if is_dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except:
        pass


# ------------------ Helpers ------------------

def open_github():
    webbrowser.open(DEFAULT_GITHUB_URL)


def open_syncedlyrics():
    webbrowser.open(SYNCEDLYRICS_URL)


def get_lang_code():
    return config.get("lang", "en")


def allow_plain_fallback():
    return bool(config.get("allow_plain_fallback", False))


def show_status_icons():
    return bool(config.get("show_lyrics_status", False))


def get_enabled_providers_in_order():
    enabled = config.get("providers_enabled", {})
    order = config.get("providers_order", [])
    out = [p for p in order if enabled.get(p, False)]
    return out if out else ["Lrclib"]


def get_synced_provider_order():
    return [p for p in get_enabled_providers_in_order() if p != "Genius"]


def get_plain_provider_order():
    return get_enabled_providers_in_order()


def infer_artist_from_path(song_path: str) -> str:
    try:
        rel = os.path.relpath(song_path, MUSIC_DIR)
        return rel.split(os.sep, 1)[0]
    except:
        return ""


def normalize_title(title: str) -> str:
    if " " in title:
        first, rest = title.split(" ", 1)
        if first.isdigit():
            title = rest
    title = title.replace("_", " ").replace("'", "'")
    for ch in ["!", "?", ":", ";"]:
        title = title.replace(ch, "")
    return " ".join(title.split())


# ------------------ Status scanning / caching ------------------

lyrics_cache = {}
missing_targets = []
scanned_artists = set()  # Track which artists have been scanned for selective icon display


def newest_mtime_in_tree(folder: str) -> int:
    newest = 0
    try:
        for root_dir, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".mp3", ".flac", ".lrc")):
                    p = os.path.join(root_dir, f)
                    try:
                        newest = max(newest, int(os.path.getmtime(p)))
                    except:
                        pass
    except:
        pass
    return newest


def scan_folder_completeness(folder: str):
    total = 0
    have = 0
    try:
        for root_dir, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".mp3", ".flac")):
                    total += 1
                    base = os.path.splitext(os.path.join(root_dir, f))[0]
                    lrc = base + ".lrc"
                    if os.path.exists(lrc):
                        have += 1
    except:
        pass
    return {"total": total, "have": have}


def completeness_icon(have: int, total: int) -> str:
    if total <= 0 or have == 0:
        return "⬜"
    if have >= total:
        return "✅"
    return "🟨"


def analyze_lrc(lrc_path: str) -> str:
    if not os.path.exists(lrc_path):
        return "none"
    try:
        with open(lrc_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [ln.strip() for ln in f.read().splitlines()]
    except:
        return "none"

    lyric_lines = []
    for ln in lines:
        if not ln:
            continue
        if ln.startswith(("[ar:", "[ti:", "[al:", "[by:", "[offset:", "[re:", "[ve:")):
            continue
        lyric_lines.append(ln)

    if len(lyric_lines) < 6:
        return "incomplete"

    ts_lines = sum(1 for ln in lyric_lines if TS_RE.match(ln))
    return "synced" if ts_lines >= 3 else "plain"


def track_icon_for_state(state: str) -> str:
    return {
        "synced": "✅",      # Green check - has synced
        "plain": "📄",      # Page/document - has plain text
        "incomplete": "⚠️",  # Warning - incomplete/bad quality
        "none": "❌"        # Red X - missing
    }.get(state, "❌")


# ------------------ UI helpers ------------------

def _set_status(text: str, color: str = "normal"):
    status_var.set(text)
    t = THEMES[config.get("theme", "dark")]
    
    # Set color based on type
    if color == "success":
        status_label.configure(fg=t["ok"])
    elif color == "error":
        status_label.configure(fg=t["incomp"])
    elif color == "working":
        status_label.configure(fg=t["plain"])
    else:
        status_label.configure(fg=t["status_fg"])


def set_status(text: str, color: str = "normal"):
    if threading.current_thread() is threading.main_thread():
        _set_status(text, color)
    else:
        ui_call(_set_status, text, color)


def _log(msg: str):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)


def log(msg: str):
    if threading.current_thread() is threading.main_thread():
        _log(msg)
    else:
        ui_call(_log, msg)


# ------------------ Artist filtering ------------------

all_artists = []

def rebuild_artist_list_filtered(keep_selection_name=None):
    artist_list.delete(0, tk.END)
    q = search_var.get().strip().lower() if 'search_var' in globals() else ""

    def add_artist(name: str):
        # Show icons only if this artist has been scanned
        if name in scanned_artists:
            ap = os.path.join(MUSIC_DIR, name)
            newest = newest_mtime_in_tree(ap)
            key = (ap, newest, "artist")
            if key not in lyrics_cache:
                lyrics_cache[key] = scan_folder_completeness(ap)
            res = lyrics_cache[key]
            icon = completeness_icon(res["have"], res["total"])
            artist_list.insert(tk.END, f"{icon} {name}")
        else:
            artist_list.insert(tk.END, name)

    if not q:
        for a in all_artists:
            add_artist(a)
    else:
        for a in all_artists:
            if q in a.lower():
                add_artist(a)

    if keep_selection_name:
        for i in range(artist_list.size()):
            if strip_icon(artist_list.get(i)) == keep_selection_name:
                artist_list.selection_set(i)
                artist_list.activate(i)
                artist_list.see(i)  # Scroll to keep selected artist in view
                break


# ------------------ Tooltips ------------------

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        t = THEMES[config.get("theme", "dark")]
        label = tk.Label(tw, text=self.text, justify='left',
                        background=t["panel"], foreground=t["fg"],
                        relief='solid', borderwidth=1,
                        font=("Segoe UI", 9), padx=8, pady=4)
        label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def create_tooltip(widget, text):
    """Helper to create tooltips easily"""
    return ToolTip(widget, text)


# ------------------ Keyboard Shortcuts ------------------

def setup_keyboard_shortcuts():
    """Setup global keyboard shortcuts"""
    root.bind('<F5>', lambda e: load_artists() if MUSIC_DIR else None)
    root.bind('<Escape>', lambda e: request_cancel() if downloading else None)
    root.bind('<Control-d>', lambda e: start_download() if not downloading else None)
    root.bind('<Control-D>', lambda e: start_download() if not downloading else None)


# ------------------ Refresh helpers ------------------

def get_selected_artist_name():
    if not artist_list.curselection():
        return None
    if len(artist_list.curselection()) != 1:
        return None
    return strip_icon(artist_list.get(artist_list.curselection()[0]))


def refresh_artist_list(keep_selection=True):
    global all_artists
    if not MUSIC_DIR or not os.path.isdir(MUSIC_DIR):
        return

    sel_artist = get_selected_artist_name() if keep_selection else None

    try:
        artists = [a for a in sorted(os.listdir(MUSIC_DIR)) if os.path.isdir(os.path.join(MUSIC_DIR, a))]
    except:
        artists = []

    all_artists = artists[:]
    rebuild_artist_list_filtered(keep_selection_name=sel_artist)


def refresh_current_view():
    if not artist_list.curselection():
        album_list.delete(0, tk.END)
        track_list.delete(0, tk.END)
        return
    on_artist_select(None)


# ------------------ Library Scan ------------------

def choose_folder():
    global MUSIC_DIR, missing_targets
    folder = filedialog.askdirectory(title="Select Music Folder")
    if not folder:
        return
    MUSIC_DIR = folder
    missing_targets = []
    config["music_dir"] = MUSIC_DIR
    save_config(config)
    load_artists()


def load_artists():
    if not MUSIC_DIR or not os.path.isdir(MUSIC_DIR):
        return

    album_list.delete(0, tk.END)
    track_list.delete(0, tk.END)
    log_box.delete("1.0", tk.END)

    set_status(f"Loaded: {MUSIC_DIR}")
    log(f"Loaded artists from: {MUSIC_DIR}")
    log(f"Config file: {CONFIG_FILE}")

    lyrics_cache.clear()
    refresh_artist_list(keep_selection=False)


def update_missing_dl_button_state():
    """Enable Download Missing button if any selected artists are scanned and might have missing items"""
    # Check if any selected artists have been scanned
    selected_artists = [strip_icon(artist_list.get(i)) for i in artist_list.curselection()]
    
    has_scanned = any(artist in scanned_artists for artist in selected_artists)
    
    if has_scanned:
        missing_dl_btn.configure(state="normal")
    else:
        missing_dl_btn.configure(state="disabled")


def on_artist_select(event=None):
    # Preserve missing_targets if they exist
    has_missing_targets = bool(missing_targets)
    
    # Only clear if no missing targets exist
    if not has_missing_targets:
        missing_scan_btn.configure(text="Scan Missing (Selection) [0]")
    
    # Update Download Missing button state
    if has_missing_targets:
        missing_dl_btn.configure(state="normal")
    else:
        update_missing_dl_button_state()

    # Update button text based on selection
    if artist_list.curselection():
        if len(artist_list.curselection()) == artist_list.size() and artist_list.size() > 0:
            artist_select_btn.configure(text="Clear All")
        else:
            artist_select_btn.configure(text="Select All")
    else:
        artist_select_btn.configure(text="Select All")

    album_list.delete(0, tk.END)
    track_list.delete(0, tk.END)

    if not artist_list.curselection():
        return

    if len(artist_list.curselection()) > 1:
        set_status(f"{len(artist_list.curselection())} artists selected")
        return

    artist = strip_icon(artist_list.get(artist_list.curselection()[0]))
    artist_path = os.path.join(MUSIC_DIR, artist)

    try:
        albums = [a for a in sorted(os.listdir(artist_path)) if os.path.isdir(os.path.join(artist_path, a))]
    except:
        return

    # Show icons only if this artist has been scanned
    if artist in scanned_artists:
        for album in albums:
            ap = os.path.join(artist_path, album)
            newest = newest_mtime_in_tree(ap)
            key = (ap, newest, "album")
            if key not in lyrics_cache:
                lyrics_cache[key] = scan_folder_completeness(ap)
            res = lyrics_cache[key]
            icon = completeness_icon(res["have"], res["total"])
            album_list.insert(tk.END, f"{icon} {album}")
    else:
        for album in albums:
            album_list.insert(tk.END, album)

    set_status(f"{artist} — {album_list.size()} albums")

    if album_list.size() > 0:
        album_list.selection_set(0)
        album_list.activate(0)
        # Update album button after auto-selection
        album_select_btn.configure(text="Select All")
        on_album_select(None)


def on_album_select(event=None):
    # Preserve missing_targets if they exist
    has_missing_targets = bool(missing_targets)
    
    # Only clear if no missing targets exist
    if not has_missing_targets:
        missing_scan_btn.configure(text="Scan Missing (Selection) [0]")
    
    # Update Download Missing button state
    if has_missing_targets:
        missing_dl_btn.configure(state="normal")
    else:
        update_missing_dl_button_state()

    track_list.delete(0, tk.END)

    # Update button text based on selection
    if album_list.size() > 0:
        if album_list.curselection():
            if len(album_list.curselection()) == album_list.size():
                album_select_btn.configure(text="Clear All")
            else:
                album_select_btn.configure(text="Select All")
        else:
            album_select_btn.configure(text="Select All")
    
    if not artist_list.curselection():
        return
    if len(artist_list.curselection()) > 1:
        set_status("Multiple artists selected (track list not shown)")
        return

    artist = strip_icon(artist_list.get(artist_list.curselection()[0]))
    artist_path = os.path.join(MUSIC_DIR, artist)

    sel_albums_disp = [album_list.get(i) for i in album_list.curselection()]
    if not sel_albums_disp:
        # Don't auto-select if we just cleared selection
        return

    sel_albums = [strip_icon(a) for a in sel_albums_disp]
    combined = (len(sel_albums) > 1)

    total_tracks = 0
    show_icons = artist in scanned_artists  # Only show icons if artist has been scanned
    
    for album in sel_albums:
        album_path = os.path.join(artist_path, album)
        try:
            for root_dir, _, files in os.walk(album_path):
                for file in sorted(files):
                    if file.lower().endswith((".mp3", ".flac")):
                        rel_to_album = os.path.relpath(os.path.join(root_dir, file), album_path)
                        track_path = os.path.join(album_path, rel_to_album)
                        lrc_path = os.path.splitext(track_path)[0] + ".lrc"

                        prefix = ""
                        if show_icons:
                            if os.path.exists(lrc_path):
                                state = analyze_lrc(lrc_path)
                            else:
                                state = "none"
                            prefix = f"{track_icon_for_state(state)} "

                        display = f"{album}{os.sep}{rel_to_album}" if combined else rel_to_album
                        track_list.insert(tk.END, prefix + display)
                        total_tracks += 1
        except:
            pass

    if len(sel_albums) == 1:
        set_status(f"{artist} / {sel_albums[0]} — {total_tracks} tracks")
    else:
        set_status(f"{artist} — {len(sel_albums)} albums selected — {total_tracks} tracks")


# ------------------ Lyrics helpers ------------------

def run_provider(query: str, provider: str, out_path: str, lang_code: str, want_synced: bool) -> bool:
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except:
            pass

    cmd = ["syncedlyrics", query, "-p", provider, "-o", out_path]
    cmd.append("--synced-only" if want_synced else "--plain-only")
    if lang_code:
        cmd.extend(["--lang", lang_code])

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(out_path) and os.path.getsize(out_path) > 50


def ask_upgrade_plain_lyrics(song_name: str) -> tuple[bool, bool]:
    """
    Ask user what to do with plain lyrics file.
    Returns: (rename_to_txt, try_upgrade_to_synced)
    """
    t = THEMES[config.get("theme", "dark")]
    
    dialog = tk.Toplevel(root)
    dialog.title("Plain Lyrics Found")
    dialog.configure(bg=t["bg"])
    dialog.grab_set()
    dialog.resizable(False, False)
    
    # Center on parent
    dialog.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - 250
    y = root.winfo_y() + (root.winfo_height() // 2) - 100
    dialog.geometry(f"500x180+{x}+{y}")
    
    result = {"rename": False, "upgrade": False}
    
    # Message
    msg_frame = tk.Frame(dialog, bg=t["bg"])
    msg_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    tk.Label(
        msg_frame,
        text=f"Plain lyrics file saved as .lrc:",
        bg=t["bg"], fg=t["fg"],
        font=("Segoe UI", 10, "bold")
    ).pack(anchor="w")
    
    tk.Label(
        msg_frame,
        text=song_name,
        bg=t["bg"], fg=t["fg"],
        font=("Segoe UI", 9)
    ).pack(anchor="w", padx=20, pady=(5, 10))
    
    # Checkboxes
    check_frame = tk.Frame(dialog, bg=t["bg"])
    check_frame.pack(fill="x", padx=20, pady=10)
    
    rename_var = tk.BooleanVar(value=True)
    tk.Checkbutton(
        check_frame,
        text="Rename .lrc → .txt (recommended for plain lyrics)",
        variable=rename_var,
        bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
        activebackground=t["bg"], activeforeground=t["fg"]
    ).pack(anchor="w")
    
    upgrade_var = tk.BooleanVar(value=True)
    tk.Checkbutton(
        check_frame,
        text="Try to find synced version (may take a moment)",
        variable=upgrade_var,
        bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
        activebackground=t["bg"], activeforeground=t["fg"]
    ).pack(anchor="w", pady=(5, 0))
    
    # Buttons
    btn_frame = tk.Frame(dialog, bg=t["bg"])
    btn_frame.pack(fill="x", padx=20, pady=(10, 20))
    
    def on_ok():
        result["rename"] = rename_var.get()
        result["upgrade"] = upgrade_var.get()
        dialog.destroy()
    
    def on_skip():
        result["rename"] = False
        result["upgrade"] = False
        dialog.destroy()
    
    tk.Button(
        btn_frame,
        text="OK",
        command=on_ok,
        bg=t["btn_bg"], fg=t["btn_fg"],
        activebackground=t["btn_bg"], activeforeground=t["btn_fg"],
        width=10
    ).pack(side="left", padx=(0, 10))
    
    tk.Button(
        btn_frame,
        text="Skip",
        command=on_skip,
        bg=t["btn_bg"], fg=t["btn_fg"],
        activebackground=t["btn_bg"], activeforeground=t["btn_fg"],
        width=10
    ).pack(side="left")
    
    dialog.wait_window()
    return result["rename"], result["upgrade"]


def strip_cjk_lines_in_lrc(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
    except:
        return False

    kept = []
    changed = False
    for line in lines:
        if line.startswith(("[ar:", "[ti:", "[al:", "[by:", "[offset:", "[re:", "[ve:")):
            kept.append(line)
            continue
        if "]" in line:
            text = line.rsplit("]", 1)[-1].strip()
            if text and CJK_RE.search(text):
                changed = True
                continue
        kept.append(line)

    try:
        with open(path, "w", encoding="utf-8", errors="ignore") as f:
            f.write("\n".join(kept).strip() + "\n")
    except:
        return False

    return changed


def handle_plain_lyrics(lrc_path: str) -> str:
    """
    If a .lrc file is actually plain lyrics (not synced), rename it to .txt
    Returns the final path (either .lrc or .txt)
    """
    if not os.path.exists(lrc_path):
        return lrc_path
    
    state = analyze_lrc(lrc_path)
    
    if state == "plain":
        # This is plain text, should be .txt not .lrc
        txt_path = os.path.splitext(lrc_path)[0] + ".txt"
        try:
            # Remove .txt if it exists
            if os.path.exists(txt_path):
                os.remove(txt_path)
            # Rename .lrc to .txt
            os.rename(lrc_path, txt_path)
            return txt_path
        except:
            return lrc_path
    
    return lrc_path


def reject_if_mostly_non_ascii(path: str) -> bool:
    if not config.get("reject_non_ascii", True):
        return False

    ratio_limit = float(config.get("reject_non_ascii_ratio", 0.15))
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except:
        return False

    non_ascii = sum(1 for c in content if ord(c) > 127)
    ratio = non_ascii / max(len(content), 1)

    if ratio > ratio_limit:
        try:
            os.remove(path)
        except:
            pass
        return True
    return False


# ------------------ Download (thread + cancel) ------------------

downloading = False
cancel_requested = False


def start_download():
    global cancel_requested
    if downloading:
        return
    cancel_requested = False
    cancel_btn.configure(state="normal")
    threading.Thread(target=download_selected, daemon=True).start()


def request_cancel():
    global cancel_requested
    if not downloading:
        return
    cancel_requested = True
    set_status("Cancel requested…")
    log("⚠ Cancel requested — stopping after current step.")


def should_cancel():
    return cancel_requested


def resolve_track_display_to_path(artist: str, display: str) -> str:
    display = strip_icon(display)
    base_artist = os.path.join(MUSIC_DIR, artist)

    parts = display.split(os.sep, 1)
    if len(parts) == 2:
        return os.path.join(base_artist, parts[0], parts[1])

    sel_albums = [strip_icon(album_list.get(i)) for i in album_list.curselection()]
    if not sel_albums and album_list.size() > 0:
        sel_albums = [strip_icon(album_list.get(0))]
    if sel_albums:
        return os.path.join(base_artist, sel_albums[0], display)
    return os.path.join(base_artist, display)


def download_selected():
    global downloading, missing_targets

    if not artist_list.curselection() and not album_list.curselection() and not track_list.curselection():
        ui_call(messagebox.showwarning, "Select", "Select an artist/album/track first.")
        ui_call(cancel_btn.configure, {"state": "disabled"})
        return
    if not MUSIC_DIR or not os.path.isdir(MUSIC_DIR):
        ui_call(messagebox.showwarning, "Music folder", "Pick a valid music folder first.")
        ui_call(cancel_btn.configure, {"state": "disabled"})
        return

    downloading = True
    ui_call(dl_btn.configure, {"state": "disabled"})
    ui_call(open_btn.configure, {"state": "disabled"})
    ui_call(custom_btn.configure, {"state": "disabled"})
    ui_call(missing_scan_btn.configure, {"state": "disabled"})
    ui_call(missing_dl_btn.configure, {"state": "disabled"})

    selected_artists_disp = [artist_list.get(i) for i in artist_list.curselection()]
    selected_artists = [strip_icon(a) for a in selected_artists_disp]
    targets = []

    if len(selected_artists) > 1:
        for artist in selected_artists:
            base_path = os.path.join(MUSIC_DIR, artist)
            for root_dir, _, files in os.walk(base_path):
                for f in files:
                    if f.lower().endswith((".mp3", ".flac")):
                        targets.append(os.path.join(root_dir, f))
    else:
        artist = selected_artists[0] if selected_artists else None

        if not artist:
            log("Nothing selected. Pick an artist/album/track.")
            set_status("Select an artist/album/track.")
            downloading = False
            ui_call(dl_btn.configure, {"state": "normal"})
            ui_call(open_btn.configure, {"state": "normal"})
            ui_call(custom_btn.configure, {"state": "normal"})
            ui_call(missing_scan_btn.configure, {"state": "normal"})
            ui_call(missing_dl_btn.configure, {"state": "normal"})
            ui_call(cancel_btn.configure, {"state": "disabled"})
            return
        else:
            base_artist = os.path.join(MUSIC_DIR, artist)
            sel_albums = [strip_icon(album_list.get(i)) for i in album_list.curselection()]

            if track_list.curselection():
                for i in track_list.curselection():
                    path = resolve_track_display_to_path(artist, track_list.get(i))
                    if os.path.isfile(path) and path.lower().endswith((".mp3", ".flac")):
                        targets.append(path)

            elif sel_albums:
                for album in sel_albums:
                    album_path = os.path.join(base_artist, album)
                    for root_dir, _, files in os.walk(album_path):
                        for f in files:
                            if f.lower().endswith((".mp3", ".flac")):
                                targets.append(os.path.join(root_dir, f))
            else:
                for root_dir, _, files in os.walk(base_artist):
                    for f in files:
                        if f.lower().endswith((".mp3", ".flac")):
                            targets.append(os.path.join(root_dir, f))

    seen = set()
    deduped = []
    for p in targets:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    targets = deduped

    providers_synced = get_synced_provider_order()
    providers_plain = get_plain_provider_order()
    lang_code = get_lang_code()
    plain_ok = allow_plain_fallback()

    total = len(targets)
    set_status(f"Downloading… ({total} tracks)", "working")
    log(f"\nProcessing {total} tracks...\n")
    
    success_count = 0
    failed_count = 0

    for idx, song in enumerate(targets, 1):
        if should_cancel():
            log("🛑 Cancelled by user.")
            break

        lrc = os.path.splitext(song)[0] + ".lrc"
        
        song_name = os.path.basename(song)
        title = normalize_title(os.path.splitext(song_name)[0])

        set_status(f"[{idx}/{total}] {song_name}", "working")
        log(f"[{idx}/{total}] Searching: {title}")

        # Check if we already have lyrics
        existing_lrc_state = None
        if os.path.exists(lrc):
            existing_lrc_state = analyze_lrc(lrc)

            # If plain lyrics exist and upgrade is enabled, ask user
            if existing_lrc_state == "plain" and config.get("upgrade_plain_to_synced", True):
                log("   ℹ Found plain lyrics (.lrc file)")

                ui_result = {"done": False, "upgrade": False}

                def ask_on_main():
                    result = messagebox.askyesno(
                        "Upgrade Plain Lyrics?",
                        f"Found plain lyrics for:\n{song_name}\n\n"
                        "Search for a synced version?",
                        parent=root
                    )
                    ui_result["upgrade"] = result
                    ui_result["done"] = True

                ui_call(ask_on_main)
                while not ui_result["done"]:
                    if should_cancel():
                        break
                    import time
                    time.sleep(0.1)

                if should_cancel():
                    break

                if ui_result["upgrade"]:
                    log("   🔄 Searching for synced version...")
                    inferred_artist = infer_artist_from_path(song) or (selected_artists[0] if selected_artists else "")
                    query = f"{title} {inferred_artist}".strip()

                    found_synced = False
                    for p in providers_synced:
                        if should_cancel():
                            break
                        log(f"      trying synced: {p}")
                        temp_lrc = lrc + ".temp"
                        if run_provider(query, p, temp_lrc, lang_code, want_synced=True):
                            if analyze_lrc(temp_lrc) == "synced":
                                try:
                                    os.remove(lrc)
                                    os.rename(temp_lrc, lrc)
                                    log(f"      ⬆ Upgraded plain → synced [{p}]")
                                    success_count += 1
                                    found_synced = True
                                    break
                                except:
                                    pass
                            else:
                                try:
                                    os.remove(temp_lrc)
                                except:
                                    pass

                    if not found_synced:
                        log("      ↪ No synced version found, keeping plain .lrc")
                else:
                    log("   ↪ Skipped upgrade, keeping plain .lrc")

                continue  # Move to next song

            # Skip if .lrc already exists (synced, plain, or incomplete)
            if existing_lrc_state in ("synced", "incomplete"):
                log(f"   ↪ Skip (already has .lrc)")
                continue

        inferred_artist = infer_artist_from_path(song) or (selected_artists[0] if selected_artists else "")
        query = f"{title} {inferred_artist}".strip()

        used = None
        mode = None

        for p in providers_synced:
            if should_cancel():
                break
            log(f"   trying synced: {p}")
            if run_provider(query, p, lrc, lang_code, want_synced=True):
                used, mode = p, "synced"
                break

        if (not os.path.exists(lrc)) and plain_ok and (not should_cancel()):
            for p in providers_plain:
                if should_cancel():
                    break
                log(f"   trying plain: {p}")
                if run_provider(query, p, lrc, lang_code, want_synced=False):
                    used, mode = p, "plain"
                    break

        if os.path.exists(lrc):
            if config.get("strip_cjk", True):
                if strip_cjk_lines_in_lrc(lrc):
                    log("   🧹 Stripped CJK lines")

            if reject_if_mostly_non_ascii(lrc):
                log(f"   ⚠ Rejected (mostly non-ASCII) [{used}/{mode}]")
                failed_count += 1
                continue

            log(f"   ✔ Saved [{used}/{mode}]")
            success_count += 1
        else:
            log("   ✖ Not found")
            failed_count += 1

    log("\nDone.\n")
    
    # Show detailed results
    if cancel_requested:
        set_status(f"Cancelled. Downloaded: {success_count}/{total} ({failed_count} failed)")
    else:
        set_status(f"Done. Downloaded: {success_count}/{total} ({failed_count} failed)", color="success")

    # Store which items were downloaded and mark as scanned
    global scanned_artists
    temp_scanned = set()
    for song in targets:
        artist = infer_artist_from_path(song)
        if artist:
            temp_scanned.add(artist)
            scanned_artists.add(artist)  # Mark for icon display

    missing_targets = []
    ui_call(missing_scan_btn.configure, {"text": "Scan Missing (Selection) [0]"})
    ui_call(missing_dl_btn.configure, {"state": "disabled"})
    
    # Clear cache for downloaded artists to force rescan with updated icons
    for artist in temp_scanned:
        ap = os.path.join(MUSIC_DIR, artist)
        keys_to_remove = [k for k in lyrics_cache.keys() if isinstance(k, tuple) and k[0].startswith(ap)]
        for k in keys_to_remove:
            lyrics_cache.pop(k, None)
    
    ui_call(refresh_artist_list, True)
    ui_call(refresh_current_view)

    downloading = False
    ui_call(dl_btn.configure, {"state": "normal"})
    ui_call(open_btn.configure, {"state": "normal"})
    ui_call(custom_btn.configure, {"state": "normal"})
    ui_call(missing_scan_btn.configure, {"state": "normal"})
    ui_call(missing_dl_btn.configure, {"state": "normal"})
    ui_call(cancel_btn.configure, {"state": "disabled"})


# ------------------ Missing (Selection-only) ------------------

def build_missing_for_selection():
    global missing_targets
    missing_targets = []

    if not MUSIC_DIR or not os.path.isdir(MUSIC_DIR):
        return

    selected_artists = [strip_icon(artist_list.get(i)) for i in artist_list.curselection()]

    if not selected_artists:
        log("Missing scan: no artist selected (selection-only).")
        set_status("Select an artist/album/track first.")
        return

    # Count what we're about to scan
    if len(selected_artists) > 1:
        item_desc = f"{len(selected_artists)} artists"
    else:
        sel_albums = [strip_icon(album_list.get(i)) for i in album_list.curselection()]
        if track_list.curselection():
            item_desc = f"{len(track_list.curselection())} tracks"
        elif sel_albums:
            item_desc = f"{len(sel_albums)} albums"
        else:
            item_desc = "1 artist"

    set_status(f"Scanning {item_desc}...")
    log(f"Scanning {item_desc}...")

    if len(selected_artists) > 1:
        roots = [os.path.join(MUSIC_DIR, a) for a in selected_artists]
        for root_dir in roots:
            for rd, _, files in os.walk(root_dir):
                for f in files:
                    if f.lower().endswith((".mp3", ".flac")):
                        song = os.path.join(rd, f)
                        lrc = os.path.splitext(song)[0] + ".lrc"
                        
                        
                        if not os.path.exists(lrc):
                            missing_targets.append(song)
    else:
        artist = selected_artists[0]
        base_artist = os.path.join(MUSIC_DIR, artist)

        if track_list.curselection():
            for i in track_list.curselection():
                song = resolve_track_display_to_path(artist, track_list.get(i))
                if os.path.isfile(song) and song.lower().endswith((".mp3", ".flac")):
                    lrc = os.path.splitext(song)[0] + ".lrc"
                    
                    
                    if not os.path.exists(lrc):
                        missing_targets.append(song)
        else:
            sel_albums = [strip_icon(album_list.get(i)) for i in album_list.curselection()]
            roots = [os.path.join(base_artist, alb) for alb in sel_albums] if sel_albums else [base_artist]

            for root_dir in roots:
                for rd, _, files in os.walk(root_dir):
                    for f in files:
                        if f.lower().endswith((".mp3", ".flac")):
                            song = os.path.join(rd, f)
                            lrc = os.path.splitext(song)[0] + ".lrc"
                            
                            
                            if not os.path.exists(lrc):
                                missing_targets.append(song)

    seen = set()
    missing_targets = [p for p in missing_targets if not (p in seen or seen.add(p))]

    log(f"Missing scan (selection): {len(missing_targets)} tracks missing .lrc")
    set_status(f"Missing: {len(missing_targets)} tracks without lyrics")
    
    # Update button text
    missing_scan_btn.configure(text=f"Scan Missing (Selection) [{len(missing_targets)}]")
    missing_dl_btn.configure(state=("normal" if missing_targets else "disabled"))
    
    # Mark these artists as scanned so icons will show
    global scanned_artists
    for artist in selected_artists:
        scanned_artists.add(artist)
    
    # Clear cache for scanned items to force rescan with icons
    for artist in selected_artists:
        ap = os.path.join(MUSIC_DIR, artist)
        keys_to_remove = [k for k in lyrics_cache.keys() if isinstance(k, tuple) and k[0].startswith(ap)]
        for k in keys_to_remove:
            lyrics_cache.pop(k, None)
    
    # Refresh the view to show icons for scanned items
    refresh_artist_list(keep_selection=True)
    refresh_current_view()


def start_download_missing():
    global missing_targets
    
    if downloading:
        return
    
    # If no missing targets built yet, build them first
    if not missing_targets:
        build_missing_for_selection()
    
    if not missing_targets:
        messagebox.showinfo("Missing", "No missing tracks found for this selection.")
        return

    cancel_btn.configure(state="normal")
    threading.Thread(target=download_missing_queue, daemon=True).start()


def download_missing_queue():
    global downloading, missing_targets

    if not missing_targets:
        return
    if not MUSIC_DIR or not os.path.isdir(MUSIC_DIR):
        return

    downloading = True
    ui_call(dl_btn.configure, {"state": "disabled"})
    ui_call(open_btn.configure, {"state": "disabled"})
    ui_call(custom_btn.configure, {"state": "disabled"})
    ui_call(missing_scan_btn.configure, {"state": "disabled"})
    ui_call(missing_dl_btn.configure, {"state": "disabled"})

    targets = list(missing_targets)
    providers_synced = get_synced_provider_order()
    providers_plain = get_plain_provider_order()
    lang_code = get_lang_code()
    plain_ok = allow_plain_fallback()

    total = len(targets)
    set_status(f"Downloading missing… ({total} tracks)", "working")
    log(f"\nProcessing {total} missing tracks...\n")
    
    success_count = 0
    failed_count = 0

    for idx, song in enumerate(targets, 1):
        if should_cancel():
            log("🛑 Cancelled by user.")
            break

        lrc = os.path.splitext(song)[0] + ".lrc"
        
        song_name = os.path.basename(song)
        title = normalize_title(os.path.splitext(song_name)[0])

        set_status(f"[{idx}/{total}] {song_name}", "working")
        log(f"[{idx}/{total}] Searching: {title}")

        # Check if we already have lyrics
        existing_lrc_state = None
        if os.path.exists(lrc):
            existing_lrc_state = analyze_lrc(lrc)
            
            # If plain lyrics exist and upgrade is enabled, try to find synced version
            if existing_lrc_state == "plain" and config.get("upgrade_plain_to_synced", True):
                log("   ℹ Found plain lyrics - searching for synced version...")
                
                inferred_artist = infer_artist_from_path(song)
                query = f"{title} {inferred_artist}".strip()
                
                # Try to find synced version
                found_synced = False
                for p in providers_synced:
                    if should_cancel():
                        break
                    log(f"   trying synced: {p}")
                    
                    # Save to temp file first
                    temp_lrc = lrc + ".temp"
                    if run_provider(query, p, temp_lrc, lang_code, want_synced=True):
                        # Check if it's actually synced
                        if analyze_lrc(temp_lrc) == "synced":
                            # Replace plain with synced
                            try:
                                os.remove(lrc)
                                os.rename(temp_lrc, lrc)
                                log(f"   ⬆ Upgraded plain → synced [{p}]")
                                success_count += 1
                                found_synced = True
                                break
                            except:
                                pass
                        else:
                            # Not actually synced, remove temp
                            try:
                                os.remove(temp_lrc)
                            except:
                                pass
                
                if not found_synced:
                    log("   ↪ No synced version found, keeping plain lyrics")
                
                continue  # Move to next song

        inferred_artist = infer_artist_from_path(song)
        query = f"{title} {inferred_artist}".strip()

        used = None
        mode = None

        for p in providers_synced:
            if should_cancel():
                break
            log(f"   trying synced: {p}")
            if run_provider(query, p, lrc, lang_code, want_synced=True):
                used, mode = p, "synced"
                break

        if (not os.path.exists(lrc)) and plain_ok and (not should_cancel()):
            for p in providers_plain:
                if should_cancel():
                    break
                log(f"   trying plain: {p}")
                if run_provider(query, p, lrc, lang_code, want_synced=False):
                    used, mode = p, "plain"
                    break

        if os.path.exists(lrc):
            if config.get("strip_cjk", True):
                if strip_cjk_lines_in_lrc(lrc):
                    log("   🧹 Stripped CJK lines")

            if reject_if_mostly_non_ascii(lrc):
                log(f"   ⚠ Rejected (mostly non-ASCII) [{used}/{mode}]")
                failed_count += 1
                continue

            log(f"   ✔ Saved [{used}/{mode}]")
            success_count += 1
        else:
            log("   ✖ Not found")
            failed_count += 1

    log("\nDone.\n")
    
    # Show detailed results with color
    if cancel_requested:
        set_status(f"Cancelled. Downloaded: {success_count}/{total} ({failed_count} failed)", "error")
    else:
        set_status(f"Done. Downloaded: {success_count}/{total} ({failed_count} failed)", "success")

    # Mark artists as scanned and clear their cache
    global scanned_artists
    temp_scanned = set()
    for song in targets:
        artist = infer_artist_from_path(song)
        if artist:
            temp_scanned.add(artist)
            scanned_artists.add(artist)  # Mark for icon display

    missing_targets = []
    ui_call(missing_scan_btn.configure, {"text": "Scan Missing (Selection) [0]"})
    ui_call(missing_dl_btn.configure, {"state": "disabled"})
    
    # Clear cache for scanned artists to force rescan with updated icons
    for artist in temp_scanned:
        ap = os.path.join(MUSIC_DIR, artist)
        keys_to_remove = [k for k in lyrics_cache.keys() if isinstance(k, tuple) and k[0].startswith(ap)]
        for k in keys_to_remove:
            lyrics_cache.pop(k, None)
    
    ui_call(refresh_artist_list, True)
    ui_call(refresh_current_view)

    downloading = False
    ui_call(dl_btn.configure, {"state": "normal"})
    ui_call(open_btn.configure, {"state": "normal"})
    ui_call(custom_btn.configure, {"state": "normal"})
    ui_call(missing_scan_btn.configure, {"state": "normal"})
    ui_call(missing_dl_btn.configure, {"state": "normal"})
    ui_call(cancel_btn.configure, {"state": "disabled"})


# ------------------ Custom Search ------------------

def open_custom_search():
    artist = get_selected_artist_name()
    if not artist:
        messagebox.showinfo("Custom Search", "Select exactly ONE artist first.")
        return
    if not track_list.curselection() or len(track_list.curselection()) != 1:
        messagebox.showinfo("Custom Search", "Select exactly ONE track to custom search.")
        return

    disp = track_list.get(track_list.curselection()[0])
    song_path = resolve_track_display_to_path(artist, disp)
    if not os.path.isfile(song_path):
        # Try to provide helpful error message
        display_name = strip_icon(disp)
        messagebox.showerror(
            "Custom Search", 
            f"Could not find track file:\n\n{display_name}\n\n" +
            f"Expected path:\n{song_path}\n\n" +
            "This might be due to special characters or file system issues."
        )
        return

    title_guess = normalize_title(os.path.splitext(os.path.basename(song_path))[0])
    
    # Build query as: Artist: Album - Track
    sel_albums = [strip_icon(album_list.get(i)) for i in album_list.curselection()]
    album_guess = sel_albums[0] if sel_albums else ""
    
    if album_guess:
        default_query = f"{artist}: {album_guess} - {title_guess}".strip()
    else:
        default_query = f"{artist}: {title_guess}".strip()

    def apply_strip_punctuation(s: str) -> str:
        """Remove all punctuation, keep only letters, numbers, spaces and hyphens as separators"""
        result = ""
        for ch in s:
            if ch == "-":
                result += ch  # Keep hyphens as separators
            elif ch == ":":
                result += ch  # Keep colons as separators
            elif ch.isalnum() or ch.isspace():
                result += ch
            # Strip everything else: apostrophes, commas, periods, !, ?, ', etc.
        return " ".join(result.split())  # Clean up extra spaces

    t = THEMES[config.get("theme", "dark")]
    win = tk.Toplevel(root)
    win.title("Custom Search")
    win.configure(bg=t["bg"])
    win.grab_set()
    popup_over_root(win, 580, 270)

    tk.Label(win, text="Search query to use:", bg=t["bg"], fg=t["fg"],
             font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(12, 4))

    qvar = tk.StringVar(value=default_query)
    entry = tk.Entry(win, textvariable=qvar, bg=t["panel"], fg=t["fg"],
                     insertbackground=t["fg"], font=("Segoe UI", 10))
    entry.pack(fill="x", padx=12)
    entry.focus_set()
    entry.selection_range(0, tk.END)

    hint = "Tip: remove stuff like (remix), (live), feat., etc."
    tk.Label(win, text=hint, bg=t["bg"], fg=t["fg"],
             font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(4, 6))

    # Strip punctuation checkbox
    strip_var = tk.BooleanVar(value=False)
    dedup_var = tk.BooleanVar(value=False)

    def clean_query(s: str) -> str:
        result = s
        if dedup_var.get():
            parts = result.split(" - ")
            cleaned = []
            artist_lower = artist.lower()
            artist_seen = False
            for part in parts:
                part_stripped = part.strip()
                part_lower = part_stripped.lower()
                if part_lower.startswith(artist_lower):
                    after = part_lower[len(artist_lower):]
                    # Matches if: exact artist, OR artist followed by space/colon/comma
                    # e.g. "Cypress Hill feat ..." or "Boyz II Men: Album" or "Boyz II Men"
                    is_artist_variant = (after == "" or after[0] in " :,")
                    if is_artist_variant:
                        if not artist_seen:
                            artist_seen = True
                            cleaned.append(part_stripped)  # Keep first occurrence
                        else:
                            continue  # Skip duplicate
                    else:
                        cleaned.append(part_stripped)
                else:
                    cleaned.append(part_stripped)
            result = " - ".join(cleaned)
        if strip_var.get():
            result = apply_strip_punctuation(result)
        return result

    def apply_all_cleaning():
        qvar.set(clean_query(default_query))
        entry.selection_range(0, tk.END)

    def on_strip_toggle():
        apply_all_cleaning()

    def on_dedup_toggle():
        apply_all_cleaning()

    tk.Checkbutton(
        win, text="Remove duplicate artist  (e.g.  \"Adele: 21 - Adele - Someone Like You\"  →  \"Adele: 21 - Someone Like You\")",
        variable=dedup_var,
        bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
        activebackground=t["bg"], activeforeground=t["fg"],
        font=("Segoe UI", 8),
        command=on_dedup_toggle,
        wraplength=540, justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 4))

    tk.Checkbutton(
        win, text="Strip punctuation  (e.g.  \"Guns N' Roses - Don't Cry\"  →  \"Guns N Roses - Dont Cry\")",
        variable=strip_var,
        bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
        activebackground=t["bg"], activeforeground=t["fg"],
        font=("Segoe UI", 8),
        command=on_strip_toggle,
        wraplength=540, justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 6))

    btns = tk.Frame(win, bg=t["bg"])
    btns.pack(fill="x", padx=12, pady=8)

    def run_custom():
        query = qvar.get().strip()
        if not query:
            return

        def worker():
            global downloading, cancel_requested
            cancel_requested = False
            downloading = True

            ui_call(dl_btn.configure, {"state": "disabled"})
            ui_call(open_btn.configure, {"state": "disabled"})
            ui_call(custom_btn.configure, {"state": "disabled"})
            ui_call(missing_scan_btn.configure, {"state": "disabled"})
            ui_call(missing_dl_btn.configure, {"state": "disabled"})
            ui_call(cancel_btn.configure, {"state": "normal"})

            lrc = os.path.splitext(song_path)[0] + ".lrc"
            lrc = os.path.splitext(song_path)[0] + ".lrc"

            providers_synced = get_synced_provider_order()
            providers_plain = get_plain_provider_order()
            lang_code = get_lang_code()
            plain_ok = allow_plain_fallback()

            log(f"\nCustom search for: {os.path.basename(song_path)}")
            log(f"Query: {query}")

            used = None
            mode = None

            if os.path.exists(lrc):
                log("   (Existing .lrc found — deleting and re-downloading)")
                try:
                    os.remove(lrc)
                except:
                    pass

            for p in providers_synced:
                if should_cancel():
                    break
                log(f"   trying synced: {p}")
                if run_provider(query, p, lrc, lang_code, want_synced=True):
                    used, mode = p, "synced"
                    break

            if (not os.path.exists(lrc)) and plain_ok and (not should_cancel()):
                for p in providers_plain:
                    if should_cancel():
                        break
                    log(f"   trying plain: {p}")
                    if run_provider(query, p, lrc, lang_code, want_synced=False):
                        used, mode = p, "plain"
                        break

            if os.path.exists(lrc):
                if config.get("strip_cjk", True):
                    if strip_cjk_lines_in_lrc(lrc):
                        log("   🧹 Stripped CJK lines")
                if reject_if_mostly_non_ascii(lrc):
                    log(f"   ⚠ Rejected (mostly non-ASCII) [{used}/{mode}]")
                else:
                    log(f"   ✔ Saved [{used}/{mode}]")
            else:
                log("   ✖ Not found")

            # Mark artist as scanned and refresh icons
            artist = infer_artist_from_path(song_path)
            if artist:
                scanned_artists.add(artist)
                ap = os.path.join(MUSIC_DIR, artist)
                keys_to_remove = [k for k in lyrics_cache.keys() if isinstance(k, tuple) and k[0].startswith(ap)]
                for k in keys_to_remove:
                    lyrics_cache.pop(k, None)
            
            ui_call(refresh_artist_list, True)
            ui_call(refresh_current_view)

            downloading = False
            ui_call(dl_btn.configure, {"state": "normal"})
            ui_call(open_btn.configure, {"state": "normal"})
            ui_call(custom_btn.configure, {"state": "normal"})
            ui_call(missing_scan_btn.configure, {"state": "normal"})
            ui_call(missing_dl_btn.configure, {"state": "normal"})
            ui_call(cancel_btn.configure, {"state": "disabled"})
            set_status("Done.")

        win.destroy()
        threading.Thread(target=worker, daemon=True).start()

    tk.Button(
        btns, text="Download using this query", command=run_custom,
        bg=t["btn_bg"], fg=t["btn_fg"],
        activebackground=t["btn_bg"], activeforeground=t["btn_fg"]
    ).pack(side="left")

    tk.Button(
        btns, text="Cancel", command=win.destroy,
        bg=t["btn_bg"], fg=t["btn_fg"],
        activebackground=t["btn_bg"], activeforeground=t["btn_fg"]
    ).pack(side="right")


# ------------------ About / Help ------------------

def about():
    t = THEMES[config.get("theme", "dark")]
    win = tk.Toplevel(root)
    win.title("About")
    win.configure(bg=t["bg"])
    win.grab_set()
    popup_over_root(win, 760, 560)

    tk.Label(
        win, text=APP_NAME,
        bg=t["bg"], fg=t["fg"],
        font=("Segoe UI", 14, "bold")
    ).pack(anchor="w", padx=14, pady=(14, 6))

    body = (
        "Downloads synced (.lrc) lyrics next to your music files.\n\n"
        "How it works:\n"
        "  - Select artists, albums or tracks then click Download Lyrics For Selection\n"
        "  - Always tries synced lyrics first, optional plain fallback via Settings\n"
        "  - Use Scan Missing to find tracks without lyrics, then Download Missing\n"
        "  - Double-click any track to open Custom Search for hard-to-find tracks\n"
        "  - Cancel stops safely after finishing the current track\n"
        "  - Icons appear after scanning — select an artist and click Scan Missing\n\n"
        "Tips:\n"
        "  - In Custom Search, remove (remix), (live), feat. etc. for better results\n"
        "  - Getting non-English results? Disable NetEase or raise the reject threshold\n"
        "  - Provider priority and language are configurable in Settings → Options\n\n"
        "Requirements:\n"
        "  Windows:\n"
        "    - Python 3.10+  →  python.org/downloads\n"
        "    - syncedlyrics  →  pip install syncedlyrics\n"
        "    - tkinter (included with standard Python install)\n\n"
        "  Linux:\n"
        "    - Python 3.10+  →  sudo apt install python3\n"
        "    - syncedlyrics  →  pip install syncedlyrics\n"
        "    - tkinter       →  sudo apt install python3-tk\n"
    )

    tk.Label(
        win, text=body, justify="left",
        bg=t["bg"], fg=t["fg"],
        font=("Segoe UI", 10)
    ).pack(anchor="w", padx=14)

    link_lbl = tk.Label(
        win, text="syncedlyrics on PyPI",
        bg=t["bg"], fg=t["link_fg"],
        cursor="hand2",
        font=("Segoe UI", 10, "underline")
    )
    link_lbl.pack(anchor="w", padx=14, pady=(10, 10))
    link_lbl.bind("<Button-1>", lambda e: open_syncedlyrics())

    btns = tk.Frame(win, bg=t["bg"])
    btns.pack(fill="x", padx=14, pady=14)

    tk.Button(
        btns, text="Open GitHub", command=open_github,
        bg=t["btn_bg"], fg=t["btn_fg"],
        activebackground=t["btn_bg"], activeforeground=t["btn_fg"]
    ).pack(side="left")

    tk.Button(
        btns, text="Close", command=win.destroy,
        bg=t["btn_bg"], fg=t["btn_fg"],
        activebackground=t["btn_bg"], activeforeground=t["btn_fg"]
    ).pack(side="right")


# ------------------ Options Window (WITH PRIORITY REORDERING) ------------------

def open_options_window():
    if downloading:
        messagebox.showinfo("Busy", "Wait for the current download to finish first.")
        return

    t = THEMES[config.get("theme", "dark")]
    win = tk.Toplevel(root)
    win.title("Options")
    win.configure(bg=t["bg"])
    win.grab_set()
    popup_over_root(win, 880, 590)

    enabled_map = dict(config.get("providers_enabled", {p: True for p in ALL_PROVIDERS}))
    order = list(config.get("providers_order", ALL_PROVIDERS))
    lang = config.get("lang", "en")
    plain_ok = bool(config.get("allow_plain_fallback", False))
    strip_cjk = bool(config.get("strip_cjk", True))
    reject_non_ascii = bool(config.get("reject_non_ascii", True))
    ratio = float(config.get("reject_non_ascii_ratio", 0.15))
    status_on = bool(config.get("show_lyrics_status", False))

    frm = tk.Frame(win, bg=t["bg"])
    frm.pack(fill="both", expand=True, padx=12, pady=12)

    left = tk.Frame(frm, bg=t["bg"])
    left.pack(side="left", fill="y")

    mid = tk.Frame(frm, bg=t["bg"])
    mid.pack(side="left", fill="both", expand=True, padx=(12, 0))

    tk.Label(left, text="Providers", bg=t["bg"], fg=t["fg"], font=("Segoe UI", 11, "bold")).pack(anchor="w")

    plain_var = tk.BooleanVar(value=plain_ok)
    provider_vars = {}

    tk.Label(mid, text="Priority (top = tried first)", bg=t["bg"], fg=t["fg"],
             font=("Segoe UI", 11, "bold")).pack(anchor="w")

    pri_frame = tk.Frame(mid, bg=t["bg"])
    pri_frame.pack(fill="both", expand=True)

    pri_list = tk.Listbox(
        pri_frame, exportselection=False,
        bg=t["panel"], fg=t["fg"],
        selectbackground=t["sel_bg"], selectforeground=t["sel_fg"],
        highlightbackground=t["border"], highlightcolor=t["border"]
    )
    pri_scroll = tk.Scrollbar(pri_frame, orient="vertical", command=pri_list.yview)
    pri_list.configure(yscrollcommand=pri_scroll.set)
    pri_list.pack(side="left", fill="both", expand=True)
    pri_scroll.pack(side="right", fill="y")

    def render_priority_list(select_index=None):
        pri_list.delete(0, tk.END)
        for p in order:
            is_enabled = bool(provider_vars[p].get())
            if p == "Genius" and not plain_var.get():
                is_enabled = False
            pri_list.insert(tk.END, f"✔ {p}" if is_enabled else f"✖ {p} (disabled)")
        if select_index is not None and 0 <= select_index < pri_list.size():
            pri_list.selection_set(select_index)
            pri_list.activate(select_index)

    def on_toggle_plain():
        if not plain_var.get():
            provider_vars["Genius"].set(False)
        render_priority_list(pri_list.curselection()[0] if pri_list.curselection() else None)
        genius_cb.configure(state=("normal" if plain_var.get() else "disabled"))

    tk.Checkbutton(
        left, text="Allow plain lyrics fallback",
        variable=plain_var,
        bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
        activebackground=t["bg"], activeforeground=t["fg"],
        command=on_toggle_plain
    ).pack(anchor="w", pady=(0, 6))
    
    upgrade_var = tk.BooleanVar(value=config.get("upgrade_plain_to_synced", True))
    tk.Checkbutton(
        left, text="Auto-upgrade plain → synced",
        variable=upgrade_var,
        bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
        activebackground=t["bg"], activeforeground=t["fg"]
    ).pack(anchor="w", pady=(0, 10))

    genius_cb = None

    def on_toggle_provider(pname: str):
        if pname == "Genius" and provider_vars["Genius"].get() and not plain_var.get():
            plain_var.set(True)
            genius_cb.configure(state="normal")
        render_priority_list(pri_list.curselection()[0] if pri_list.curselection() else None)

    for p in ALL_PROVIDERS:
        v = tk.BooleanVar(value=enabled_map.get(p, True))
        provider_vars[p] = v
        cb = tk.Checkbutton(
            left, text=p, variable=v,
            bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            command=lambda name=p: on_toggle_provider(name)
        )
        cb.pack(anchor="w")
        if p == "Genius":
            genius_cb = cb

    genius_cb.configure(state=("normal" if plain_var.get() else "disabled"))
    if not plain_var.get():
        provider_vars["Genius"].set(False)

    render_priority_list(0 if order else None)

    btns = tk.Frame(mid, bg=t["bg"])
    btns.pack(fill="x", pady=(6, 0))

    def move_up():
        sel = pri_list.curselection()
        if not sel:
            return
        i = sel[0]
        if i == 0:
            return
        order[i - 1], order[i] = order[i], order[i - 1]
        render_priority_list(i - 1)

    def move_down():
        sel = pri_list.curselection()
        if not sel:
            return
        i = sel[0]
        if i >= len(order) - 1:
            return
        order[i + 1], order[i] = order[i], order[i + 1]
        render_priority_list(i + 1)

    tk.Button(btns, text="Up", command=move_up, width=10,
              bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"]).pack(side="left")
    tk.Button(btns, text="Down", command=move_down, width=10,
              bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"]).pack(side="left", padx=(8, 0))

    bottom_opts = tk.Frame(win, bg=t["bg"])
    bottom_opts.pack(fill="x", padx=12, pady=(10, 12))

    tk.Label(bottom_opts, text="Lyrics Language:", bg=t["bg"], fg=t["fg"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
    lang_var = tk.StringVar(value=lang)
    tk.Entry(bottom_opts, textvariable=lang_var, width=6,
             bg=t["panel"], fg=t["fg"], insertbackground=t["fg"],
             highlightbackground=t["border"], highlightcolor=t["border"]).grid(row=0, column=1, sticky="w", padx=(8, 0))
    tk.Label(bottom_opts, text="(en, es, fr… or blank = auto)",
             bg=t["bg"], fg=t["fg"]).grid(row=0, column=2, sticky="w", padx=(10, 0))

    strip_var = tk.BooleanVar(value=strip_cjk)
    tk.Checkbutton(
        bottom_opts, text="Strip CJK lines from downloaded LRC (optional cleanup)",
        variable=strip_var, bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
        activebackground=t["bg"], activeforeground=t["fg"]
    ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))

    rej_var = tk.BooleanVar(value=reject_non_ascii)
    tk.Checkbutton(
        bottom_opts, text="Reject lyrics files that are mostly non-ASCII (good for English)",
        variable=rej_var, bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
        activebackground=t["bg"], activeforeground=t["fg"]
    ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

    tk.Label(bottom_opts, text="Reject threshold (0.05–0.50):", bg=t["bg"], fg=t["fg"]).grid(row=3, column=0, sticky="w", pady=(6, 0))
    ratio_var = tk.StringVar(value=str(ratio))
    tk.Entry(bottom_opts, textvariable=ratio_var, width=8,
             bg=t["panel"], fg=t["fg"], insertbackground=t["fg"],
             highlightbackground=t["border"], highlightcolor=t["border"]).grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

    status_var_local = tk.BooleanVar(value=status_on)
    tk.Checkbutton(
        bottom_opts, text="Show artist/album/track lyrics status (slower)",
        variable=status_var_local, bg=t["bg"], fg=t["fg"], selectcolor=t["bg"],
        activebackground=t["bg"], activeforeground=t["fg"]
    ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(12, 0))

    footer = tk.Frame(win, bg=t["bg"])
    footer.pack(fill="x", padx=12, pady=12)

    def on_save():
        fixed, seen = [], set()
        for p in order:
            if p in ALL_PROVIDERS and p not in seen:
                fixed.append(p); seen.add(p)
        for p in ALL_PROVIDERS:
            if p not in seen:
                fixed.append(p)

        try:
            r = float(ratio_var.get())
            r = max(0.05, min(0.50, r))
        except:
            r = 0.15

        plain = bool(plain_var.get())
        if not plain:
            provider_vars["Genius"].set(False)

        config["allow_plain_fallback"] = plain
        config["upgrade_plain_to_synced"] = bool(upgrade_var.get())
        config["providers_enabled"] = {p: bool(provider_vars[p].get()) for p in ALL_PROVIDERS}
        config["providers_order"] = fixed
        config["lang"] = lang_var.get()
        config["strip_cjk"] = bool(strip_var.get())
        config["reject_non_ascii"] = bool(rej_var.get())
        config["reject_non_ascii_ratio"] = r
        config["show_lyrics_status"] = bool(status_var_local.get())

        save_config(config)
        lyrics_cache.clear()
        missing_targets.clear()
        win.destroy()
        load_artists()

    tk.Button(footer, text="Cancel", command=win.destroy, width=10,
              bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"]).pack(side="right")
    tk.Button(footer, text="Save", command=on_save, width=10,
              bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"]).pack(side="right", padx=(0, 8))


# ------------------ Selection helpers ------------------

def select_all_in_listbox(lb: tk.Listbox):
    if lb.size() > 0:
        lb.selection_set(0, tk.END)
        lb.activate(0)


def clear_missing_state():
    """Clear missing targets when user manually changes selection"""
    global missing_targets
    missing_targets = []
    missing_scan_btn.configure(text="Scan Missing (Selection) [0]")
    update_missing_dl_button_state()


def clear_all_selections():
    global missing_targets
    artist_list.selection_clear(0, tk.END)
    album_list.selection_clear(0, tk.END)
    track_list.selection_clear(0, tk.END)
    missing_targets = []
    missing_scan_btn.configure(text="Scan Missing (Selection) [0]")
    missing_dl_btn.configure(state="disabled")
    set_status("Selection cleared")
    
    # Reset all toggle buttons to "Select All"
    artist_select_btn.configure(text="Select All", command=toggle_artist_selection)
    album_select_btn.configure(text="Select All", command=toggle_album_selection)
    track_select_btn.configure(text="Select All", command=toggle_track_selection)


def toggle_artist_selection():
    if artist_list.size() == 0:
        # No items to select
        return
    
    # Check if ALL items are selected
    all_selected = (len(artist_list.curselection()) == artist_list.size())
    
    if all_selected:
        # All selected - clear everything
        artist_list.selection_clear(0, tk.END)
        artist_select_btn.configure(text="Select All", command=toggle_artist_selection)
        on_artist_select(None)
    else:
        # Not all selected (even if some are) - select all
        select_all_in_listbox(artist_list)
        artist_select_btn.configure(text="Clear All", command=toggle_artist_selection)
        on_artist_select(None)


def toggle_album_selection():
    if album_list.size() == 0:
        # No items to select
        return
    
    # Check if ALL items are selected
    all_selected = (len(album_list.curselection()) == album_list.size())
    
    if all_selected:
        # All selected - clear everything
        album_list.selection_clear(0, tk.END)
        album_select_btn.configure(text="Select All", command=toggle_album_selection)
        on_album_select(None)
    else:
        # Not all selected (even if some are) - select all
        select_all_in_listbox(album_list)
        album_select_btn.configure(text="Clear All", command=toggle_album_selection)
        on_album_select(None)


def toggle_track_selection():
    if track_list.size() == 0:
        # No items to select
        return
    
    # Check if ALL items are selected
    all_selected = (len(track_list.curselection()) == track_list.size())
    
    if all_selected:
        # All selected - clear everything
        track_list.selection_clear(0, tk.END)
        track_select_btn.configure(text="Select All", command=toggle_track_selection)
    else:
        # Not all selected (even if some are) - select all
        select_all_in_listbox(track_list)
        track_select_btn.configure(text="Clear All", command=toggle_track_selection)


def select_all_artists():
    select_all_in_listbox(artist_list)
    artist_select_btn.configure(text="Clear All", command=toggle_artist_selection)
    on_artist_select(None)


def select_all_albums():
    select_all_in_listbox(album_list)
    album_select_btn.configure(text="Clear All", command=toggle_album_selection)
    on_album_select(None)


def select_all_tracks():
    select_all_in_listbox(track_list)
    track_select_btn.configure(text="Clear All", command=toggle_track_selection)


def bind_ctrl_a(lb: tk.Listbox):
    lb.bind("<Control-a>", lambda e: (select_all_in_listbox(lb), "break"))
    lb.bind("<Control-A>", lambda e: (select_all_in_listbox(lb), "break"))


# ------------------ Theme apply ------------------

def apply_theme(theme_name: str):
    t = THEMES[theme_name]

    root.configure(bg=t["bg"])
    top.configure(bg=t["bg"])
    main.configure(bg=t["bg"])
    bottom.configure(bg=t["bg"])
    list_frame.configure(bg=t["bg"])
    btn_row.configure(bg=t["bg"])
    legend_row.configure(bg=t["bg"])
    status_bar.configure(bg=t["status_bg"])
    
    # Theme list cards
    for card in (artist_card, album_card, track_card):
        card.configure(bg=t["bg"], highlightbackground=t["border"], highlightcolor=t["border"])
    
    # Theme card headers
    for header in (artist_header, album_header, track_header):
        header.configure(bg=t["panel"])
    
    # Theme title labels
    for title_lbl in (artist_title, album_title, track_title):
        title_lbl.configure(bg=t["panel"], fg=t["fg"])
    
    # Theme Select All buttons
    for btn in (artist_select_btn, album_select_btn, track_select_btn):
        btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], 
                     activebackground=t["btn_bg"], activeforeground=t["btn_fg"])

    open_btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"])
    
    # Theme search widgets in top bar
    search_label.configure(bg=t["bg"], fg=t["fg"])
    search_entry.configure(
        bg=t["panel"], fg=t["fg"],
        insertbackground=t["fg"],
        highlightbackground=t["border"], highlightcolor=t["border"]
    )
    
    dl_btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"])
    cancel_btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"])
    custom_btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"])
    missing_scan_btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"])
    missing_dl_btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"])
    clear_btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_bg"], activeforeground=t["btn_fg"])

    for lb in (artist_list, album_list, track_list):
        lb.configure(
            bg=t["panel"], fg=t["fg"],
            selectbackground=t["sel_bg"], selectforeground=t["sel_fg"],
            highlightbackground=t["border"], highlightcolor=t["border"]
        )

    log_box.configure(
        bg=t["log_bg"], fg=t["log_fg"],
        insertbackground=t["log_fg"],
        highlightbackground=t["border"], highlightcolor=t["border"]
    )

    status_label.configure(bg=t["status_bg"], fg=t["status_fg"])

    legend_frame.configure(bg=t["legend_bg"], highlightbackground=t["legend_border"], highlightthickness=1)
    legend_title.configure(bg=t["legend_bg"], fg=t["fg"])
    legend_artist_ok.configure(bg=t["legend_bg"], fg=t["ok"])
    legend_artist_some.configure(bg=t["legend_bg"], fg=t["warn"])
    legend_artist_none.configure(bg=t["legend_bg"], fg=t["none"])
    legend_track_synced.configure(bg=t["legend_bg"], fg=t["ok"])
    legend_track_plain.configure(bg=t["legend_bg"], fg=t["plain"])
    legend_track_incomp.configure(bg=t["legend_bg"], fg=t["incomp"])
    legend_track_none.configure(bg=t["legend_bg"], fg=t["none"])

    set_titlebar_theme(theme_name == "dark")

    config["theme"] = theme_name
    save_config(config)


# ------------------ UI build ------------------

root = tk.Tk()
root.title(APP_NAME)

# Restore saved window geometry or use default
_saved_geo = config.get("window_geometry", "1180x800")
try:
    root.geometry(_saved_geo)
except:
    root.geometry("1180x800")

def save_window_geometry():
    try:
        config["window_geometry"] = root.geometry()
        save_config()
    except:
        pass

root.protocol("WM_DELETE_WINDOW", lambda: [save_window_geometry(), root.destroy()])

menubar = tk.Menu(root)

settings_menu = tk.Menu(menubar, tearoff=0)
theme_menu = tk.Menu(settings_menu, tearoff=0)
theme_var = tk.StringVar(value=config.get("theme", "dark"))
theme_menu.add_radiobutton(label="Dark", variable=theme_var, value="dark", command=lambda: apply_theme("dark"))
theme_menu.add_radiobutton(label="Light", variable=theme_var, value="light", command=lambda: apply_theme("light"))
settings_menu.add_cascade(label="Theme", menu=theme_menu)
settings_menu.add_separator()
settings_menu.add_command(label="Options…", command=open_options_window)
menubar.add_cascade(label="Settings", menu=settings_menu)

help_menu = tk.Menu(menubar, tearoff=0)
help_menu.add_command(label="Open GitHub", command=open_github)
help_menu.add_command(label="About", command=about)
menubar.add_cascade(label="Help", menu=help_menu)

root.config(menu=menubar)

top = tk.Frame(root)
top.pack(fill="x", padx=12, pady=(12, 6))

open_btn = tk.Button(top, text="Open Music Folder", command=choose_folder)
open_btn.pack(side="left")

# Add artist search next to Open Music Folder button
search_label = tk.Label(top, text="Artist Search:", font=("Segoe UI", 9))
search_label.pack(side="left", padx=(20, 6))

search_var = tk.StringVar(value="")
search_entry = tk.Entry(top, textvariable=search_var, width=30)
search_entry.pack(side="left")

def on_search(*_):
    rebuild_artist_list_filtered(keep_selection_name=get_selected_artist_name())

search_var.trace_add("write", on_search)

main = tk.Frame(root)
main.pack(fill="both", expand=True, padx=12, pady=6)

list_frame = tk.Frame(main)
list_frame.pack(fill="both", expand=True)


def make_scrolled_listbox(parent, width, selectmode=None):
    frame = tk.Frame(parent)
    lb = tk.Listbox(frame, width=width, exportselection=False, selectmode=selectmode)
    sb = tk.Scrollbar(frame, orient="vertical", command=lb.yview)
    lb.configure(yscrollcommand=sb.set)
    lb.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return frame, lb


def make_list_card(parent, title, select_all_cmd, width, selectmode):
    """Create a styled listbox card with header and Select All button"""
    card = tk.Frame(parent, highlightthickness=1, bd=0)
    
    # Header with title and Select All button
    header = tk.Frame(card)
    header.pack(fill="x", padx=2, pady=2)
    
    title_label = tk.Label(header, text=title, font=("Segoe UI", 10, "bold"), anchor="w")
    title_label.pack(side="left", padx=4)
    
    select_btn = tk.Button(header, text="Select All", command=select_all_cmd, 
                          font=("Segoe UI", 8), padx=8, pady=2)
    select_btn.pack(side="right", padx=4)
    
    # Listbox with scrollbar
    list_frame, lb = make_scrolled_listbox(card, width, selectmode)
    list_frame.pack(fill="both", expand=True, padx=2, pady=(0, 2))
    
    return card, header, title_label, select_btn, lb


artist_card, artist_header, artist_title, artist_select_btn, artist_list = \
    make_list_card(list_frame, "Artists", toggle_artist_selection, 28, tk.EXTENDED)

album_card, album_header, album_title, album_select_btn, album_list = \
    make_list_card(list_frame, "Albums", toggle_album_selection, 40, tk.EXTENDED)

track_card, track_header, track_title, track_select_btn, track_list = \
    make_list_card(list_frame, "Tracks", toggle_track_selection, 70, tk.EXTENDED)

artist_card.pack(side="left", fill="both", padx=(0, 6), pady=4)
album_card.pack(side="left", fill="both", padx=(0, 6), pady=4)
track_card.pack(side="left", fill="both", padx=(0, 0), pady=4, expand=True)

artist_list.bind("<<ListboxSelect>>", on_artist_select)
album_list.bind("<<ListboxSelect>>", on_album_select)

def on_track_select(event=None):
    # Update track button text based on selection
    if track_list.curselection():
        if len(track_list.curselection()) == track_list.size() and track_list.size() > 0:
            track_select_btn.configure(text="Clear All")
        else:
            track_select_btn.configure(text="Select All")
    else:
        track_select_btn.configure(text="Select All")

track_list.bind("<<ListboxSelect>>", on_track_select)
track_list.bind("<Double-Button-1>", lambda e: open_custom_search())

bind_ctrl_a(artist_list)
bind_ctrl_a(album_list)
bind_ctrl_a(track_list)

bottom = tk.Frame(root)
bottom.pack(fill="both", expand=True, padx=12, pady=(6, 8))

btn_row = tk.Frame(bottom)
btn_row.pack(fill="x", pady=(0, 6))

dl_btn = tk.Button(btn_row, text="Download Lyrics For Selection", command=start_download)
dl_btn.pack(side="left", padx=(0, 10))

cancel_btn = tk.Button(btn_row, text="Cancel", command=request_cancel, state="disabled")
cancel_btn.pack(side="left")

custom_btn = tk.Button(btn_row, text="Custom Search…", command=open_custom_search)
custom_btn.pack(side="left", padx=(10, 0))

missing_scan_btn = tk.Button(btn_row, text="Scan Missing (Selection) [0]", command=build_missing_for_selection)
missing_scan_btn.pack(side="left", padx=(10, 0))

missing_dl_btn = tk.Button(btn_row, text="Download Missing (Selection)", command=start_download_missing)
missing_dl_btn.pack(side="left", padx=(10, 0))

# Clear All button on right side
clear_btn = tk.Button(btn_row, text="Clear All Selections", command=clear_all_selections)
clear_btn.pack(side="right")

legend_row = tk.Frame(bottom)
legend_row.pack(fill="x", pady=(0, 8))

legend_frame = tk.Frame(legend_row, padx=10, pady=4)
legend_frame.pack(side="left", fill="x", expand=True)
legend_frame.pack_propagate(True)

legend_title = tk.Label(legend_frame, text="Legend:", font=("Segoe UI", 9, "bold"))
legend_title.pack(side="left", padx=(0, 10))

legend_artist_ok = tk.Label(legend_frame, text="Artist/Album ✅ all", font=("Segoe UI", 9))
legend_artist_ok.pack(side="left", padx=(0, 10))
legend_artist_some = tk.Label(legend_frame, text="🟨 some", font=("Segoe UI", 9))
legend_artist_some.pack(side="left", padx=(0, 10))
legend_artist_none = tk.Label(legend_frame, text="⬜ none", font=("Segoe UI", 9))
legend_artist_none.pack(side="left", padx=(0, 16))

legend_track_synced = tk.Label(legend_frame, text="Track ✅ synced", font=("Segoe UI", 9))
legend_track_synced.pack(side="left", padx=(0, 10))
legend_track_plain = tk.Label(legend_frame, text="📄 plain", font=("Segoe UI", 9))
legend_track_plain.pack(side="left", padx=(0, 10))
legend_track_incomp = tk.Label(legend_frame, text="⚠️ incomplete", font=("Segoe UI", 9))
legend_track_incomp.pack(side="left", padx=(0, 10))
legend_track_none = tk.Label(legend_frame, text="❌ none", font=("Segoe UI", 9))
legend_track_none.pack(side="left")

log_frame = tk.Frame(bottom)
log_frame.pack(fill="both", expand=True)

log_box = tk.Text(log_frame, height=14, padx=8, pady=6, wrap="none")
log_scroll = tk.Scrollbar(log_frame, orient="vertical", command=log_box.yview)
log_box.configure(yscrollcommand=log_scroll.set)
log_box.pack(side="left", fill="both", expand=True)
log_scroll.pack(side="right", fill="y")

status_var = tk.StringVar(value="Ready.")
status_bar = tk.Frame(root)
status_bar.pack(fill="x", side="bottom")

status_label = tk.Label(status_bar, textvariable=status_var, anchor="w", padx=10, pady=4)
status_label.pack(fill="x")

# Apply theme
apply_theme(config.get("theme", "dark"))
root.update()
set_titlebar_theme(config.get("theme", "dark") == "dark")

# Setup keyboard shortcuts
setup_keyboard_shortcuts()

# Add tooltips to buttons
create_tooltip(open_btn, "Open a music folder to scan (F5 to refresh)")
create_tooltip(dl_btn, "Download lyrics for selected items (Ctrl+D)")
create_tooltip(cancel_btn, "Cancel current operation (Escape)")
create_tooltip(custom_btn, "Override search query for difficult tracks")
create_tooltip(missing_scan_btn, "Scan selection to find tracks without lyrics")
create_tooltip(missing_dl_btn, "Download missing lyrics (auto-scans if needed)")
create_tooltip(clear_btn, "Clear all selections in all listboxes")
create_tooltip(artist_select_btn, "Select/Clear all artists")
create_tooltip(album_select_btn, "Select/Clear all albums")
create_tooltip(track_select_btn, "Select/Clear all tracks")

pump_ui_queue()

if MUSIC_DIR and os.path.isdir(MUSIC_DIR):
    load_artists()
else:
    set_status("Ready. Click 'Open Music Folder'.")

root.mainloop()
