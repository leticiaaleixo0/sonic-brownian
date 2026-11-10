"""
Fokker–Planck description of the cloud and its entropy over time.

The particles obey the discrete Langevin equation of simulation.py,
    v_next = (1 - gamma) v + mu dt + sigma sqrt(dt) xi + impulse,     x_next = x + v_next,
on a toroidal domain. Their density rho(x, t) obeys the corresponding Fokker–Planck equation, which is solved
here on a grid, with the same per-frame parameters (mu, sigma, gamma, onset impulse) that drive the video:

    d rho / dt = - mu_eff . grad rho + D lap rho,       mu_eff = mu / gamma,      D = sigma^2 / (2 gamma^2)

mu_eff and D are the overdamped (Smoluchowski) limit of the velocity equation: for a constant gamma, the sum of the
velocities of an AR(1) process has drift mu / gamma and diffusion sigma^2 / (2 gamma^2) per axis and per frame.
The approximation is good when the parameters change slowly compared with 1 / gamma frames.

Since mu_eff and D do not depend on the position and the domain is periodic, each frame is solved exactly in
Fourier space: every mode k is multiplied by exp(-i k.mu_eff - D |k|^2). No stability condition, no numerical diffusion.

The onset impulse is a dilation around the centre of the cloud (dilation_impulse in simulation.py). Its displacement
is the impulse divided by gamma (the velocity it adds decays by (1 - gamma) per frame), so each frame with an impulse
maps rho to its dilation by the factor 1 + impulse / (gamma * typical_distance), where typical_distance is the median
distance of the cloud to its centre. The negative pulse a few frames later undoes it, as in the particles.

The entropy is S(t) = - integral rho ln rho dA, in nats (rho in 1/px^2). It is at most ln(width * height), reached by
the uniform distribution on the domain.

Usage:
    positions = initial_cloud(config.n_particles_export, config.width, config.height, rng, hp.INITIAL_SPREAD)
    entropy = entropy_over_time(positions, params, config)      # shape (n_frames + 1,), entropy[0] at t = 0
"""
import numpy as np
from scipy.ndimage import map_coordinates

GRID_CELL = 4.0 # approximate side of a grid cell, in pixels (the initial cloud is ~50 px wide)
GAMMA_FLOOR = 0.01 # the overdamped limit does not exist for gamma = 0 (ballistic motion)
MIN_DILATION = 0.05 # a dilation factor below this would collapse the cloud to a point


class Grid:
    """Periodic grid over [0, width) x [0, height). Arrays have shape (nx, ny): the first axis is x."""

    def __init__(self, width, height, cell=GRID_CELL):
        self.width, self.height = float(width), float(height)
        self.nx, self.ny = max(int(round(width / cell)), 8), max(int(round(height / cell)), 8)
        self.dx, self.dy = self.width / self.nx, self.height / self.ny
        self.cell_area = self.dx * self.dy
        self.x = (np.arange(self.nx) + 0.5) * self.dx # cell centres
        self.y = (np.arange(self.ny) + 0.5) * self.dy
        self.kx = 2 * np.pi * np.fft.fftfreq(self.nx, d=self.dx) # rad/px; rfft over y, so ky has ny // 2 + 1 values
        self.ky = 2 * np.pi * np.fft.rfftfreq(self.ny, d=self.dy)
        # the Nyquist mode has no defined sign, so it does not take part in the drift (first derivative)
        self.kx_drift = self.kx.copy()
        if self.nx % 2 == 0:
            self.kx_drift[self.nx // 2] = 0.0
        self.ky_drift = self.ky.copy()
        if self.ny % 2 == 0:
            self.ky_drift[-1] = 0.0

    @property
    def max_entropy(self):
        """Entropy of the uniform distribution on the domain: ln(width * height)."""
        return float(np.log(self.width * self.height))


def normalize(rho, grid):
    """Remove the negative round-off and rescale so that the integral of rho is 1."""
    rho = np.clip(rho, 0.0, None)
    return rho / (rho.sum() * grid.cell_area)


def density_from_particles(positions, grid, bandwidth=None):
    """Initial density rho(x, 0) of the cloud: histogram of the particles on the grid, smoothed by a Gaussian kernel.

    bandwidth: kernel std in pixels, scalar or (hx, hy). Default: Scott's rule, std * N^(-1/6) on each axis.
    """
    positions = np.asarray(positions, dtype=float)
    counts, _, _ = np.histogram2d(positions[:, 0] % grid.width, positions[:, 1] % grid.height,
                                  bins=(grid.nx, grid.ny), range=((0, grid.width), (0, grid.height)))
    if bandwidth is None:
        bandwidth = positions.std(axis=0) * len(positions) ** (-1 / 6)
    hx, hy = np.broadcast_to(np.asarray(bandwidth, dtype=float), (2,))

    # Periodic Gaussian smoothing: a product in Fourier space
    counts_hat = np.fft.rfft2(counts)
    counts_hat *= np.exp(-0.5 * (hx * grid.kx) ** 2)[:, None] * np.exp(-0.5 * (hy * grid.ky) ** 2)[None, :]
    return normalize(np.fft.irfft2(counts_hat, s=(grid.nx, grid.ny)), grid)


def entropy(rho, grid):
    """Differential entropy S = - sum rho ln rho dA, in nats (0 ln 0 = 0)."""
    p = normalize(rho, grid)
    positive = p > 0
    return float(-np.sum(p[positive] * np.log(p[positive])) * grid.cell_area)


def drift_diffusion_step(rho, mu, diffusion, grid):
    """Exact solution, over one frame, of d rho / dt = - mu . grad rho + D lap rho on the torus.

    mu: (mu_x, mu_y) in px/frame. diffusion: D in px^2/frame, on each axis.
    """
    multiplier_x = np.exp(-1j * grid.kx_drift * mu[0] - diffusion * grid.kx ** 2)
    multiplier_y = np.exp(-1j * grid.ky_drift * mu[1] - diffusion * grid.ky ** 2)
    rho_hat = np.fft.rfft2(rho) * multiplier_x[:, None] * multiplier_y[None, :]
    return normalize(np.fft.irfft2(rho_hat, s=(grid.nx, grid.ny)), grid)


def _signed_offset(coordinate, centre, period):
    """Offset to the centre on the torus: the one of smallest magnitude, in [-period / 2, period / 2)."""
    return (coordinate - centre + period / 2) % period - period / 2


def cloud_centre(rho, grid):
    """Centre of the density on the torus: the circular mean on each axis."""
    centre = []
    for marginal, coordinate, period in ((rho.sum(axis=1), grid.x, grid.width), (rho.sum(axis=0), grid.y, grid.height)):
        angle = 2 * np.pi * coordinate / period
        mean_angle = np.arctan2(np.sum(marginal * np.sin(angle)), np.sum(marginal * np.cos(angle)))
        centre.append((mean_angle * period / (2 * np.pi)) % period)
    return np.array(centre)


def typical_distance(rho, grid, centre):
    """Median distance of the cloud to its centre (the typical_distance of dilation_impulse in simulation.py)."""
    distance = np.hypot(_signed_offset(grid.x, centre[0], grid.width)[:, None],
                        _signed_offset(grid.y, centre[1], grid.height)[None, :]).ravel()
    order = np.argsort(distance)
    cumulative = np.cumsum(rho.ravel()[order])
    return float(distance[order][np.searchsorted(cumulative, 0.5 * cumulative[-1])])


def dilate(rho, factor, grid, centre=None):
    """Density after the offsets to the centre are scaled by `factor` on the torus.

    rho'(x) = sum over the periodic images of x of rho(c + (x - c) / factor) / factor^2, where only the source points
    with offset inside [-period / 2, period / 2) count, so each particle is counted once and the mass is conserved:
    when shrinking, the points that would come from outside the domain are empty; when expanding, what leaves one side
    comes back from the other.
    """
    factor = max(float(factor), MIN_DILATION)
    if centre is None:
        centre = cloud_centre(rho, grid)
    offsets = (_signed_offset(grid.x, centre[0], grid.width), _signed_offset(grid.y, centre[1], grid.height))
    periods, steps = (grid.width, grid.height), (grid.dx, grid.dy)
    image_range = int(np.ceil((factor + 1) / 2)) # |offset + k * period| < factor * period / 2

    def sources(axis, k):
        """Cells of `axis` that receive mass from image k, and the (fractional) cell index they take it from."""
        source_offset = (offsets[axis] + k * periods[axis]) / factor
        cells = np.flatnonzero(np.abs(source_offset) < periods[axis] / 2)
        return cells, (centre[axis] + source_offset[cells]) / steps[axis] - 0.5

    result = np.zeros_like(rho)
    for kx in range(-image_range, image_range + 1):
        cells_x, index_x = sources(0, kx)
        if cells_x.size == 0:
            continue
        for ky in range(-image_range, image_range + 1):
            cells_y, index_y = sources(1, ky)
            if cells_y.size == 0:
                continue
            coordinates = np.stack(np.meshgrid(index_x, index_y, indexing="ij"))
            result[np.ix_(cells_x, cells_y)] += map_coordinates(rho, coordinates, order=3, mode="grid-wrap")
    return normalize(result / factor ** 2, grid)


def evolve_frame(rho, params, frame, grid):
    """Advance rho by one frame with the Langevin parameters of that frame (the counterpart of simulate_frame)."""
    gamma = max(float(params["friction"][frame]), GAMMA_FLOOR)
    impulse = float(params["onset_impulse"][frame])
    if impulse != 0.0:
        centre = cloud_centre(rho, grid)
        rho = dilate(rho, 1.0 + impulse / gamma / max(typical_distance(rho, grid, centre), 1e-9), grid, centre)

    mu = np.array([params["mu_x"][frame], params["mu_y"][frame]], dtype=float) / gamma
    diffusion = float(params["sigma"][frame]) ** 2 / (2 * gamma ** 2)
    return drift_diffusion_step(rho, mu, diffusion, grid)


def entropy_over_time(positions, params, config, cell=GRID_CELL):
    """Entropy (nats) of the density that starts as the cloud `positions` and follows the parameters of mapping.py.

    Returns an array of length n_frames + 1: entry i is the entropy at t = i / fps (entry 0 is the initial cloud).
    """
    grid = Grid(config.width, config.height, cell)
    rho = density_from_particles(positions, grid)
    n_frames = len(params["sigma"])

    result = np.empty(n_frames + 1)
    result[0] = entropy(rho, grid)
    for frame in range(n_frames):
        rho = evolve_frame(rho, params, frame, grid)
        result[frame + 1] = entropy(rho, grid)
    return result
