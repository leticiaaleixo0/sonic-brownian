"""
Side-by-side video: the particle video on the left and the entropy over time on the right, with the track's audio.

The particle video (render.py) is not drawn again: it is joined by ffmpeg to a second video made here, frame by frame,
from the entropy series of the task. Both panels are squares of the same size: the particle video (wider than tall)
gets black bars above and below and a frame is drawn around the area where the particles can move (the whole simulation
domain), so the limits of their space can be seen. Nothing is cropped or stretched. The curve of the right-hand side grows as the music plays, with a marker on the
current value, the same one the web interface shows under the player.

Usage (from the repository root, after rendering the video of a task, with `entropy` as in api/services.py):
    from src.render_combined import export_side_by_side
    export_side_by_side("data/videos/<id>.mp4", entropy, "data/videos/<id>_entropy.mp4")
"""
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import matplotlib
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image, ImageDraw, ImageFont

# Colours of the web interface (index.css), so the video looks like the chart on the page
BACKGROUND = "#0d1117"
GRID = "#21262d"
TEXT = "#8b949e"
CURVE = "#58a6ff"
CURVE_FAINT = "#1b3a5e" # the part of the curve the music has not reached yet
MAXIMUM = "#d29922"
CURSOR = "#c9d1d9"

CURVE_WIDTH = 3
FRAME_MARGIN = 24 # px of black between the frame and the edge of the panel
FRAME_THICKNESS = 2
FRAME_COLOR = "0xc9d1d9@0.9" # ffmpeg colour@opacity of the frame around the particles' domain
CRF = 20 # x264 quality: lower is better (18 is almost lossless, 23 is the default)
FONT_PATH = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSansMono.ttf"
REFERENCE_SIDE = 1188 # panel side (px) the text and line sizes here are tuned for; other panels scale them


def _background(entropy, max_entropy, duration, width, height):
    """The part of the chart that never changes, as a PIL image, plus the function (seconds, nats) -> pixel."""
    dpi = 100 * height / REFERENCE_SIDE # fixes the pixel size via figsize, so it only scales text and lines
    figure = Figure(figsize=(width / dpi, height / dpi), dpi=dpi, facecolor=BACKGROUND)
    FigureCanvasAgg(figure)
    axes = figure.add_axes([0.10, 0.24, 0.86, 0.52], facecolor=BACKGROUND)

    y_min = np.floor((entropy.min() - 0.2) * 2) / 2
    y_max = np.ceil((max(entropy.max(), max_entropy) + 0.1) * 2) / 2
    axes.set_xlim(0, duration)
    axes.set_ylim(y_min, y_max)

    time = np.linspace(0, duration, len(entropy))
    axes.plot(time, entropy, color=CURVE_FAINT, linewidth=CURVE_WIDTH / 2)
    axes.axhline(max_entropy, color=MAXIMUM, linewidth=1, linestyle=(0, (5, 4)))
    axes.text(duration, max_entropy, "máximo: distribuição uniforme no quadro", color=MAXIMUM, fontsize=9,
              ha="right", va="bottom")

    axes.grid(color=GRID, linewidth=1)
    axes.set_axisbelow(True)
    axes.tick_params(colors=TEXT, labelsize=9)
    for side in axes.spines.values():
        side.set_color(GRID)
    axes.set_xlabel("tempo (s)", color=TEXT, fontsize=10)
    axes.set_ylabel("S (nats)", color=TEXT, fontsize=10)
    figure.text(0.5, 0.88, r"Entropia da distribuição das partículas, $S(t) = -\int \rho \, \ln \rho \; dA$",
                color=CURSOR, fontsize=13, ha="center", va="center")

    figure.canvas.draw()
    image = Image.fromarray(np.asarray(figure.canvas.buffer_rgba())[..., :3].copy())

    def to_pixel(seconds, value):
        x, y = axes.transData.transform((seconds, value))
        return float(x), float(height - y) # matplotlib's y grows upwards; the image's grows downwards

    plot_top = to_pixel(0, y_max)[1]
    plot_bottom = to_pixel(0, y_min)[1]
    return image, to_pixel, plot_top, plot_bottom


def render_entropy_frames(entropy_data, n_frames, width, height):
    """Yield the n_frames RGB frames (bytes, width x height) of the entropy video: frame i is at t = i / fps."""
    fps = entropy_data["fps"]
    entropy = np.asarray(entropy_data["entropy"], dtype=float)
    duration = max(len(entropy) - 1, 1) / fps
    seconds = np.arange(len(entropy)) / fps

    background, to_pixel, plot_top, plot_bottom = _background(entropy, entropy_data["max_entropy"], duration, width, height)
    points = [to_pixel(t, s) for t, s in zip(seconds, entropy)]
    scale = height / REFERENCE_SIDE
    font = ImageFont.truetype(str(FONT_PATH), round(14 * scale))
    curve_width, radius = max(round(CURVE_WIDTH * scale), 1), 5 * scale
    cursor_width, ring_width = max(round(scale), 1), max(round(2 * scale), 1)

    drawn = background.copy() # accumulates the curve: each frame only adds one segment to it
    drawn_draw = ImageDraw.Draw(drawn)
    for i in range(n_frames):
        index = min(i, len(entropy) - 1)
        if index > 0:
            drawn_draw.line([points[index - 1], points[index]], fill=CURVE, width=curve_width, joint="curve")

        frame = drawn.copy()
        draw = ImageDraw.Draw(frame)
        x, y = points[index]
        draw.line([(x, plot_top), (x, plot_bottom)], fill=CURSOR, width=cursor_width)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=BACKGROUND, outline=CURSOR, width=ring_width)
        readout = f"t = {seconds[index]:.1f} s de {duration:.1f} s  ·  S = {entropy[index]:.2f} nats"
        draw.text((width / 2, height * 0.88), readout, fill=TEXT, font=font, anchor="mm")
        yield frame.tobytes()


def export_side_by_side(video_path, entropy_data, output_path, width=None, height=None):
    """Join the particle video (left) to the entropy video (right), keeping the audio of the first. Returns output_path.

    video_path: MP4 made by render.export_video.
    entropy_data: {"fps", "time", "entropy", "max_entropy"}, as in the API's entropy response.
    width, height: size of the video panels; default is a square whose side is the larger side of the particle video
    plus a margin, so the frame around the particles fits inside it.
    """
    video_path, output_path = Path(video_path), Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    video_width, video_height = _video_size(ffmpeg, video_path)
    if width is None or height is None:
        width = height = max(video_width, video_height) + 2 * FRAME_MARGIN # even, as yuv420p needs
    left, top = (width - video_width) // 2, (height - video_height) // 2 # where the particle video sits in its panel
    t = FRAME_THICKNESS
    left_panel = (
        f"[0:v]pad={width}:{height}:{left}:{top}:black,"
        f"drawbox=x={left - t - 1}:y={top - t - 1}:w={video_width + 2 * (t + 1)}:h={video_height + 2 * (t + 1)}:color={FRAME_COLOR}:t={t}[left]"
    ) # the frame is drawn just outside the video, so it hides no particle
    fps = entropy_data["fps"]
    n_frames = _count_frames(ffmpeg, video_path, fps)

    command = [
        ffmpeg, "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-framerate", str(fps), "-i", "-",
        "-filter_complex", f"{left_panel};[left][1:v]hstack=inputs=2:shortest=1[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-crf", str(CRF), "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart",
        str(output_path),
    ]
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors)
        try:
            for frame in render_entropy_frames(entropy_data, n_frames, width, height):
                process.stdin.write(frame)
        except BrokenPipeError:
            pass # ffmpeg stopped early; its message is reported below
        finally:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
            code = process.wait()
        if code != 0:
            errors.seek(0)
            raise RuntimeError(f"ffmpeg failed: {errors.read().decode(errors='replace')[-500:]}")
    return output_path


def _probe(ffmpeg, video_path):
    """The text ffmpeg prints about the file (it has no ffprobe here, but the header of -i is enough)."""
    result = subprocess.run([ffmpeg, "-i", str(video_path)], capture_output=True, text=True)
    return result.stderr


def _video_size(ffmpeg, video_path):
    import re
    match = re.search(r"Video:.*?,\s(\d{2,5})x(\d{2,5})", _probe(ffmpeg, video_path))
    if not match:
        raise RuntimeError(f"Could not read the size of {video_path}")
    return int(match.group(1)), int(match.group(2))


def _count_frames(ffmpeg, video_path, fps):
    import re
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", _probe(ffmpeg, video_path))
    if not match:
        raise RuntimeError(f"Could not read the duration of {video_path}")
    hours, minutes, seconds = int(match.group(1)), int(match.group(2)), float(match.group(3))
    # The container duration includes the audio, which can be a few ms longer than the frames: -shortest trims the excess
    return int(round((hours * 3600 + minutes * 60 + seconds) * fps)) + 2
