"""
The mapping module is responsible for mapping the normalized features to the physical parameters of the particle system. 
"""

import numpy as np

from src.config import load_config
from src.features import normalize_features, soften_features

VERTICAL_GAIN = 1.0
HORIZONTAL_GAIN = 1.0
SIGMA_MIN = 0.01
SIGMA_MAX = 0.1
FRICTION_MIN = 0.1
FRICTION_MAX = 0.9
ONSET_GAIN = 1.0
ONSET_THRESHOLD = 0.5

# preparing some features for mapping

def compute_energy_balance(low_energy, high_energy, eps=1e-8):
    """ Compute the balance between low and high energy features. 
    The result is a value in [-1, 1], where -1 means all low energy, 1 means all high energy, and 0 means balanced.
    """
    return (high_energy - low_energy) / (high_energy + low_energy + eps)


def compute_beat_impulses(beat_frames, n_frames):
    """ Compute a binary array of shape (n_frames,) where each beat frame is marked as 1 and the rest as 0. """
    impulses = np.zeros(n_frames)
    impulses[beat_frames] = 1
    return impulses


# physical parameters mapping:

def map_vertical_drift(spectral_centroid, vertical_gain=1.0):
    """ Map the spectral centroid to the vertical drift of the particles. 
    The spectral centroid is normalized to [0, 1] and then mapped to a vertical drift in [-1, 1].
    """
    mu_y = vertical_gain * (2 * spectral_centroid - 1)
    return mu_y


def map_horizontal_drift(low_energy, high_energy, horizontal_gain=1.0, eps=1e-8):
    """ Map the energy balance to the horizontal drift of the particles. 
    The energy balance is in [-1, 1] and then mapped to a horizontal drift in [-1, 1].
    """
    energy_balance = compute_energy_balance(low_energy, high_energy, eps)
    mu_x = horizontal_gain * energy_balance
    return mu_x


def map_noise_intensity(rms, sigma_min:float, sigma_max:float):
    """ Map the RMS energy to the noise intensity of the particles. 
    The RMS energy is normalized to [0, 1] and then mapped to a noise intensity in [sigma_min, sigma_max].
    """
    if sigma_min < 0 or sigma_max < sigma_min:
        raise ValueError(f"Expected 0 <= sigma_min <= sigma_max, got sigma_min={sigma_min} and sigma_max={sigma_max}")
    rms = np.asarray(rms, dtype=np.float)

    if not np.all(np.isfinite(rms)):
        raise ValueError(f"RMS values must be finite, got {rms}")

    rms = np.clip(rms, 0.0, 1.0)  # ensure rms is in [0, 1]
    sigma = sigma_min + (sigma_max - sigma_min) * rms
    return sigma


def map_friction(spectral_flatness, friction_min:float, friction_max:float):
    """ Map the spectral flatness to the friction of the particles. 
    The spectral flatness is normalized to [0, 1] and then mapped to a friction in [friction_min, friction_max].
    """
    if friction_min < 0 or friction_max < friction_min:
        raise ValueError(f"Expected 0 <= friction_min <= friction_max, got friction_min={friction_min} and friction_max={friction_max}")
    spectral_flatness = np.asarray(spectral_flatness, dtype=np.float)

    if not np.all(np.isfinite(spectral_flatness)):
        raise ValueError(f"Spectral flatness values must be finite, got {spectral_flatness}")

    spectral_flatness = np.clip(spectral_flatness, 0.0, 1.0)  # ensure spectral flatness is in [0, 1]
    friction = friction_min + (friction_max - friction_min) * spectral_flatness
    return friction


def map_onset_impulse(onset_strength, onset_gain=1.0, onset_threshold=0.5):
    """ Map the onset strength to a binary impulse signal. 
    The onset strength is normalized to [0, 1] and then mapped to a binary impulse signal where values above the threshold are 1 and below are 0.
    """
    onset_strength = np.asarray(onset_strength, dtype=np.float)

    if not np.all(np.isfinite(onset_strength)):
        raise ValueError(f"Onset strength values must be finite, got {onset_strength}")

    onset_strength = np.clip(onset_strength, 0.0, 1.0)  # ensure onset strength is in [0, 1]
    impulses = (onset_strength > onset_threshold).astype(np.float)
    return impulses * onset_gain


# uses the previous functions and combines them into a single dictionary
def map_features_to_physical_params(features, config=None):
    """ Map the normalized features to the physical parameters of the particle system. """
    config = config or load_config()
    normalized_features = normalize_features(features)
    softened_features = soften_features(normalized_features, config)

    physical_params = {
        "mu_x": map_horizontal_drift(softened_features["low_energy"], softened_features["high_energy"], horizontal_gain=HORIZONTAL_GAIN),
        "mu_y": map_vertical_drift(softened_features["spectral_centroid"], vertical_gain=VERTICAL_GAIN),
        "sigma": map_noise_intensity(softened_features["rms"], sigma_min=SIGMA_MIN, sigma_max=SIGMA_MAX),
        "friction": map_friction(softened_features["spectral_flatness"], friction_min=FRICTION_MIN, friction_max=FRICTION_MAX),
        "onset_impulse": map_onset_impulse(softened_features["onset_strength"], onset_gain=ONSET_GAIN, onset_threshold=ONSET_THRESHOLD)
        }
    return physical_params


# mapping features to color parameters


def map_color(features, saturation_min=0.4, saturation_max=1.0, value_min=0.3, value_max=1.0, eps=1e-8,):
    """Map chroma, RMS, and spectral centroid to HSV color parameters."""

    # verification of the limits of saturation and value:
    if not (0 <= saturation_min <= saturation_max <= 1):
        raise ValueError("Saturation limits must satisfy 0 <= min <= max <= 1.")
    if not (0 <= value_min <= value_max <= 1):
        raise ValueError("Value limits must satisfy 0 <= min <= max <= 1.")

    # Shape: (T, 12), one chroma value per pitch class and frame.
    chroma = np.column_stack([features[f"chroma_{i}"] for i in range(12)])

    rms = np.asarray(features["rms"], dtype=float)
    centroid = np.asarray(features["spectral_centroid"], dtype=float)

    if chroma.ndim != 2 or not (chroma.shape[0] == len(rms) == len(centroid)):
        raise ValueError("All features must have the same number of frames.")

    if not (np.all(np.isfinite(chroma)) and np.all(np.isfinite(rms)) and np.all(np.isfinite(centroid))):
        raise ValueError("Color features must contain only finite values.")

    chroma = np.clip(chroma, 0.0, 1.0)
    rms = np.clip(rms, 0.0, 1.0)
    centroid = np.clip(centroid, 0.0, 1.0)

    # Map the 12 pitch classes onto the hue circle.
    angles = 2 * np.pi * np.arange(12) / 12

    cos_component = chroma @ np.cos(angles)
    sin_component = chroma @ np.sin(angles)

    hue = (np.arctan2(sin_component, cos_component) / (2 * np.pi)) % 1.0

    # If the circular mean is ambiguous, use the dominant pitch class.
    resultant = np.hypot(cos_component, sin_component)
    ambiguous = resultant < eps

    dominant_note = np.argmax(chroma, axis=1)
    fallback_hue = dominant_note / 12.0

    hue = np.where(ambiguous, fallback_hue, hue)

    saturation = saturation_min + (saturation_max - saturation_min) * rms  # RMS controls color saturation.
    value = value_min + (value_max - value_min) * centroid  # Spectral centroid controls brightness.

    return {"hue": hue, "saturation": saturation, "value": value}


