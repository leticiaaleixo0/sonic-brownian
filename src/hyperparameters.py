"""
Hyperparameters of the simulation, in one place.
Global parameters (sample rate, fps, domain size, number of particles, seed) stay in config/default.yaml.
"""

# Normalization
MIN_RELATIVE_RANGE = 0.05 # a 5–95% range below this share of the feature's magnitude counts as constant

# Smoothing, in seconds (features.py, mapping.py)
FAST_TAU = 0.1 # intensity
SLOW_TAU = 0.5 # the other features and the colour

# Motion: target quantities, in pixels per frame (mapping.py)
VERTICAL_GAIN = 1.3 # drift speed when the vertical bias is ±1
HORIZONTAL_GAIN = 1.0 # drift speed when the horizontal bias is ±1
SIGMA_MIN = 0.6 # random speed in the quietest part of the track (while there is sound)
SIGMA_MAX = 5.0 # random speed in the loudest part
FRICTION_MIN = 0.1 # tonal sound: fluid paths
FRICTION_MAX = 0.9 # noisy sound: erratic paths

# Drift: follows how the sound changed relative to its recent past (mapping.py)
DRIFT_TAU = 3.0 # seconds of "recent past"
OCTAVES_FOR_FULL_BIAS = 1.0 # centroid change that gives the full vertical bias
SHARE_FOR_FULL_BIAS = 0.2 # treble − bass energy share change that gives the full horizontal bias

# Attacks (mapping.py)
ONSET_GAIN = 40.0 # distance (px) an attack moves the particles at the typical radius of the cloud
ONSET_THRESHOLD = 1.0 # how far an onset peak must exceed the median of the last second
PULSE_FRAMES = 4 # frames until the pulse is undone

# Absolute scales, the same for every track (mapping.py)
PRESENCE_DB = (-60.0, -30.0) # RMS (dBFS) from silence to clearly audible
FLATNESS_DB = (-50.0, -5.0) # spectral flatness (dB) from pure tone to white noise

# Colour, in OKLCH (mapping.py, conditional_visualization.py)
HUE_OF_C = 239.0 # Castel: C blue; -30° per semitone gives G red and A violet
LIGHTNESS_RANGE = (0.55, 0.92) # lowest to highest centroid of the track
CHROMA_RANGE = (0.07, 0.20) # quietest to loudest part of the track (grey in silence)
HUE_SPREAD = 15 # fixed hue offset of each particle, up to ± this many degrees

# Particles (simulation.py, conditional_visualization.py)
INITIAL_SPREAD = 0.1 # std of the initial cloud, as a share of the domain height
TRAIL_DECAY = 0.9 # share of the trail kept from one frame to the next
