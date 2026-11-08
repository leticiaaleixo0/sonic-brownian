from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

from src.api import services
from src.api.schemas import HealthResponse, HyperparameterSpec, Hyperparameters, VideoResponse, VideoStatusResponse

router = APIRouter(tags=["Sonic Brownian API"], prefix="/api")

MAX_PARTICLES = 200000


def _find_task(task_id):
    task = services.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"No task with id {task_id}.")
    return task


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check the health of the API.",
)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/hyperparameters",
    response_model=list[HyperparameterSpec],
    summary="List the hyperparameters a video request can change, with their defaults and limits.",
)
def list_hyperparameters() -> list[HyperparameterSpec]:
    properties = Hyperparameters.model_json_schema()["properties"]
    return [HyperparameterSpec(name=name, **{key: spec[key] for key in HyperparameterSpec.model_fields if key != "name"})
            for name, spec in properties.items()]


@router.post(
    "/videos",
    response_model=VideoResponse,
    status_code=202,
    summary="Upload an audio file and queue the rendering of its video.",
)
def request_video_rendering(
    audio: UploadFile = File(..., description="WAV or MP3 file"),
    n_particles: int | None = Form(None, gt=0, le=MAX_PARTICLES, description="default: n_particles_export of config/default.yaml"),
    hyperparameters: str | None = Form(None, description="JSON object with any of the fields of GET /api/hyperparameters; the rest keep their defaults"),
) -> VideoResponse:
    suffix = Path(audio.filename or "").suffix.lower()
    if suffix not in services.AUDIO_SUFFIXES:
        raise HTTPException(415, "Send a .wav or .mp3 file.")
    try:
        chosen = Hyperparameters.model_validate_json(hyperparameters or "{}")
    except ValidationError as error:
        raise HTTPException(422, error.errors(include_url=False, include_context=False)) from error
    task_id = services.submit(audio.file, suffix, n_particles, chosen.overrides())
    return VideoResponse(task_id=task_id, status="queued")


@router.get(
    "/videos/{task_id}",
    response_model=VideoStatusResponse,
    summary="Get the status of a video rendering task.",
)
def get_video_status(task_id: str) -> VideoStatusResponse:
    task = _find_task(task_id)
    video_url = f"{router.prefix}/videos/{task_id}/file" if task.status == "completed" else None
    return VideoStatusResponse(task_id=task_id, status=task.status, video_url=video_url, error=task.error)


@router.get(
    "/videos/{task_id}/file",
    response_class=FileResponse,
    summary="Download the video of a completed task.",
)
def download_video_file(task_id: str) -> FileResponse:
    task = _find_task(task_id)
    if task.status != "completed":
        raise HTTPException(409, f"The video is not ready (status: {task.status}).")
    return FileResponse(task.video_path, media_type="video/mp4", filename=f"{task_id}.mp4")