"""Background luminance analysis → palette mode selection.

Pillow is used ONLY for image analysis here — no text rendering, no rasterization.
"""
from __future__ import annotations

import io
from typing import Literal

from .themes import Theme, ThemePalette, get_palette

PaletteMode = Literal["light_text", "dark_text"]

_LUMA_THRESHOLD: float = 128.0   # 0..255 — midpoint of L channel
_SAMPLE_SIZE:    int   = 64       # downsample target (pixels per side)


def compute_mean_luma(image_bytes: bytes, sample_size: int = _SAMPLE_SIZE) -> float:
    """Calcula la luminancia media (0–255) de una muestra reducida de la imagen."""
    from PIL import Image  # lazy — Pillow only loaded when actually needed

    img    = Image.open(io.BytesIO(image_bytes))
    img    = img.convert("L").resize((sample_size, sample_size))
    pixels = list(img.getdata())
    return sum(pixels) / (sample_size * sample_size)


def select_palette_mode(image_bytes: bytes) -> PaletteMode:
    """Bright bg → dark_text.  Dark bg → light_text."""
    luma = compute_mean_luma(image_bytes)
    return "dark_text" if luma > _LUMA_THRESHOLD else "light_text"


def auto_select_palette(image_bytes: bytes, theme: Theme) -> ThemePalette:
    """Analyze bg bytes and return the best-contrast ThemePalette for `theme`."""
    mode = select_palette_mode(image_bytes)
    return get_palette(theme, mode)
