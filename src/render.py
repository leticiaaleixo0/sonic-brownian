"""
Save the simulation as an MP4 with the track's audio, drawn as in the pygame preview.

Usage (from the repository root):
    python -m src.render data/audio/songs/faixa.wav                  # saves in data/videos/faixa.mp4
    python -m src.render data/audio/songs/faixa.wav -o saida.mp4

The video is rendered offline, one frame per feature frame, so it stays in sync with the audio.
"""
import argparse
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from src.conditional_visualization import draw_frame, particle_colors
from src.config import load_config
from src.features import load_features
from src.hyperparameters import resolve
from src.mapping import map_features_to_color_params, map_features_to_physical_params
from src.simulation import initial_cloud, simulate_frame

DEFAULT_VIDEO_DIR = Path(__file__).resolve().parent.parent / "data" / "videos"
VIDEO_QUALITY = 6 # imageio-ffmpeg scale from 1 to 10


def video_size(width, height, video_height):
    """(width, height) of the video: the domain's aspect ratio at video_height, both even as H.264 requires."""
    video_height = 2 * round(video_height / 2)
    return 2 * round(width * video_height / height / 2), video_height


def export_video(audio_path, params, colors, output_path=None, config=None, n_particles=None, hp=None):
    """Render the cloud driven by params and colors (from mapping.py) to an MP4 with the audio of audio_path. Returns the video path."""
    config = config or load_config()
    hp = hp or resolve()
    output_path = Path(output_path or DEFAULT_VIDEO_DIR / f"{Path(audio_path).stem}.mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n_frames = len(params["sigma"])
    width, height = config.width, config.height
    rng = np.random.default_rng(config.seed)
    positions = initial_cloud(n_particles or config.n_particles_export, width, height, rng, hp.INITIAL_SPREAD)
    velocities = np.zeros_like(positions)
    hue_offsets = np.random.default_rng(config.seed + 1).integers(-hp.HUE_SPREAD, hp.HUE_SPREAD + 1, len(positions))

    size = video_size(width, height, hp.VIDEO_HEIGHTS[hp.RESOLUTION])
    trail = np.zeros((*size, 3), dtype=np.float32)
    writer = imageio_ffmpeg.write_frames(str(output_path), size, fps=config.fps, quality=VIDEO_QUALITY, macro_block_size=2, audio_path=str(audio_path), audio_codec="aac")
    writer.send(None)
    
    # writing frames:
    try:
        for frame in range(n_frames):
            positions, velocities = simulate_frame(positions, velocities, params, frame, width, height, rng)
            draw_frame(trail, positions, particle_colors(colors, frame, hue_offsets, hp.HUE_SPREAD), width, height, hp.TRAIL_DECAY)
            writer.send(np.ascontiguousarray(trail.astype(np.uint8).transpose(1, 0, 2)))
    finally:
        writer.close()
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save the particle cloud driven by an audio file as an MP4 with the audio.")
    parser.add_argument("audio_path")
    parser.add_argument("-o", "--output", help=f"video path (default: {DEFAULT_VIDEO_DIR.name}/<track>.mp4)")
    args = parser.parse_args()

    features = load_features(args.audio_path)
    path = export_video(args.audio_path, map_features_to_physical_params(features), map_features_to_color_params(features), args.output)
    print(f"video: {path}")
