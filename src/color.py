"""
OKLCH -> sRGB conversion (OKLab by Björn Ottosson). OKLCH is perceptually uniform: equal steps of
lightness, chroma or hue look like equal changes, which HSV does not guarantee.
"""
import numpy as np

# OKLab -> LMS (cube roots) and linear LMS -> linear sRGB
LAB_TO_LMS = np.array([
    [1.0, 0.3963377774, 0.2158037573],
    [1.0, -0.1055613458, -0.0638541728],
    [1.0, -0.0894841775, -1.2914855480],
])
LMS_TO_RGB = np.array([
    [4.0767416621, -3.3077115913, 0.2309699292],
    [-1.2684380046, 2.6097574011, -0.3413193965],
    [-0.0041960863, -0.7034186147, 1.7076147010],
])


def _linear_rgb(lightness, chroma, hue):
    """ Linear sRGB of OKLCH colours (hue in degrees); may fall outside [0, 1]. """
    h = np.deg2rad(hue)
    lab = np.stack(np.broadcast_arrays(lightness, chroma * np.cos(h), chroma * np.sin(h)), axis=-1)
    lms = (lab @ LAB_TO_LMS.T) ** 3
    return lms @ LMS_TO_RGB.T


def _gamma(linear):
    """ Linear -> sRGB transfer curve. """
    return np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * np.abs(linear) ** (1 / 2.4) - 0.055)


def oklch_to_srgb(lightness, chroma, hue, steps=12):
    """ sRGB in [0, 1], shape (..., 3). Colours outside the sRGB gamut lose chroma, keeping lightness and hue. """
    lightness, chroma, hue = np.broadcast_arrays(*(np.asarray(v, dtype=float) for v in (lightness, chroma, hue)))
    rgb = _linear_rgb(lightness, chroma, hue)
    outside = np.any((rgb < -1e-6) | (rgb > 1 + 1e-6), axis=-1)

    # Bisection on the chroma of the colours outside the gamut
    low, high = np.zeros_like(chroma), chroma.copy()
    for _ in range(steps):
        mid = (low + high) / 2
        candidate = _linear_rgb(lightness, mid, hue)
        fits = np.all((candidate >= -1e-6) & (candidate <= 1 + 1e-6), axis=-1)
        low, high = np.where(fits, mid, low), np.where(fits, high, mid)
    rgb = np.where(outside[..., None], _linear_rgb(lightness, low, hue), rgb)

    return np.clip(_gamma(np.clip(rgb, 0.0, 1.0)), 0.0, 1.0)
