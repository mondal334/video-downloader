import os
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from downloader_core import (
    fetch_video_info,
    download_video,
    detect_platform,
    DOWNLOADS_DIR,
    COOKIES_FILE,
)

logger = logging.getLogger("api")
app = FastAPI(title="Universal Video Downloader", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=4)

# In-memory storage of tasks
tasks: Dict[str, Dict[str, Any]] = {}


class DownloadRequest(BaseModel):
    url: str
    quality: str = "best_video"


@app.get("/api/info")
async def get_media_info(url: str = Query(..., description="Video URL to inspect")):
    """Fetches video information without downloading."""
    if not url.strip():
        raise HTTPException(status_code=400, detail="Please provide a valid URL")

    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(executor, fetch_video_info, url.strip())
        return {"success": True, "data": info}
    except Exception as e:
        logger.error(f"Error fetching info: {e}")
        raise HTTPException(status_code=400, detail=str(e))


def run_download_job(task_id: str, url: str, quality: str):
    """Background worker to run the download."""
    def progress_callback(data: Dict[str, Any]):
        if task_id in tasks:
            tasks[task_id].update(data)

    try:
        tasks[task_id]["status"] = "downloading"
        result = download_video(url, quality=quality, progress_callback=progress_callback)
        tasks[task_id].update({
            "status": "completed",
            "percent": 100.0,
            "filename": result["filename"],
            "filepath": result["filepath"],
            "filesize": result["filesize"],
            "title": result["title"],
        })
    except Exception as e:
        logger.error(f"Download failed for task {task_id}: {e}")
        tasks[task_id].update({
            "status": "error",
            "error": str(e),
        })


@app.post("/api/download")
async def start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    """Starts a background download task."""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "task_id": task_id,
        "url": url,
        "quality": req.quality,
        "status": "queued",
        "percent": 0.0,
        "speed": "0 KB/s",
        "eta": "--",
        "filename": "",
        "filepath": "",
        "filesize": 0,
        "error": None,
    }

    # Run in background
    background_tasks.add_task(run_download_job, task_id, url, req.quality)

    return {"success": True, "task_id": task_id}


@app.get("/api/progress/{task_id}")
async def get_task_progress(task_id: str):
    """Poll task progress."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]


@app.get("/api/progress/{task_id}/events")
async def stream_task_progress(task_id: str):
    """Server-Sent Events (SSE) stream of download progress."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        import json
        last_percent = -1
        while True:
            task = tasks.get(task_id)
            if not task:
                break
            
            # Send event update
            data_str = json.dumps(task)
            yield f"data: {data_str}\n\n"

            if task["status"] in ["completed", "error"]:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/file/{task_id}")
async def get_downloaded_file(task_id: str):
    """Serve the downloaded file directly to the browser."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Download is not completed yet")

    filepath = task.get("filepath")
    filename = task.get("filename")

    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Downloaded file could not be found on server")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/octet-stream",
    )


@app.get("/api/downloads")
async def list_recent_downloads():
    """Returns list of files currently in the downloads directory."""
    files = []
    if os.path.exists(DOWNLOADS_DIR):
        for f in sorted(os.listdir(DOWNLOADS_DIR), key=lambda x: os.path.getmtime(os.path.join(DOWNLOADS_DIR, x)), reverse=True):
            fpath = os.path.join(DOWNLOADS_DIR, f)
            if os.path.isfile(fpath):
                files.append({
                    "filename": f,
                    "size_mb": round(os.path.getsize(fpath) / (1024 * 1024), 2),
                    "created": os.path.getmtime(fpath),
                })
    return {"files": files}


@app.post("/api/cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """Upload a cookies.txt file to unlock private/restricted Instagram & Facebook posts."""
    content = await file.read()
    with open(COOKIES_FILE, "wb") as f:
        f.write(content)
    return {"success": True, "message": "cookies.txt updated successfully"}


# Mount static assets
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Web UI index.html not found.</h3>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
