import os
import re
import sys
import time
import logging
from typing import Dict, Any, Optional, Callable
import yt_dlp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Base downloads directory
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Cookie file path if user provides it for Instagram/Facebook login-required media
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")


def get_ffmpeg_path() -> Optional[str]:
    """Tries to find ffmpeg via imageio_ffmpeg or system path."""
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_exe and os.path.exists(ffmpeg_exe):
            return ffmpeg_exe
    except Exception as e:
        logger.debug(f"imageio_ffmpeg lookup error: {e}")
    return None


def format_duration(seconds: Optional[int]) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    if not seconds:
        return "N/A"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def detect_platform(url: str, extractor_key: str = "") -> str:
    """Detect platform from URL or extractor key."""
    url_lower = url.lower()
    extractor_lower = extractor_key.lower()

    if "youtube" in url_lower or "youtu.be" in url_lower or "youtube" in extractor_lower:
        return "YouTube"
    if "instagram" in url_lower or "instagram" in extractor_lower:
        return "Instagram"
    if "facebook" in url_lower or "fb.watch" in url_lower or "fb.com" in url_lower or "facebook" in extractor_lower:
        return "Facebook"
    if "tiktok" in url_lower or "tiktok" in extractor_lower:
        return "TikTok"
    if "twitter" in url_lower or "x.com" in url_lower or "twitter" in extractor_lower:
        return "Twitter / X"
    if "reddit" in url_lower or "reddit" in extractor_lower:
        return "Reddit"
    if "pinterest" in url_lower or "pinterest" in extractor_lower:
        return "Pinterest"
    return extractor_key or "Generic Web"


def get_ydl_base_opts() -> Dict[str, Any]:
    """Base options for yt-dlp."""
    ffmpeg_exe = get_ffmpeg_path()
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "retries": 10,
        "fragment_retries": 10,
        # Rotate clients to prevent rate limits and bot challenges
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "mweb", "web_creator", "web"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    if ffmpeg_exe:
        opts["ffmpeg_location"] = ffmpeg_exe

    if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        opts["cookiefile"] = COOKIES_FILE

    return opts


def fetch_video_info(url: str) -> Dict[str, Any]:
    """
    Extracts metadata from URL without downloading.
    Returns details including title, thumbnail, duration, author, platform, and available formats.
    """
    opts = get_ydl_base_opts()
    opts["extract_flat"] = False

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            err_msg = str(e)
            if "login" in err_msg.lower() or "private" in err_msg.lower() or "sign in" in err_msg.lower():
                raise ValueError(
                    f"This post or video requires login or is private. If you have an account, provide cookies.txt or try a public link."
                )
            raise ValueError(f"Could not retrieve video details: {err_msg}")

    if not info:
        raise ValueError("Could not extract media info from this link.")

    # In case of playlist / multi-item, pick first entry
    if "entries" in info and info["entries"]:
        info = info["entries"][0]

    title = info.get("title") or "Video"
    thumbnail = info.get("thumbnail") or ""
    duration_sec = info.get("duration")
    duration_str = format_duration(duration_sec)
    uploader = info.get("uploader") or info.get("channel") or info.get("creator") or "Creator"
    platform = detect_platform(url, info.get("extractor_key", ""))

    # Inspect formats to give resolution choices
    formats = info.get("formats") or []
    has_video = False
    has_audio = False
    available_resolutions = set()

    for f in formats:
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        height = f.get("height")
        if vcodec and vcodec != "none":
            has_video = True
            if height:
                available_resolutions.add(height)
        if acodec and acodec != "none":
            has_audio = True

    # Build selectable format list
    quality_options = []
    if has_video:
        quality_options.append({"id": "best_video", "label": "Best Video Quality (Auto)", "type": "video"})
        standard_heights = [2160, 1440, 1080, 720, 480, 360]
        for h in standard_heights:
            if any(avail >= h for avail in available_resolutions):
                quality_options.append({"id": f"{h}p", "label": f"{h}p HD/SD Video", "type": "video"})

    if has_audio or has_video:
        quality_options.append({"id": "mp3", "label": "Audio Only (MP3)", "type": "audio"})
        quality_options.append({"id": "m4a", "label": "Audio Only (Original M4A)", "type": "audio"})

    # Fallback if no specific format list detected (common for direct MP4 Instagram/FB links)
    if not quality_options:
        quality_options.append({"id": "best_video", "label": "Best Quality", "type": "video"})

    return {
        "url": url,
        "title": title,
        "thumbnail": thumbnail,
        "duration": duration_str,
        "duration_sec": duration_sec,
        "uploader": uploader,
        "platform": platform,
        "qualities": quality_options,
    }


def download_video(
    url: str,
    quality: str = "best_video",
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Downloads media from URL with the chosen quality/format.
    Supports progress callback.
    """
    opts = get_ydl_base_opts()
    opts["outtmpl"] = os.path.join(DOWNLOADS_DIR, "%(title).120B [%(id)s].%(ext)s")

    # Hook for tracking progress
    def ydl_hook(d):
        if progress_callback:
            status = d.get("status")
            if status == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                pct = 0
                if total > 0:
                    pct = round((downloaded / total) * 100, 1)
                speed = d.get("speed")
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "Calculating..."
                eta = d.get("eta")
                eta_str = f"{eta}s" if eta else ""
                
                progress_callback({
                    "status": "downloading",
                    "percent": pct,
                    "downloaded_bytes": downloaded,
                    "total_bytes": total,
                    "speed": speed_str,
                    "eta": eta_str,
                })
            elif status == "finished":
                progress_callback({
                    "status": "processing",
                    "percent": 99.0,
                    "message": "Finalizing media...",
                })

    opts["progress_hooks"] = [ydl_hook]

    # Configure formats according to selection
    if quality == "mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    elif quality == "m4a":
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    elif quality == "best_video" or quality == "best":
        opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"
    elif quality.endswith("p"):
        res_height = quality.replace("p", "")
        opts["format"] = f"bestvideo[height<={res_height}]+bestaudio/best[height<={res_height}]/best"
        opts["merge_output_format"] = "mp4"
    else:
        opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except Exception as e:
            err_str = str(e)
            if "Sign in to confirm you" in err_str:
                # Retry with mobile android/mweb format
                logger.info("Retrying with mobile format fallback...")
                opts["format"] = "best/worst"
                with yt_dlp.YoutubeDL(opts) as retry_ydl:
                    info = retry_ydl.extract_info(url, download=True)
            else:
                raise e

        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        # Determine target file path
        filename = ydl.prepare_filename(info)
        # If converted to mp3, the extension changes
        if quality == "mp3":
            base, _ = os.path.splitext(filename)
            filename = f"{base}.mp3"
        elif opts.get("merge_output_format") == "mp4":
            base, _ = os.path.splitext(filename)
            if os.path.exists(f"{base}.mp4"):
                filename = f"{base}.mp4"

        # Final check if file exists
        if not os.path.exists(filename):
            base_name = os.path.splitext(os.path.basename(filename))[0]
            for f in os.listdir(DOWNLOADS_DIR):
                if f.startswith(base_name[:30]):
                    filename = os.path.join(DOWNLOADS_DIR, f)
                    break

        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0

        result = {
            "title": info.get("title", "download"),
            "filepath": filename,
            "filename": os.path.basename(filename),
            "filesize": file_size,
            "status": "completed",
        }

        if progress_callback:
            progress_callback({
                "status": "completed",
                "percent": 100.0,
                "filename": result["filename"],
                "filesize": file_size,
            })

        return result
