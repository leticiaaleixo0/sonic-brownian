"""
Run from the repository root:
    pytest tests/test_fokker_planck.py
"""
from types import SimpleNamespace

import numpy as np
import pytest

from src.fokker_planck import (Grid, density_from_particles, dilate, drift_diffusion_step, entropy, entropy_over_time,
                               evolve_frame)
from src.simulation import initial_cloud, step_simulation

WIDTH, HEIGHT = 854, 480
CONFIG = SimpleNamespace(width=WIDTH, height=HEIGHT)


def constant_params(n_frames, gamma, sigma, mu=(0.0, 0.0), impulse=None):
    return {
        "mu_x": np.full(n_frames, gamma * mu[0]), "mu_y": np.full(n_frames, gamma * mu[1]),
        "sigma": np.full(n_frames, sigma), "friction": np.full(n_frames, gamma),
        "onset_impulse": np.zeros(n_frames) if impulse is None else impulse,
    }


@pytest.fixture(scope="module")
def grid():
    return Grid(WIDTH, HEIGHT)


@pytest.fixture(scope="module")
def cloud_density(grid):
    positions = initial_cloud(20000, WIDTH, HEIGHT, np.random.default_rng(0), spread=0.1)
    return density_from_particles(positions, grid)


def test_initial_entropy_matches_the_gaussian_formula(grid, cloud_density):
    std = 0.1 * HEIGHT
    assert cloud_density.sum() * grid.cell_area == pytest.approx(1.0)
    assert entropy(cloud_density, grid) == pytest.approx(np.log(2 * np.pi * np.e * std**2), abs=0.06) # + the smoothing of the kernel


def test_pure_diffusion_follows_the_gaussian_entropy(grid, cloud_density):
    # variance grows by 2 D per frame on each axis, as long as the cloud does not feel the borders
    diffusion, frames, std = 20.0, 10, 0.1 * HEIGHT
    rho = cloud_density
    for _ in range(frames):
        rho = drift_diffusion_step(rho, (0.0, 0.0), diffusion, grid)
    expected = np.log(2 * np.pi * np.e * (std**2 + 2 * diffusion * frames))
    assert entropy(rho, grid) == pytest.approx(expected, abs=0.06) # + the smoothing of the initial kernel


def test_drift_moves_the_cloud_without_changing_the_entropy(grid, cloud_density):
    rho = drift_diffusion_step(cloud_density, (10.0, -4.0), 0.0, grid)
    assert entropy(rho, grid) == pytest.approx(entropy(cloud_density, grid), abs=1e-6)


def test_long_diffusion_tends_to_the_uniform_distribution(grid, cloud_density):
    rho = cloud_density
    for _ in range(200):
        rho = drift_diffusion_step(rho, (0.0, 0.0), 500.0, grid)
    assert entropy(rho, grid) == pytest.approx(grid.max_entropy, abs=1e-3)


@pytest.mark.parametrize("factor", [0.6, 1.5])
def test_dilation_changes_the_entropy_by_two_log_factor(grid, cloud_density, factor):
    rho = dilate(cloud_density, factor, grid)
    assert rho.sum() * grid.cell_area == pytest.approx(1.0)
    assert entropy(rho, grid) == pytest.approx(entropy(cloud_density, grid) + 2 * np.log(factor), abs=0.03)


def test_onset_pulse_swells_the_cloud_and_is_undone(grid, cloud_density):
    gamma, strength, frames = 0.5, 40.0, 10
    impulse = np.zeros(frames)
    impulse[2], impulse[6] = gamma * strength, -gamma * strength
    params = constant_params(frames, gamma, sigma=0.5, impulse=impulse)

    rho, history = cloud_density, [entropy(cloud_density, grid)]
    for frame in range(frames):
        rho = evolve_frame(rho, params, frame, grid)
        history.append(entropy(rho, grid))

    assert history[3] > history[2] + 0.5 # swollen
    assert history[-1] == pytest.approx(history[2], abs=0.15) # undone (the diffusion in between adds a little)


@pytest.mark.parametrize("gamma, sigma, mu", [(0.9, 3.0, (0.5, 0.0)), (0.5, 3.0, (0.5, 0.2))])
def test_matches_the_langevin_particles(grid, gamma, sigma, mu):
    """The ensemble of Langevin particles samples the density of the Fokker–Planck equation."""
    n_particles, n_frames = 200000, 40
    rng = np.random.default_rng(2) # not the seed of the initial cloud, or the noise would repeat its numbers
    positions = initial_cloud(n_particles, WIDTH, HEIGHT, np.random.default_rng(1), spread=0.1)
    rho = density_from_particles(positions, grid)
    velocities = np.zeros_like(positions)
    params = constant_params(n_frames, gamma, sigma, mu)

    half_cell = 0.5 * np.array([grid.dx, grid.dy])
    for frame in range(n_frames):
        positions, velocities = step_simulation(positions, velocities, mu=gamma * np.array(mu), sigma=sigma, gamma=gamma,
                                                width=WIDTH, height=HEIGHT, rng=rng)
        rho = evolve_frame(rho, params, frame, grid)

    particles_entropy = entropy(density_from_particles(positions, grid, bandwidth=half_cell), grid)
    assert entropy(rho, grid) == pytest.approx(particles_entropy, abs=0.06)


def test_entropy_over_time_has_one_value_per_frame_plus_the_initial_one():
    n_frames = 30
    positions = initial_cloud(2000, WIDTH, HEIGHT, np.random.default_rng(0), spread=0.1)
    result = entropy_over_time(positions, constant_params(n_frames, gamma=0.5, sigma=2.0), CONFIG)
    assert result.shape == (n_frames + 1,)
    assert np.all(np.diff(result) > 0) # pure diffusion only increases the entropy
