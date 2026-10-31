import numpy as np


def step_simulation(
    positions: np.ndarray,
    velocities: np.ndarray,
    mu: np.ndarray | float = 0.0,
    sigma: float = 1.0,
    gamma: float = 1.0,
    dt: float = 1.0,
    width: float = 800.0,
    height: float = 600.0,
    rng: np.random.Generator | None = None,
    impulse: np.ndarray | float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Perform a single step of the simulation.

    Args:
        positions: Current positions of the particles (shape: [n_particles, 2]).
        velocities: Current velocities of the particles (shape: [n_particles, 2]).
        mu: Drift term (can be a scalar or an array of shape [n_particles, 2]).
        sigma: Noise intensity.
        gamma: Friction coefficient.
        dt: Time step.
        width: Width of the simulation area.
        height: Height of the simulation area.
        rng: Random number generator for reproducibility.
        impulse: Velocity added at this step (scalar, shape (2,) or [n_particles, 2]).

    Returns:
        Updated positions and velocities of the particles.
            v_next = (1 - gamma) * v + mu * dt + sigma * sqrt(dt) * noise + impulse
            x_next = x + v_next
    """
    positions = np.asarray(positions, dtype=float)
    velocities = np.asarray(velocities, dtype=float)

    if positions.ndim != 2 or positions.shape[1] != 2:
        raise ValueError("positions must have shape (N, 2).")
    if velocities.shape != positions.shape:
        raise ValueError("velocities must have the same shape as positions.")
    if not np.all(np.isfinite(positions)) or not np.all(np.isfinite(velocities)):
        raise ValueError("positions and velocities must be finite.")
    if not np.isfinite(sigma) or sigma < 0:
        raise ValueError("sigma must be finite and non-negative.")
    if not np.isfinite(gamma) or not 0 <= gamma <= 1:
        raise ValueError("gamma must be in [0, 1].")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive.")
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive.")

    mu = np.asarray(mu, dtype=float)
    if mu.shape not in ((), (2,)):
        raise ValueError("mu must be a scalar or a vector of shape (2,).")
    if not np.all(np.isfinite(mu)):
        raise ValueError("mu must contain only finite values.")

    impulse = np.asarray(impulse, dtype=float)
    if impulse.shape not in ((), (2,), positions.shape):
        raise ValueError("impulse must be a scalar, a vector of shape (2,) or have the shape of positions.")

    if rng is None:
        rng = np.random.default_rng()

    noise = rng.standard_normal(size=positions.shape)

    velocities = (1.0 - gamma) * velocities + mu * dt + sigma * np.sqrt(dt) * noise + impulse

    positions = positions + velocities

    # defining the toroidal domain: if a particle exits one side, it re-enters from the opposite side
    positions[:, 0] %= width
    positions[:, 1] %= height

    return positions, velocities


# Simulation conditioned by the music -------------------------------

def initial_cloud(n_particles, width, height, rng, spread=0.1):
    """Gaussian cloud at the centre of the domain"""
    return rng.normal([width / 2, height / 2], spread * height, size=(n_particles, 2)) % [width, height]


def dilation_impulse(positions, strength):
    """Impulse that swells (strength > 0) or shrinks (strength < 0) the cloud around the mean of the positions on screen.
    Proportional to the distance from the centre: particles at the median distance move by strength.
    """
    offset = positions - positions.mean(axis=0)
    typical_distance = np.median(np.linalg.norm(offset, axis=1))
    return strength * offset / max(typical_distance, 1e-9)


def simulate_frame(positions, velocities, params, frame, width, height, rng):
    """Advance one frame with that frame's parameters from mapping.py (mu_y > 0 is up)."""
    impulse = dilation_impulse(positions, params["onset_impulse"][frame])
    return step_simulation(positions, velocities, mu=np.array([params["mu_x"][frame], params["mu_y"][frame]]), sigma=params["sigma"][frame],
        gamma=params["friction"][frame], width=width, height=height, rng=rng, impulse=impulse)
