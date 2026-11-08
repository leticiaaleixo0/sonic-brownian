"""
Rendering tasks of the API: each uploaded audio becomes a task that renders its MP4 in the background.

Tasks live in memory: they are lost when the server restarts.
The audio is saved in data/uploads/<task_id>.<ext> and the video in data/videos/<task_id>.mp4.
"""
import queue
import shutil
import threading
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

from src.config import load_config
from src.hyperparameters import resolve
from src.pipeline import run_pipeline
from src.render import DEFAULT_VIDEO_DIR

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"
AUDIO_SUFFIXES = (".wav", ".mp3")


@dataclass
class Task:
    status: str = "queued"
    video_path: Path | None = None
    error: str | None = None


_tasks: dict[str, Task] = {}
_queue: queue.Queue = queue.Queue()


def submit(audio_file, suffix, n_particles=None, hyperparameters=None):
    """Save the uploaded audio under a new task id and queue the rendering of its video. Returns the task id.
    hyperparameters: overrides keyed by the constant names of hyperparameters.py.
    """
    task_id = uuid.uuid4().hex # unique id for the task
    audio_path = UPLOAD_DIR / f"{task_id}{suffix}"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio_file, f)

    _tasks[task_id] = Task()
    _queue.put((task_id, audio_path, n_particles, hyperparameters))
    return task_id


def get_task(task_id):
    """The task with this id, or None."""
    return _tasks.get(task_id)


def _render(task_id, audio_path, n_particles, hyperparameters):
    task = _tasks[task_id]
    task.status = "running"
    try:
        config = load_config()
        if n_particles is not None:
            config = replace(config, n_particles_export=n_particles)
        task.video_path = run_pipeline(audio_path, save_video=True, output_path=DEFAULT_VIDEO_DIR / f"{task_id}.mp4", config=config, hp=resolve(hyperparameters))
        task.status = "completed"
    except Exception as error:
        task.error = f"{type(error).__name__}: {error}"
        task.status = "failed"


def _worker():
    while True:
        _render(*_queue.get())


# One render at a time, since each already uses several cores
threading.Thread(target=_worker, daemon=True).start()
