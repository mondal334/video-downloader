# Universal Video & Audio Downloader

A fast, self-hosted web and CLI application to directly download videos and audio from **Instagram**, **Facebook**, **YouTube**, **TikTok**, and 1,000+ other supported platforms.

---

## Features

- 🎥 **Supported Platforms**:
  - **YouTube**: Videos, Shorts, Playlists
  - **Instagram**: Reels, Posts, Stories
  - **Facebook**: Watch, Reels, public video posts
  - **TikTok, Twitter / X, Reddit**, and many more
- 🚀 **Direct Downloads**: No external ad-filled third-party websites. Files are extracted and downloaded directly.
- 🎬 **Quality Selection**: Choose from Best Quality, 1080p, 720p, 480p, 360p.
- 🎵 **Audio Extraction**: Download high-quality MP3 or native M4A audio.
- 📊 **Real-time Progress**: Live download percentage, speed (MB/s), and ETA indicators.
- 💻 **Multiple Interfaces**:
  - **Web Dashboard**: Modern, glassmorphic, responsive user interface.
  - **Command-line Interface (CLI)**: Quick terminal commands for automated downloads.

---

## Quick Start (Web App)

### Option 1: One-Click Windows Launcher
Simply double-click:
```
run.bat
```
This will automatically launch the server and open `http://127.0.0.1:8000` in your web browser.

### Option 2: Run via Terminal
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Start the server
python app.py
```
Open your browser at `http://127.0.0.1:8000`.

---

## CLI Usage (Command Line)

You can download directly from terminal using `downloader_cli.py`:

```bash
# Check info for a video without downloading:
.\venv\Scripts\python.exe downloader_cli.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --info

# Download best video:
.\venv\Scripts\python.exe downloader_cli.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Download 720p video:
.\venv\Scripts\python.exe downloader_cli.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -q 720p

# Download Audio only as MP3:
.\venv\Scripts\python.exe downloader_cli.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --audio
```

---

## Notes on Instagram & Facebook Media

- **Public Posts & Reels**: Download directly by simply pasting the link.
- **Private or Age-Restricted Content**:
  Meta (Instagram & Facebook) sometimes requires an active session cookie to view certain posts.
  If a post requires login:
  1. Export your cookies into a `cookies.txt` file (using browser extensions like *Get cookies.txt LOCALLY* for Chrome/Edge/Firefox).
  2. Place the `cookies.txt` file in this directory (`C:\Users\suraj\.gemini\antigravity\scratch\universal_video_downloader\cookies.txt`).
  3. The downloader will automatically use the cookies to access the restricted media.
