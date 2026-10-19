"""
Extract audio features, one value per video frame, with a .npz cache.

Usage (from the repository root):
    python -m src.features data/audio/songs/faixa.wav            # usa o cache se estiver atualizado
    python -m src.features data/audio/songs/faixa.wav --force    # recalcula e regrava o cache

From Python:
    from src.features import load_features
    features = load_features("data/audio/songs/faixa.wav")
    features["rms"]            # array of length T (frames)
    features["beat_frames"]    # frame indices of the detected beats
    features["tempo_bpm"]      # float

load_features returns the same dict as extract_features, but reads it from
data/cache/<track>.npz when available. The cache is recomputed whenever the
audio, the analysis parameters in config/default.yaml or this file change.

The .npz holds:
    features      T × K matrix (one row per video frame)
    columns       the K feature names, in column order
    beat_frames   frame indices of the beats
    tempo_bpm     estimated tempo
"""

import argparse
import hashlib
import os
from pathlib import Path
import librosa
import numpy as np

from src.config import load_config

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"

# Outputs of extract_features that are not one value per frame
NON_FRAME_KEYS = ("beat_frames", "tempo_bpm")


# Features extraction:

def extract_features(audio_path, config=None):
    config = config or load_config()
    y, sr = librosa.load(audio_path, sr=config.sample_rate, mono=True)

    hop_length = config.hop_length
    n_fft = config.n_fft

    # STFT: time-frequency representation of the audio
    D = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
    S = np.abs(D)

    features = {}

    # 1. Intensity
    features["rms"] = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop_length)[0]

    # 2. Frequency
    features["spectral_centroid"] = (librosa.feature.spectral_centroid(S=S, sr=sr)[0])

    # 3. Timbre
    features["spectral_bandwidth"] = (librosa.feature.spectral_bandwidth(S=S, sr=sr)[0])
    features["spectral_rolloff"] = (librosa.feature.spectral_rolloff(S=S, sr=sr)[0])
    features["spectral_flatness"] = (librosa.feature.spectral_flatness(S=S)[0])

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, n_fft=n_fft, hop_length=hop_length)

    for i in range(13):
        features[f"mfcc_{i + 1}"] = mfcc[i]

    # 4. Energy in three frequency bands
    frequencies = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    power = S**2

    bands = {
        "low_energy": frequencies < 250,
        "mid_energy": (frequencies >= 250) & (frequencies <= 4000),
        "high_energy": frequencies > 4000,
    }

    for name, mask in bands.items():
        features[name] = power[mask].sum(axis=0)

    # 5. Chroma: 12 pitch classes
    # A chroma is a 12-element representation of the energy distribution across the 12 pitch classes (semitones: C, C#, D, ..., B) of the musical octave
    chroma = librosa.feature.chroma_stft(S=S, sr=sr, n_fft=n_fft, hop_length=hop_length)

    for i in range(12):
        features[f"chroma_{i}"] = chroma[i]

    # 6. Rhythm
    onset_strength = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    features["onset_strength"] = onset_strength

    # 7. Beats and tempo
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_strength, sr=sr, hop_length=hop_length)

    features["beat_frames"] = beat_frames
    features["tempo_bpm"] = float(np.asarray(tempo).reshape(-1)[0])

    return features


def cache_path(audio_path, cache_dir=DEFAULT_CACHE_DIR):
    return Path(cache_dir) / f"{Path(audio_path).stem}.npz"


def load_features(audio_path, config=None, cache_dir=DEFAULT_CACHE_DIR, force=False):
    """Same output as extract_features, read from the .npz cache when it is up to date."""
    config = config or load_config()
    path = cache_path(audio_path, cache_dir)
    key = _cache_key(audio_path, config)

    if not force:
        cached = _read_cache(path, key)
        if cached is not None:
            return cached

    features = extract_features(audio_path, config)
    _write_cache(path, features, key)
    return features

# ------------------------------- Normalization and softening of the features -------------------------------

# Volume and energy are perceived on a log scale, so they are normalized in dB
DB_FEATURES = {"rms": 20, "low_energy": 10, "mid_energy": 10, "high_energy": 10}

# A 5–95% range smaller than this fraction of the feature's magnitude counts as constant.
# Without it, a steady tone would have its tiny fluctuations stretched over [0, 1].
MIN_RELATIVE_RANGE = 0.05

# Onsets are instants: smoothing would spread and delay each attack
NOT_SMOOTHED = ("onset_strength",)


# defining functions to normalize and soften the features

def normalize_features(extracted_features):
    """ Normalize each feature to the range [0, 1] using the 5th and 95th percentiles. """
    normalized_features = {}
    for name, values in extracted_features.items():
        # Chroma already comes in [0, 1] per frame, and the balance between the 12 notes is what defines the color
        if name in NON_FRAME_KEYS or name.startswith("chroma_"):
            normalized_features[name] = values
            continue

        if name in DB_FEATURES:
            values = DB_FEATURES[name] * np.log10(values + 1e-10) # normalize in dB, adding a small value to avoid log(0)

        p5, p95 = np.percentile(values, [5, 95])
        span = max(p95 - p5, MIN_RELATIVE_RANGE * max(abs(p5), abs(p95)))
        if span == 0:
            normalized_features[name] = np.zeros_like(values)
        else:
            normalized_features[name] = np.clip((values - p5) / span, 0, 1)
    return normalized_features


"""
The features extracted from the audio changes 30 times per second (fps). 
To avoid abrupt changes in the visualization, we apply a softening filter to the features.
"""

def soften_features(features, tau=0.5, config=None):
    """ Apply an exponential moving average to the features; tau (seconds) is how long it takes to follow a change. """
    config = config or load_config()
    alpha = 1 - np.exp(-1 / (config.fps * tau))  # weight of the new frame

    softened_features = {}
    for name, values in features.items():
        if name in NON_FRAME_KEYS or name in NOT_SMOOTHED:
            softened_features[name] = values
            continue
        softened_values = np.zeros_like(values)
        softened_values[0] = values[0]
        for i in range(1, len(values)):
            softened_values[i] = alpha * values[i] + (1 - alpha) * softened_values[i-1]
        softened_features[name] = softened_values
    return softened_features

# -----------------------------------------------------------------

def _cache_key(audio_path, config):
    # The cache is reused only while the audio, the analysis parameters and this file stay the same
    h = hashlib.sha256()
    h.update(Path(audio_path).read_bytes())
    h.update(f"{config.sample_rate}:{config.hop_length}:{config.n_fft}".encode())
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()


def _write_cache(path, features, key):
    # T × K matrix: one row per video frame, one column per feature
    columns = [name for name in features if name not in NON_FRAME_KEYS]
    matrix = np.stack([features[name] for name in columns], axis=1)

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.npz")
    np.savez(
        tmp,
        features=matrix,
        columns=np.array(columns),
        beat_frames=features["beat_frames"],
        tempo_bpm=features["tempo_bpm"],
        key=key,
    )
    # Rename only once the file is complete, so an interrupted run never leaves a broken cache
    os.replace(tmp, path)


def _read_cache(path, key):
    if not path.exists():
        return None
    with np.load(path) as data:
        if str(data["key"]) != key:
            return None
        matrix = data["features"]
        features = {str(name): matrix[:, i] for i, name in enumerate(data["columns"])}
        features["beat_frames"] = data["beat_frames"]
        features["tempo_bpm"] = float(data["tempo_bpm"])
    return features


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract the features of an audio file, using the .npz cache when possible.")
    parser.add_argument("audio_path")
    parser.add_argument("--force", action="store_true", help="recompute even if the cache is up to date")
    args = parser.parse_args()

    features = load_features(args.audio_path, force=args.force)
    n_columns = len(features) - len(NON_FRAME_KEYS)
    print(f"{len(features['rms'])} frames × {n_columns} features, tempo {features['tempo_bpm']:.1f} BPM")
    print(f"cache: {cache_path(args.audio_path)}")