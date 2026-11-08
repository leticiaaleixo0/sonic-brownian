"""
Run from the repository root:
    pytest tests/
"""
import numpy as np
import pytest

from src.simulation import step_simulation

N_PARTICLES = 5000
N_STEPS = 200


def run_pure_brownian(sigma, dt, rng):
    """Return the mean squared displacement after each step of a pure Brownian cloud."""
    positions = np.full((N_PARTICLES, 2), 100.0)
    velocities = np.zeros((N_PARTICLES, 2))
    displacement = np.zeros((N_PARTICLES, 2))

    msd = np.empty(N_STEPS)
    for i in range(N_STEPS):
        positions, velocities = step_simulation(positions, velocities, mu=0.0, sigma=sigma, gamma=1.0, dt=dt, rng=rng)
        displacement += velocities
        msd[i] = np.mean(np.sum(displacement**2, axis=1))
    return msd


# dt = 0.5 checks the sqrt(dt) scaling of the noise
@pytest.mark.parametrize("sigma, dt", [(1.0, 1.0), (2.0, 1.0), (2.0, 0.5)])
def test_mean_squared_displacement_grows_linearly_with_slope_2_sigma_squared(sigma, dt):
    msd = run_pure_brownian(sigma, dt, np.random.default_rng(0))
    t = np.arange(1, N_STEPS + 1) * dt

    slope, intercept = np.polyfit(t, msd, 1)

    assert slope == pytest.approx(2 * sigma**2, rel=0.05)
    assert abs(intercept) < 0.03 * msd[-1]


def test_particles_stay_inside_the_toroidal_domain():
    #A toroidal domain is a rectangle where particles that exit one side re-enter from the opposite side.
    rng = np.random.default_rng(0)
    width, height = 50.0, 30.0
    positions = rng.uniform([0, 0], [width, height], size=(N_PARTICLES, 2))
    velocities = np.zeros_like(positions)

    for _ in range(100):
        positions, velocities = step_simulation(positions, velocities, sigma=5.0, width=width, height=height, rng=rng)

    assert np.all(positions[:, 0] < width)
    assert np.all(positions[:, 1] < height)
