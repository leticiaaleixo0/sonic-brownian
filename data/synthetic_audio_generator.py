"""
Generate the project's synthetic control signals.

Usage (from the repository root):
    python -m data.synthetic_audio_generator            # salva em data/audio/synthetic/
    python -m data.synthetic_audio_generator output/    # salva na pasta indicada

Sample rate and seed come from config/default.yaml.
"""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from src.config import load_config

_config = load_config()
SR = _config.sample_rate   # taxa de amostragem (Hz)
DUR = 10.0                 # duração de cada sinal (s)
AMP = 0.5                  # amplitude de pico: metade da escala, para sobrar margem
SEED = _config.seed        # semente fixa: o ruído sai igual em toda execução

# Eixo de tempo: um valor por amostra, de 0 até DUR (exclusive), em segundos.
t = np.arange(int(SR * DUR)) / SR


def fade(x, ms=10):
    """Apply short fade-in and fade-out ramps to avoid clicks at the edges."""
    n = int(SR * ms / 1000)
    ramp = np.linspace(0.0, 1.0, n)
    x = x.copy()
    x[:n] *= ramp
    x[-n:] *= ramp[::-1]
    return x


# 1. Silêncio -----------------------------------------------------------------
# Um vetor de zeros. Serve para ver se o sistema "inventa" movimento do nada.
def silence():
    return np.zeros_like(t)


# 2. Senoide fixa -------------------------------------------------------------
# x(t) = A sin(2π f t). Um tom puro: uma única frequência, volume constante.
# 440 Hz é a nota Lá, então o chroma deve apontar para "A".
def sine_wave(f=440.0):
    return fade(AMP * np.sin(2 * np.pi * f * t))


# 3. Varredura de frequência (chirp) -----------------------------------------
# Não basta trocar f por f(t) em sin(2π f(t) t): a frequência instantânea é a
# DERIVADA da fase, então a fase tem de ser a INTEGRAL da frequência:
#     φ(t) = 2π ∫ f(τ) dτ
# Usamos varredura exponencial, f(t) = f0 · (f1/f0)^(t/T): ela sobe o mesmo
# número de oitavas por segundo, que é como o ouvido percebe altura.
# A integral fechada é φ(t) = 2π f0 T / ln(k) · (k^(t/T) − 1), com k = f1/f0.
def frequency_sweep(f0=100.0, f1=4000.0):
    k = f1 / f0
    phase = 2 * np.pi * f0 * DUR / np.log(k) * (k ** (t / DUR) - 1)
    return fade(AMP * np.sin(phase))


# 4. Ruído branco -------------------------------------------------------------
# Amostras independentes e gaussianas: energia igual em todas as frequências,
# nenhuma altura definida. É o oposto da senoide.
# Dividimos o desvio padrão por 3 para quase nunca passar de AMP.
def white_noise():
    rng = np.random.default_rng(SEED)
    x = rng.normal(0.0, AMP / 3, size=t.shape)
    return fade(np.clip(x, -1.0, 1.0))


# 5. Trilha de cliques a 120 BPM ----------------------------------------------
# 120 batidas por minuto = uma a cada 60/120 = 0,5 s.
# Cada clique é um "tic" curto: uma senoide de 1 kHz com decaimento
# exponencial rápido (~5 ms). Um impulso de uma amostra só também funcionaria
# para o detector de onsets, mas quase não se ouve.
def click_track(bpm=120.0):
    x = np.zeros_like(t)
    period = 60.0 / bpm
    click_duration = 0.03
    click_time = np.arange(int(SR * click_duration)) / SR
    click = np.sin(2 * np.pi * 1000 * click_time) * np.exp(-click_time / 0.005)
    for start_time in np.arange(0.0, DUR - click_duration, period):
        i = int(round(start_time * SR))
        x[i:i + len(click)] += 0.9 * click
    return x


# 6. Crescendo ----------------------------------------------------------------
# A mesma senoide de 440 Hz multiplicada por um envelope que sobe de −40 dB
# até 0 dB. O envelope é linear em DECIBÉIS, não em amplitude, porque a
# percepção de volume é logarítmica: assim o aumento soa uniforme.
# Conversão: amplitude = 10^(dB/20).
def crescendo(db_start=-40.0, db_end=0.0, f=440.0):
    db = np.linspace(db_start, db_end, t.size)
    envelope = 10 ** (db / 20)
    return fade(AMP * envelope * np.sin(2 * np.pi * f * t))


SIGNALS = {
    "01_silence": silence,
    "02_sine_440hz": sine_wave,
    "03_sweep_100-4000hz": frequency_sweep,
    "04_white_noise": white_noise,
    "05_clicks_120bpm": click_track,
    "06_crescendo_440hz": crescendo,
}


def save_wav(x, path):
    """Convert float samples in [−1, 1] to 16-bit PCM and write a WAV file."""
    x16 = np.int16(np.clip(x, -1.0, 1.0) * 32767)
    wavfile.write(path, SR, x16)


if __name__ == "__main__":
    output_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "data/audio/synthetic")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, generate in SIGNALS.items():
        save_wav(generate(), output_dir / f"{name}.wav")
        print(f"ok  {output_dir / name}.wav")
