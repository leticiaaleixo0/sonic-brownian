"""
Run from the repository root:
    pytest tests/
"""
import pytest

from src.hyperparameters import VIDEO_HEIGHTS
from src.render import video_size


@pytest.mark.parametrize("video_height", VIDEO_HEIGHTS.values())
def test_video_size_keeps_aspect_ratio_and_even_sides(video_height):
    width, height = video_size(1140, 604, video_height)
    assert height == video_height
    assert width % 2 == 0 and height % 2 == 0
    assert width / height == pytest.approx(1140 / 604, abs=2 / height)


def test_video_size_rounds_odd_heights_to_even():
    assert video_size(1920, 1080, 481) == (854, 480)
