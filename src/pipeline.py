"""
Full pipeline: audio -> features -> mapping -> simulation, shown in the pygame window or saved as an MP4.

Usage (from the repository root):
    python -m src.pipeline data/audio/songs/faixa.wav  # pre-view in a pygame window
    python -m src.pipeline data/audio/songs/faixa.wav --save_video    # save in data/videos/faixa.mp4

From Python:
    from src.pipeline import run_pipeline
    run_pipeline("data/audio/songs/faixa.wav")
    run_pipeline("data/audio/songs/faixa.wav", save_video=True)
"""
import argparse

import numpy as np

from src.conditional_visualization import play_simulation
from src.config import load_config
from src.features import load_features
from src.fokker_planck import entropy_over_time
from src.hyperparameters import resolve
from src.mapping import map_features_to_color_params, map_features_to_physical_params
from src.render import DEFAULT_VIDEO_DIR, export_video
from src.simulation import initial_cloud


def build_params(audio_path, config=None, hp=None):
    """Audio -> features -> mapping: the physical parameters and the colours of each frame, as (params, colors)."""
    config = config or load_config()
    hp = hp or resolve()
    features = load_features(audio_path, config)
    return map_features_to_physical_params(features, config, hp), map_features_to_color_params(features, config, hp)


def compute_entropy(params, config=None, hp=None):
    """Entropy (nats) of the cloud over time, from the Fokker–Planck equation (see fokker_planck.py).

    It starts from the same N particles as the exported video (same seed) and follows the same params.
    Returns an array of length n_frames + 1: entry i is the entropy at t = i / fps.
    """
    config = config or load_config()
    hp = hp or resolve()
    rng = np.random.default_rng(config.seed)
    positions = initial_cloud(config.n_particles_export, config.width, config.height, rng, hp.INITIAL_SPREAD)
    return entropy_over_time(positions, params, config)


def run_pipeline(audio_path, save_video=False, output_path=None, config=None, hp=None):
    """Run the simulation of audio_path: pygame preview by default, MP4 when save_video is True (returns its path).
    hp: hyperparameters from hyperparameters.resolve (default: the values of hyperparameters.py).
    """
    config = config or load_config()
    hp = hp or resolve()
    params, colors = build_params(audio_path, config, hp)

    if save_video:
        return export_video(audio_path, params, colors, output_path, config, hp=hp)
    return play_simulation(audio_path, params, colors, config, hp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract the features of an audio file and run the particle simulation.")
    parser.add_argument("audio_path")
    parser.add_argument("--save_video", action="store_true", help="save an MP4 instead of opening the preview window")
    parser.add_argument("-o", "--output", help=f"video path when saving (default: {DEFAULT_VIDEO_DIR.name}/<track>.mp4)")
    args = parser.parse_args()

    result = run_pipeline(args.audio_path, save_video=args.save_video, output_path=args.output)
    if args.save_video:
        print(f"video: {result}")
