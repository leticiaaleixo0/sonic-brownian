"""
Rendering tasks of the API: each uploaded audio becomes a task that renders its MP4 in the background.

Tasks live in memory: they are lost when the server restarts.
The audio is saved in data/uploads/<task_id>.<ext> and the video in data/videos/<task_id>.mp4.
"""
import logging
import queue
import shutil
import threading
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

from src.config import load_config
from src.fokker_planck import Grid
from src.hyperparameters import resolve
from src.pipeline import build_params, compute_entropy
from src.render import DEFAULT_VIDEO_DIR, export_video
from src.render_combined import export_side_by_side

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"
AUDIO_SUFFIXES = (".wav", ".mp3")


@dataclass
class Task:
    status: str = "queued"
    video_path: Path | None = None
    error: str | None = None
    entropy: dict | None = None # {"fps", "time", "entropy", "max_entropy"}; None if it could not be computed
    combined_status: str = "pending" # side-by-side video (particles + entropy): pending | running | ready | failed | unavailable
    combined_path: Path | None = None


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


def _entropy_series(params, config, hp):
    """Entropy of the cloud over time, ready for the JSON response. A failure here must not lose the video."""
    try:
        entropy = compute_entropy(params, config, hp)
    except Exception:
        logger.exception("Could not compute the entropy")
        return None
    grid = Grid(config.width, config.height)
    return {
        "fps": config.fps,
        "time": [round(i / config.fps, 4) for i in range(len(entropy))],
        "entropy": [round(float(value), 5) for value in entropy],
        "max_entropy": round(grid.max_entropy, 5),
    }


def _render(task_id, audio_path, n_particles, hyperparameters):
    task = _tasks[task_id]
    task.status = "running"
    try:
        config = load_config()
        if n_particles is not None:
            config = replace(config, n_particles_export=n_particles)
        hp = resolve(hyperparameters)
        params, colors = build_params(audio_path, config, hp)
        task.video_path = export_video(audio_path, params, colors, DEFAULT_VIDEO_DIR / f"{task_id}.mp4", config, hp=hp)
        task.entropy = _entropy_series(params, config, hp)
        task.status = "completed" # the video and the chart are already usable; the combined video follows
    except Exception as error:
        task.error = f"{type(error).__name__}: {error}"
        task.status = "failed"
        return
    _render_combined(task, task_id)


def _render_combined(task, task_id):
    """Side-by-side video (particles | entropy). A failure here must not lose the video that is already completed."""
    if task.entropy is None:
        task.combined_status = "unavailable"
        return
    task.combined_status = "running"
    try:
        task.combined_path = export_side_by_side(task.video_path, task.entropy, DEFAULT_VIDEO_DIR / f"{task_id}_entropy.mp4")
        task.combined_status = "ready"
    except Exception:
        logger.exception("Could not render the side-by-side video")
        task.combined_status = "failed"


def _worker():
    while True:
        _render(*_queue.get())


# One render at a time, since each already uses several cores
threading.Thread(target=_worker, daemon=True).start()
