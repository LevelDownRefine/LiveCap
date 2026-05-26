"""FastAPI server for video editing."""

import os
import uuid
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from editor.ffmpeg_ops import probe, trim, concat

app = FastAPI(title="LiveCap Video Editor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


class Segment(BaseModel):
    start: float
    end: float


class EditRequest(BaseModel):
    video_id: str
    segments: list[Segment]


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    video_id = str(uuid.uuid4())
    ext = Path(file.filename or "video.mp4").suffix.lower()
    allowed_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    if ext not in allowed_exts:
        raise HTTPException(400, f"Unsupported format: {ext}")
    dest = UPLOAD_DIR / f"{video_id}{ext}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    info = probe(str(dest))
    return {
        "video_id": video_id,
        "filename": file.filename,
        "duration": info.duration,
        "width": info.width,
        "height": info.height,
        "fps": info.fps,
    }


@app.get("/api/video/{video_id}/info")
def video_info(video_id: str):
    path = _find_video(video_id)
    info = probe(str(path))
    return {
        "video_id": video_id,
        "duration": info.duration,
        "width": info.width,
        "height": info.height,
        "fps": info.fps,
    }


@app.get("/api/video/{video_id}/stream")
def stream_video(video_id: str):
    path = _find_video(video_id)
    return FileResponse(path, media_type="video/mp4")


@app.post("/api/edit")
def edit_video(req: EditRequest):
    src = _find_video(req.video_id)
    if not req.segments:
        raise HTTPException(400, "No segments provided")

    output_id = str(uuid.uuid4())
    if len(req.segments) == 1:
        seg = req.segments[0]
        out_path = OUTPUT_DIR / f"{output_id}.mp4"
        trim(str(src), seg.start, seg.end, str(out_path))
    else:
        temp_segs: list[str] = []
        for i, seg in enumerate(req.segments):
            tmp = OUTPUT_DIR / f"{output_id}_seg{i}.mp4"
            trim(str(src), seg.start, seg.end, str(tmp))
            temp_segs.append(str(tmp))
        out_path = OUTPUT_DIR / f"{output_id}.mp4"
        concat(temp_segs, str(out_path))
        for tmp in temp_segs:
            os.unlink(tmp)

    return {
        "output_id": output_id,
        "download_url": f"/api/download/{output_id}",
    }


@app.get("/api/download/{output_id}")
def download_output(output_id: str):
    _validate_id(output_id)
    path = (OUTPUT_DIR / f"{output_id}.mp4").resolve()
    if not str(path).startswith(str(OUTPUT_DIR.resolve())):
        raise HTTPException(400, "Invalid path")
    if not path.exists():
        raise HTTPException(404, "Output not found")
    return FileResponse(path, media_type="video/mp4", filename="edited.mp4")


def _validate_id(resource_id: str) -> str:
    """Ensure the ID is a valid UUID to prevent path traversal."""
    import re
    if not re.match(r'^[a-f0-9\-]{36}$', resource_id):
        raise HTTPException(400, "Invalid ID format")
    return resource_id


def _find_video(video_id: str) -> Path:
    _validate_id(video_id)
    for f in UPLOAD_DIR.iterdir():
        if f.stem == video_id:
            resolved = f.resolve()
            if not str(resolved).startswith(str(UPLOAD_DIR.resolve())):
                raise HTTPException(400, "Invalid path")
            return resolved
    raise HTTPException(404, "Video not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
