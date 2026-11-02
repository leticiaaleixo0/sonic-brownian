"""
Preview with audio: the coloured particle cloud follows the features of the track while it plays.

Usage (from the repository root; the play button opens DEFAULT_AUDIO):
    python -m src.conditional_visualization data/audio/synthetic/03_sweep_100-4000hz.wav

Esc closes the window. The simulation advances with the audio position, not the screen clock.
"""
import argparse
from pathlib import Path

import numpy as np
import pygame

from src.color import oklch_to_srgb
from src.config import load_config
from src.features import load_features
from src.hyperparameters import HUE_SPREAD, TRAIL_DECAY
from src.mapping import map_features_to_color_params, map_features_to_physical_params
from src.simulation import initial_cloud, simulate_frame

DEFAULT_AUDIO = Path(__file__).resolve().parent.parent / "data" / "audio" / "songs" / "cornfield_chase_50s-80s.wav"
WINDOW_SCALE = 0.5 # simulation domain
POINT_SIZE = 2 # size in pixels
DRAW_FPS = 60 # screen refresh rate


def particle_colors(colors, frame, hue_offsets):
    """RGB (0–255) of each particle: the frame's OKLCH colour turned by the particle's hue offset."""
    offsets = np.arange(-HUE_SPREAD, HUE_SPREAD + 1)
    palette = oklch_to_srgb(colors["lightness"][frame], colors["chroma"][frame], colors["hue"][frame] + offsets)
    return 255 * palette[hue_offsets + HUE_SPREAD]


def draw_frame(trail, positions, rgb, width, height):
    """Fade the trail and draw the particles on it (y is flipped: up in the simulation, down on screen)."""
    trail *= TRAIL_DECAY
    w, h = trail.shape[:2]
    xs = (positions[:, 0] * w / width).astype(int)
    ys = ((height - positions[:, 1]) * h / height).astype(int)
    for dx in range(POINT_SIZE):
        for dy in range(POINT_SIZE):
            x, y = np.clip(xs + dx, 0, w - 1), np.clip(ys + dy, 0, h - 1)
            trail[x, y] = np.maximum(trail[x, y], rgb)


def run_preview(audio_path, config=None):
    """Play audio_path with the cloud following it. Returns the number of frames simulated."""
    config = config or load_config()
    features = load_features(audio_path, config)
    params = map_features_to_physical_params(features, config)
    colors = map_features_to_color_params(features, config)
    n_frames = len(params["sigma"])
    width, height = config.width, config.height
    rng = np.random.default_rng(config.seed)
    positions = initial_cloud(config.n_particles_preview, width, height, rng)
    velocities = np.zeros_like(positions)
    hue_offsets = np.random.default_rng(config.seed + 1).integers(-HUE_SPREAD, HUE_SPREAD + 1, len(positions))

    pygame.init()
    pygame.mixer.init(buffer=512)
    screen = pygame.display.set_mode((int(width * WINDOW_SCALE), int(height * WINDOW_SCALE)))
    pygame.display.set_caption(f"sonic-brownian · {Path(audio_path).name}")
    clock = pygame.time.Clock()
    trail = np.zeros((*screen.get_size(), 3), dtype=np.float32)
    pygame.mixer.music.load(str(audio_path))
    pygame.mixer.music.play()

    frame = 0
    running = True
    while running and pygame.mixer.music.get_busy():
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
        # Frame of what is being heard at the moment:
        audio_frame = min(int(pygame.mixer.music.get_pos() / 1000 * config.fps), n_frames)
        while frame < audio_frame:
            positions, velocities = simulate_frame(positions, velocities, params, frame, width, height, rng)
            draw_frame(trail, positions, particle_colors(colors, frame, hue_offsets), width, height)
            frame += 1
        # drawning the current state of the simulation:
        pygame.surfarray.blit_array(screen, trail.astype(np.uint8))
        pygame.display.flip()
        clock.tick(DRAW_FPS)
    pygame.mixer.music.stop()
    pygame.quit()
    return frame


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview the particle cloud driven by an audio file, with the audio playing.")
    parser.add_argument("audio_path", nargs="?", default=DEFAULT_AUDIO, help=f"WAV or MP3 file (default: {DEFAULT_AUDIO.name})")
    args = parser.parse_args()
    run_preview(args.audio_path)
