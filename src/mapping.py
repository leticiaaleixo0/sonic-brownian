"""
The mapping module is responsible for mapping the normalized features to the physical parameters of the particle system. 
"""

import numpy as np
from scipy.ndimage import median_filter

from src.config import load_config
from src.features import ema, normalize_features, soften_features

# Target quantities, in pixels per frame
VERTICAL_GAIN = 1.3 
HORIZONTAL_GAIN = 1.0  
SIGMA_MIN = 0.6 # random speed in the quietest part of the track (while there is sound)
SIGMA_MAX = 5.0 # random speed in the loudest part
FRICTION_MIN = 0.1  
FRICTION_MAX = 0.9  
ONSET_GAIN = 40.0 # distance (px) an attack moves the particles at the typical radius of the cloud
ONSET_THRESHOLD = 1.0  
PULSE_FRAMES = 4  # frames until the pulse is undone

# Absolute scales, the same for every track
PRESENCE_DB = (-60.0, -30.0)   
FLATNESS_DB = (-50.0, -5.0)    

# Drift follows how the sound changed relative to its recent past
DRIFT_TAU = 3.0 
OCTAVES_FOR_FULL_BIAS = 1.0   
SHARE_FOR_FULL_BIAS = 0.2

FAST_TAU = 0.1  
SLOW_TAU = 0.5 

# Colour, in OKLCH
HUE_OF_C = 239.0 # Castel: C blue; -30° per semitone gives G red and A violet
LIGHTNESS_RANGE = (0.55, 0.92) # lowest to highest centroid of the track
CHROMA_RANGE = (0.07, 0.20) # quietest to loudest part of the track (grey in silence)

# preparing some features for mapping

def compute_energy_balance(low_energy, high_energy, eps=1e-8, mid_energy=0.0):
    """Compute the normalized energy balance between low and high bands.
    Returns [-1, 1], where -1 indicates low-band dominance, 1 high-band dominance,
    and 0 a balanced signal. Including mid_energy reduces sensitivity to leakage
    when both low and high energies are small."""
    return (high_energy - low_energy) / (high_energy + low_energy + mid_energy + eps)


def compute_beat_impulses(beat_frames, n_frames):
    """ Compute a binary array of shape (n_frames,) where each beat frame is marked as 1 and the rest as 0. """
    impulses = np.zeros(n_frames)
    impulses[beat_frames] = 1
    return impulses


def compute_presence(rms, floor_db=PRESENCE_DB[0], full_db=PRESENCE_DB[1]):
    """ Loudness in [0, 1] on a fixed dB scale: 0 in silence, 1 for clearly audible sound. """
    rms_db = 20 * np.log10(np.asarray(rms, dtype=float) + 1e-10)
    return np.clip((rms_db - floor_db) / (full_db - floor_db), 0.0, 1.0)


def hold_through_silence(values, presence):
    """ Replace silent frames with the last value heard. """
    values = np.asarray(values, dtype=float)
    sounding = presence > 0.5
    if not sounding.any():
        return np.zeros_like(values)

    last_sounding = np.maximum.accumulate(np.where(sounding, np.arange(len(values)), 0))
    held = values[last_sounding]
    first = np.argmax(sounding)
    held[:first] = values[first]
    return held


def compute_bias(values, units_for_full_bias, config, tau=DRIFT_TAU):
    """ Bias in [-1, 1]: distance of the feature from its average over the last tau seconds (positive while rising). """
    trend = values - ema(values, tau, config)
    return np.clip(trend / units_for_full_bias, -1.0, 1.0)


# physical parameters mapping 
def map_vertical_drift(vertical_bias, presence, vertical_gain=VERTICAL_GAIN):
    """ Vertical drift velocity: sounds getting higher make the cloud rise. """
    return vertical_gain * vertical_bias * presence


def map_horizontal_drift(horizontal_bias, presence, horizontal_gain=HORIZONTAL_GAIN):
    """ Horizontal drift velocity: more treble than bass pushes right, more bass pushes left. """
    return horizontal_gain * horizontal_bias * presence


def map_noise_intensity(rms, presence, sigma_min=SIGMA_MIN, sigma_max=SIGMA_MAX):
    """ Random velocity of each particle from the normalized RMS, switched off in silence. """
    if sigma_min < 0 or sigma_max < sigma_min:
        raise ValueError(f"Expected 0 <= sigma_min <= sigma_max, got sigma_min={sigma_min} and sigma_max={sigma_max}")
    rms = np.asarray(rms, dtype=float)

    if not np.all(np.isfinite(rms)):
        raise ValueError(f"RMS values must be finite, got {rms}")

    rms = np.clip(rms, 0.0, 1.0)  # ensure rms is in [0, 1]
    return presence * (sigma_min + (sigma_max - sigma_min) * rms)


def map_friction(spectral_flatness, friction_min=FRICTION_MIN, friction_max=FRICTION_MAX):
    """ Friction from the raw spectral flatness in dB: tonal -> low friction (fluid), noisy -> high friction (erratic). """
    if friction_min < 0 or friction_max < friction_min or friction_max > 1:
        raise ValueError(f"Expected 0 <= friction_min <= friction_max <= 1, got friction_min={friction_min} and friction_max={friction_max}")
    spectral_flatness = np.asarray(spectral_flatness, dtype=float)

    if not np.all(np.isfinite(spectral_flatness)):
        raise ValueError(f"Spectral flatness values must be finite, got {spectral_flatness}")

    flatness_db = 10 * np.log10(spectral_flatness + 1e-10)
    noisiness = np.clip((flatness_db - FLATNESS_DB[0]) / (FLATNESS_DB[1] - FLATNESS_DB[0]), 0.0, 1.0)
    return friction_min + (friction_max - friction_min) * noisiness


def map_onset_impulse(onset_strength, window, onset_gain=ONSET_GAIN, onset_threshold=ONSET_THRESHOLD, pulse_frames=PULSE_FRAMES):
    """ Pulse at each attack: +onset_gain at the attack frame and -onset_gain pulse_frames later.
    An attack is a local peak of the raw onset strength at least onset_threshold above the window's median.
    """
    onset_strength = np.asarray(onset_strength, dtype=float)

    if not np.all(np.isfinite(onset_strength)):
        raise ValueError(f"Onset strength values must be finite, got {onset_strength}")

    previous = np.concatenate(([0.0], onset_strength[:-1]))
    following = np.concatenate((onset_strength[1:], [0.0]))
    is_peak = (onset_strength > previous) & (onset_strength >= following)
    background = median_filter(onset_strength, size=window, mode="nearest")
    attacks = (is_peak & (onset_strength - background > onset_threshold)) * onset_gain

    pulse = attacks.copy()
    pulse[pulse_frames:] -= attacks[:-pulse_frames]
    return pulse


# uses the previous functions and combines them into a single dictionary
def map_features_to_physical_params(features, config=None):
    """ Map the raw features (as returned by load_features) to the Langevin parameters of each frame.

    Returns arrays of length T: mu_x, mu_y (positive is up), sigma, friction and onset_impulse.
    """
    config = config or load_config()
    normalized_features = normalize_features(features)

    presence = ema(compute_presence(features["rms"]), FAST_TAU, config)

    # Centroid in octaves
    octaves = np.log2(np.maximum(features["spectral_centroid"], 20.0))
    octaves = ema(hold_through_silence(octaves, presence), SLOW_TAU, config)
    vertical_bias = compute_bias(octaves, OCTAVES_FOR_FULL_BIAS, config)

    balance = compute_energy_balance(features["low_energy"], features["high_energy"], mid_energy=features["mid_energy"])
    balance = ema(hold_through_silence(balance, presence), SLOW_TAU, config)
    horizontal_bias = compute_bias(balance, SHARE_FOR_FULL_BIAS, config)

    drift_x = map_horizontal_drift(horizontal_bias, presence)
    drift_y = map_vertical_drift(vertical_bias, presence)
    agitation = map_noise_intensity(ema(normalized_features["rms"], FAST_TAU, config), presence)
    gamma = map_friction(ema(features["spectral_flatness"], SLOW_TAU, config))
    impulse = map_onset_impulse(features["onset_strength"], window=config.fps + 1)

    # Scale by gamma so that the friction changes the texture, not the speed (gamma = 1 changes nothing)
    physical_params = {
        "mu_x": gamma * drift_x,
        "mu_y": gamma * drift_y,
        "sigma": np.sqrt(gamma * (2 - gamma)) * agitation,
        "friction": gamma,
        "onset_impulse": gamma * impulse,
        }
    return physical_params


# mapping features to color parameters (OKLCH)

def pitch_class_hues(hue_of_c=HUE_OF_C):
    """ OKLCH hue (degrees) of each pitch class C, C#, ..., B, in Castel's order. """
    return (hue_of_c - 30.0 * np.arange(12)) % 360


def map_color(features, presence=1.0, lightness_range=LIGHTNESS_RANGE, chroma_range=CHROMA_RANGE, eps=1e-8):
    """ OKLCH colour per frame from normalized features: hue from the chroma, lightness from the centroid, chroma from the RMS. """
    if not (0 <= lightness_range[0] <= lightness_range[1] <= 1):
        raise ValueError("Lightness limits must satisfy 0 <= min <= max <= 1.")
    if not (0 <= chroma_range[0] <= chroma_range[1]):
        raise ValueError("Chroma limits must satisfy 0 <= min <= max.")

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

    # Circular mean of the pitch-class hues, weighted by the chroma
    angles = np.deg2rad(pitch_class_hues())

    cos_component = chroma @ np.cos(angles)
    sin_component = chroma @ np.sin(angles)

    hue = np.rad2deg(np.arctan2(sin_component, cos_component)) % 360

    # If the circular mean is ambiguous, use the dominant pitch class.
    resultant = np.hypot(cos_component, sin_component)
    ambiguous = resultant < eps

    dominant_note = np.argmax(chroma, axis=1)
    hue = np.where(ambiguous, pitch_class_hues()[dominant_note], hue)

    lightness = lightness_range[0] + (lightness_range[1] - lightness_range[0]) * centroid  # bright sounds, light colours
    color_chroma = presence * (chroma_range[0] + (chroma_range[1] - chroma_range[0]) * rms)  # loud sounds, vivid colours

    return {"lightness": lightness, "chroma": color_chroma, "hue": hue}


def map_features_to_color_params(features, config=None):
    """ Map the raw features (as returned by load_features) to the OKLCH colour of each frame. """
    config = config or load_config()
    octaves = np.log2(np.maximum(features["spectral_centroid"], 20.0))
    normalized = normalize_features({"rms": features["rms"], "spectral_centroid": octaves})

    smoothed = {name: ema(values, SLOW_TAU, config) for name, values in normalized.items()}
    smoothed.update({f"chroma_{i}": ema(features[f"chroma_{i}"], SLOW_TAU, config) for i in range(12)})
    presence = ema(compute_presence(features["rms"]), SLOW_TAU, config)
    return map_color(smoothed, presence)
