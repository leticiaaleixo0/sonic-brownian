from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

TaskStatus = Literal["queued", "running", "completed", "failed"]


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])


class VideoResponse(BaseModel):
    task_id: str
    status: TaskStatus


class VideoStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    video_url: str | None = None
    error: str | None = None
