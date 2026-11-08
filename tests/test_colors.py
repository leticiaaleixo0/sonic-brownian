"""
Day 6: OKLCH colour of the particles, from the chroma, the centroid and the RMS.

Run from the repository root:
    pytest tests/
"""
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from src.color import oklch_to_srgb
from src.features import load_features
from src.mapping import map_features_to_color_params, pitch_class_hues

SYNTHETIC = Path(__file__).resolve().parent.parent / "data" / "audio" / "synthetic"


def colors_of(name):
    return map_features_to_color_params(load_features(SYNTHETIC / f"{name}.wav"))


def test_oklch_matches_reference_srgb_colours():
    np.testing.assert_allclose(oklch_to_srgb(1.0, 0.0, 0.0), [1, 1, 1], atol=1e-4)
    np.testing.assert_allclose(oklch_to_srgb(0.0, 0.0, 0.0), [0, 0, 0], atol=1e-4)
    np.testing.assert_allclose(oklch_to_srgb(0.627955, 0.257683, 29.2339), [1, 0, 0], atol=1e-3)  # sRGB red
    np.testing.assert_allclose(oklch_to_srgb(0.452014, 0.313214, 264.052), [0, 0, 1], atol=1e-3)  # sRGB blue


def test_colours_outside_the_gamut_stay_valid():
    rgb = oklch_to_srgb(0.7, 0.4, np.linspace(0, 360, 361))

    assert np.all((rgb >= 0) & (rgb <= 1))


def test_notes_follow_castel():
    c, g = oklch_to_srgb(0.7, 0.15, pitch_class_hues()[[0, 7]])

    assert np.argmax(c) == 2  # C is blue
    assert np.argmax(g) == 0  # G is red


def test_sine_at_440_hz_gets_the_colour_of_a():
    hue = colors_of("02_sine_440hz")["hue"]
    difference = (hue - pitch_class_hues()[9] + 180) % 360 - 180

    assert np.all(np.abs(difference[15:-15]) < 10)  # skips the fades at the edges


def test_silence_is_grey():
    assert np.all(colors_of("01_silence")["chroma"] == 0)


def test_sweep_gets_lighter():
    lightness = colors_of("03_sweep_100-4000hz")["lightness"]

    assert spearmanr(np.arange(len(lightness)), lightness).statistic > 0.9


def test_crescendo_gets_more_vivid():
    chroma = colors_of("06_crescendo_440hz")["chroma"]

    assert spearmanr(np.arange(len(chroma)), chroma).statistic > 0.9
