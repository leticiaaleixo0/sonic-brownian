"""
Marco 1 (Day 5): the synthetic control signals must move the cloud as expected.
    silence    -> the cloud stays still
    crescendo  -> the agitation grows progressively
    sweep      -> the cloud rises
    clicks     -> one pulse per click: the cloud swells without opening a hole, and does not spread out

Run from the repository root:
    pytest tests/
"""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.stats import spearmanr

from src.config import load_config
from src.features import load_features
from src.mapping import map_features_to_physical_params
from src.simulation import initial_cloud, simulate_frame

SYNTHETIC = Path(__file__).resolve().parent.parent / "data" / "audio" / "synthetic"
N_PARTICLES = 1000


def run_cloud(name):
    """Simulate a synthetic signal. Per frame: mean speed, vertical displacement (up > 0) and positions."""
    config = load_config()
    params = map_features_to_physical_params(load_features(SYNTHETIC / f"{name}.wav", config), config)
    rng = np.random.default_rng(config.seed)
    positions = initial_cloud(N_PARTICLES, config.width, config.height, rng)
    velocities = np.zeros_like(positions)

    n_frames = len(params["sigma"])
    speed, rise = np.empty(n_frames), np.empty(n_frames)
    history = np.empty((n_frames, N_PARTICLES, 2))
    displacement = 0.0  # summed velocities, which do not wrap around the torus
    for frame in range(n_frames):
        positions, velocities = simulate_frame(positions, velocities, params, frame, config.width, config.height, rng)
        displacement += velocities[:, 1].mean()
        speed[frame] = np.linalg.norm(velocities, axis=1).mean()
        rise[frame] = displacement
        history[frame] = positions

    return SimpleNamespace(speed=speed, rise=rise, positions=history, params=params, config=config)


def distance_to_centre(positions):
    """Distance of each particle to the cloud's mean position."""
    return np.linalg.norm(positions - positions.mean(axis=0), axis=1)


def test_silence_leaves_the_cloud_still():
    run = run_cloud("01_silence")

    assert run.speed.max() < 0.1
    assert abs(run.rise[-1]) < 1


def test_crescendo_agitates_the_cloud_progressively():
    run = run_cloud("06_crescendo_440hz")
    second = run.config.fps

    assert spearmanr(np.arange(len(run.speed)), run.speed).statistic > 0.9
    # Second-to-last second vs second one (skips the fades at the edges)
    assert run.speed[-2 * second:-second].mean() > 3 * run.speed[second:2 * second].mean()


def test_sweep_makes_the_cloud_rise():
    run = run_cloud("03_sweep_100-4000hz")
    second = run.config.fps

    assert run.rise[-1] > 0.2 * run.config.height
    # Higher every second than the second before
    assert np.all(np.diff(run.rise[::second]) > 0)


def test_clicks_give_one_pulse_each_and_keep_the_cloud_together():
    run = run_cloud("05_clicks_120bpm")
    attacks = np.flatnonzero(run.params["onset_impulse"] > 0)

    # One attack every 0.5 s (the click at t = 0 is not detected)
    assert len(attacks) >= 18
    assert np.all(np.abs(np.diff(attacks) - 0.5 * run.config.fps) <= 1)
    # The cloud ends about as compact as it started (std 0.1 · height)
    assert np.median(distance_to_centre(run.positions[-1])) < 0.2 * run.config.height


def test_attack_swells_the_cloud_without_opening_a_hole():
    run = run_cloud("05_clicks_120bpm")
    attacks = [a for a in np.flatnonzero(run.params["onset_impulse"] > 0) if a + 2 < len(run.positions)]

    def near_centre(positions):
        return np.sum(distance_to_centre(positions) < 60)

    # Share of the particles near the centre still there 2 frames after each attack (a hole gives ~0.15)
    kept = [near_centre(run.positions[a + 2]) / near_centre(run.positions[a - 1]) for a in attacks]
    assert min(kept) > 0.4
