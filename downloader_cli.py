import sys
import argparse
from downloader_core import fetch_video_info, download_video, detect_platform

def cli_progress_hook(d):
    status = d.get("status")
    if status == "downloading":
        pct = d.get("percent", 0)
        speed = d.get("speed", "")
        eta = d.get("eta", "")
        sys.stdout.write(f"\r[Downloading] {pct}% | Speed: {speed} | ETA: {eta}  ")
        sys.stdout.flush()
    elif status == "processing":
        sys.stdout.write("\n[Processing] Merging/converting media...\n")
        sys.stdout.flush()
    elif status == "completed":
        sys.stdout.write(f"\n[Completed] File saved: {d.get('filename')}\n")
        sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(
        description="Universal Video Downloader (Instagram, Facebook, YouTube, etc.)"
    )
    parser.add_argument("url", help="URL of the video to download")
    parser.add_argument(
        "-q",
        "--quality",
        default="best_video",
        help="Quality option: 'best_video', '1080p', '720p', '480p', 'mp3', 'm4a' (Default: best_video)",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Only display media information without downloading",
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        help="Download audio only as MP3",
    )

    args = parser.parse_args()

    quality = "mp3" if args.audio else args.quality

    print("=" * 60)
    print("  Universal Video Downloader CLI")
    print(f"  Platform: {detect_platform(args.url)}")
    print("=" * 60)
    print(f"Fetching media details for: {args.url} ...")

    try:
        info = fetch_video_info(args.url)
        print(f"\nTitle    : {info['title']}")
        print(f"Platform : {info['platform']}")
        print(f"Creator  : {info['uploader']}")
        print(f"Duration : {info['duration']}")
        print("\nAvailable formats:")
        for q in info["qualities"]:
            print(f"  - {q['id']:<12} : {q['label']}")

        if args.info:
            return

        print(f"\nStarting download with quality: [{quality}] ...")
        result = download_video(args.url, quality=quality, progress_callback=cli_progress_hook)
        print("\n" + "=" * 60)
        print(f"SUCCESS!")
        print(f"File: {result['filepath']}")
        print(f"Size: {result['filesize'] / (1024 * 1024):.2f} MB")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
