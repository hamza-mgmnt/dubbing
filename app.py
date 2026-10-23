import os
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import aiofiles

from voices import get_supported_languages
from dubbing_engine import DubbingEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("app")

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# Resilient static directory (works if 'static' folder exists or if files are in root)
if os.path.isdir(os.path.join(BASE_DIR, "static")):
    STATIC_DIR = os.path.join(BASE_DIR, "static")
else:
    STATIC_DIR = BASE_DIR

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(title="AI Multi-Speaker Video Dubbing Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory task progress tracker
# {task_id: {"status": "processing"|"completed"|"error", "percent": 0..100, "message": str, "result": dict, "error": str}}
tasks_state: Dict[str, Dict[str, Any]] = {}
task_subscribers: Dict[str, list] = {}

# Cached engine instances per model size
engine_cache: Dict[str, DubbingEngine] = {}

def get_engine(model_size: str = "base") -> DubbingEngine:
    if model_size not in engine_cache:
        engine_cache[model_size] = DubbingEngine(whisper_model_size=model_size)
    return engine_cache[model_size]


@app.get("/api/languages")
def api_languages():
    """Returns list of supported target languages."""
    return get_supported_languages()


@app.post("/api/dub")
async def start_dubbing(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    target_language: str = Form("hi"),
    whisper_model: str = Form("base"),
    audio_mode: str = Form("replace"),
    hf_token: Optional[str] = Form(None)
):
    """
    Initiates video dubbing task.
    Saves uploaded video and spawns background dubbing pipeline.
    """
    task_id = str(uuid.uuid4())
    input_filename = f"{task_id}_{video.filename}"
    input_path = os.path.join(UPLOAD_DIR, input_filename)
    output_filename = f"dubbed_{task_id}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # Save uploaded video
    async with aiofiles.open(input_path, "wb") as f:
        while chunk := await video.read(1024 * 1024):  # 1MB chunks
            await f.write(chunk)

    tasks_state[task_id] = {
        "status": "processing",
        "percent": 5,
        "message": "Video uploaded successfully. Starting pipeline...",
        "result": None,
        "error": None
    }

    # Run pipeline in background task
    background_tasks.add_task(
        run_dubbing_task,
        task_id,
        input_path,
        output_path,
        target_language,
        whisper_model,
        audio_mode,
        hf_token,
        output_filename
    )

    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Dubbing pipeline started."
    }


async def notify_task_update(task_id: str):
    """Notify all active SSE listeners for this task."""
    state = tasks_state.get(task_id)
    if not state or task_id not in task_subscribers:
        return
    for queue in task_subscribers[task_id]:
        await queue.put(state)


async def run_dubbing_task(
    task_id: str,
    input_path: str,
    output_path: str,
    target_language: str,
    whisper_model: str,
    audio_mode: str,
    hf_token: Optional[str],
    output_filename: str
):
    """Background worker executing the dubbing engine."""
    try:
        engine = get_engine(whisper_model)

        async def on_progress(percent: int, message: str, extra_data: Any = None):
            tasks_state[task_id]["percent"] = percent
            tasks_state[task_id]["message"] = message
            if extra_data:
                tasks_state[task_id]["extra"] = extra_data
            await notify_task_update(task_id)

        result = await engine.process_video(
            video_path=input_path,
            output_video_path=output_path,
            target_lang=target_language,
            hf_token=hf_token,
            audio_mode=audio_mode,
            progress_cb=on_progress
        )

        tasks_state[task_id]["status"] = "completed"
        tasks_state[task_id]["percent"] = 100
        tasks_state[task_id]["message"] = "Dubbing completed successfully!"
        tasks_state[task_id]["result"] = {
            "output_filename": output_filename,
            "duration": result["duration"],
            "segments": result["segments"]
        }
        await notify_task_update(task_id)

    except Exception as e:
        logger.exception(f"Error processing task {task_id}: {e}")
        tasks_state[task_id]["status"] = "error"
        tasks_state[task_id]["error"] = str(e)
        tasks_state[task_id]["message"] = f"Failed: {str(e)}"
        await notify_task_update(task_id)


@app.get("/api/status/{task_id}")
def get_task_status(task_id: str):
    """Polling endpoint to retrieve task status."""
    if task_id not in tasks_state:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_state[task_id]


@app.get("/api/events/{task_id}")
async def task_events(task_id: str):
    """Server-Sent Events (SSE) endpoint for real-time progress streaming."""
    if task_id not in tasks_state:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        queue = asyncio.Queue()
        if task_id not in task_subscribers:
            task_subscribers[task_id] = []
        task_subscribers[task_id].append(queue)

        try:
            # Send initial state immediately
            initial_data = tasks_state[task_id]
            import json
            yield f"data: {json.dumps(initial_data)}\n\n"

            while True:
                # Wait for update
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
                if data["status"] in ("completed", "error"):
                    break
        finally:
            if task_id in task_subscribers and queue in task_subscribers[task_id]:
                task_subscribers[task_id].remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/download/{filename}")
def download_video(filename: str):
    """Serves the generated video file as an attachment for download."""
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename, media_type="video/mp4")


# Mount generated outputs so the frontend <video> player can stream/preview them
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

# Mount static web frontend
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print(" 🚀 AI Video Dubbing Studio is starting...")
    print(" Open your browser and navigate to: http://localhost:8000")
    print("=" * 60 + "\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
