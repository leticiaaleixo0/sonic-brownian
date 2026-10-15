"""
Load the project's global parameters from config/default.yaml.

Usage:
    from src.config import load_config
    cfg = load_config()
    y, sr = librosa.load(path, sr=cfg.sample_rate)
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"


@dataclass(frozen=True)
class Config:
    sample_rate: int
    hop_length: int
    n_fft: int
    fps: int
    width: int
    height: int
    n_particles_preview: int
    n_particles_export: int
    seed: int

    def __post_init__(self):
        # Sem isso, features e quadros de vídeo deslizam uns em relação aos outros.
        if self.hop_length * self.fps != self.sample_rate:
            raise ValueError(
                f"hop_length × fps must equal sample_rate: "
                f"{self.hop_length} × {self.fps} != {self.sample_rate}"
            )


def load_config(path=DEFAULT_PATH):
    """Read a YAML file and return it as a validated Config."""
    with open(path) as f:
        return Config(**yaml.safe_load(f))
