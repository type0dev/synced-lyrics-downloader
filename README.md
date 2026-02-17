# 🎵 Synced Lyrics Downloader

A desktop GUI app for downloading synced (`.lrc`) and plain (`.txt`) lyrics for your local music library. Built with Python and tkinter — no internet browser required, no accounts, no ads.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Screenshots

> Point the app at your music folder, select artists/albums/tracks, hit Download.

---

## Features

- **Synced lyrics first** — always tries `.lrc` with timestamps before falling back to plain text
- **Plain lyrics saved as `.txt`** — keeps your library clean and organized
- **Multiple providers** — Lrclib, Musixmatch, Megalobiz, NetEase, Genius (configurable priority)
- **Smart scanning** — scan selection for missing lyrics, download only what's missing
- **Custom Search** — override the search query for hard-to-find tracks
- **Auto-upgrade** — detects plain `.lrc` files and offers to find a synced version
- **Track icons** — ✅ synced · 📄 plain · ⚠️ incomplete · ❌ none
- **Artist/Album icons** — ✅ all · 🟨 some · ⬜ none (shown after scanning)
- **Dark and Light themes**
- **Keyboard shortcuts** — `Ctrl+D` download · `Escape` cancel · `F5` refresh
- **Double-click a track** to open Custom Search instantly
- **Remembers window size and position** between sessions
- **CJK stripping** and non-ASCII rejection to avoid garbage results
- Works great on **network drives** (NAS, mapped drives)

---

## Requirements

### Windows
```
Python 3.10+      →  https://python.org/downloads
syncedlyrics      →  pip install syncedlyrics
tkinter           →  included with standard Python install
```

### Linux
```
Python 3.10+      →  sudo apt install python3
syncedlyrics      →  pip install syncedlyrics
tkinter           →  sudo apt install python3-tk
```

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/synced-lyrics-downloader.git
cd synced-lyrics-downloader

# 2. Install the only dependency
pip install syncedlyrics

# 3. Run
python lyrics_downloader_ultimate.py
```

---

## Quick Start

1. Click **Open Music Folder** and point it at your music library
2. Select an **artist** from the left panel
3. Select **albums** and/or **tracks** (or use Select All)
4. Click **Download Lyrics For Selection**
5. Watch the log panel — done!

### Finding missing lyrics

1. Select one or more artists
2. Click **Scan Missing (Selection)** — shows count of tracks without lyrics
3. Click **Download Missing (Selection)** — downloads only what's missing

### Hard-to-find tracks

1. Select an artist and a **single track**
2. Click **Custom Search** (or double-click the track)
3. Edit the search query — try removing `(feat. ...)`, `(Live)`, `(Remix)` etc.
4. Use the checkboxes to remove duplicate artist names or strip punctuation
5. Click **Download using this query**

---

## Settings

Open **Settings → Options** to configure:

| Option | Description |
|--------|-------------|
| Provider priority | Drag to reorder which providers are tried first |
| Enable/disable providers | Turn off providers that give bad results |
| Allow plain fallback | Enable Genius for plain text lyrics |
| Auto-upgrade plain → synced | Detect plain `.lrc` files and offer synced upgrade |
| Language | Preferred lyrics language code (e.g. `en`) |
| Strip CJK lines | Remove Chinese/Japanese/Korean lines from results |
| Reject mostly non-ASCII | Filter out results in wrong language |

---

## File Structure

The app saves lyrics **next to your music files**, with the same filename:

```
Music/
  Artist/
    Album/
      01 Track Name.mp3
      01 Track Name.lrc      ← synced lyrics (timestamped)
      02 Another Track.mp3
      02 Another Track.txt   ← plain lyrics (no timestamps)
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+D` | Download lyrics for selection |
| `Escape` | Cancel current download |
| `F5` | Refresh library |
| `Double-click track` | Open Custom Search |

---

## Providers

| Provider | Synced | Plain | Notes |
|----------|--------|-------|-------|
| Lrclib | ✅ | ❌ | Best first choice, open source |
| Musixmatch | ✅ | ❌ | Good coverage |
| Megalobiz | ✅ | ❌ | Good for older tracks |
| NetEase | ✅ | ❌ | Large Asian library, may give non-English results |
| Genius | ❌ | ✅ | Plain text only, requires plain fallback enabled |

---

## Config File

Settings are saved automatically to `lyrics_gui_config.json` in the same folder as the script.

---

## Built With

- [Python](https://python.org) + [tkinter](https://docs.python.org/3/library/tkinter.html) — GUI
- [syncedlyrics](https://github.com/moehmeni/syncedlyrics) — lyrics fetching library

---

## License

MIT — do whatever you want with it.
