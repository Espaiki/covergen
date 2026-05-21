"""SVG decoration library — vector, theme-aware, asset-free corner ornaments."""
from __future__ import annotations

import random
from typing import Literal, NamedTuple

from .themes import Theme

Position = Literal["top-left", "top-right", "bottom-left", "bottom-right"]


class DecorationSlot(NamedTuple):
    """A single decoration assignment: which SVG at which corner."""
    position: Position
    svg: str


# ── SVG library ───────────────────────────────────────────────────────────────
# Each string is a standalone <svg> with viewBox="0 0 100 100".
# CRITICAL: only stroke="currentColor" / fill="currentColor" — zero hardcoded hex.
# All ≤ 300 chars. Top-left orientation; CSS mirrors via scaleX/scaleY/scale.

_LIBRARY: dict[str, str] = {

    # Abstract bloom: circles + stems radiating from the corner.
    "floral_corner": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"'
        ' stroke="currentColor" fill="none" stroke-width="3" stroke-linecap="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<circle cx="28" cy="8" r="7"/>'
        '<circle cx="8" cy="28" r="7"/>'
        '<circle cx="30" cy="30" r="5"/>'
        '<line x1="12" y1="22" x2="12" y2="55"/>'
        '<line x1="22" y1="12" x2="55" y2="12"/>'
        '</svg>'
    ),

    # Three concentric L-bracket strokes anchored to the corner.
    "geometric_lines": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"'
        ' stroke="currentColor" fill="none" stroke-width="4">'
        '<polyline points="80,10 10,10 10,80"/>'
        '<polyline points="65,10 25,10 25,65"/>'
        '<polyline points="50,10 40,10 40,50"/>'
        '</svg>'
    ),

    # Classic fleuron curl with accent dots at start and inflection.
    "academic_flourish": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"'
        ' stroke="currentColor" fill="none" stroke-width="3" stroke-linecap="round">'
        '<path d="M10 10 C30 0 50 20 40 40 C30 60 10 50 15 30 C20 15 35 20 30 35"/>'
        '<circle cx="10" cy="10" r="4" fill="currentColor" stroke="none"/>'
        '<circle cx="30" cy="35" r="3" fill="currentColor" stroke="none"/>'
        '</svg>'
    ),

    # Cluster of 7 filled circles, decreasing radius, asymmetric scatter.
    "dots_cluster": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"'
        ' fill="currentColor">'
        '<circle cx="12" cy="12" r="11"/>'
        '<circle cx="35" cy="10" r="8"/>'
        '<circle cx="10" cy="35" r="8"/>'
        '<circle cx="30" cy="30" r="6"/>'
        '<circle cx="52" cy="14" r="5"/>'
        '<circle cx="14" cy="52" r="5"/>'
        '<circle cx="45" cy="42" r="3"/>'
        '</svg>'
    ),
}

# Which ornaments match which theme (subset for affinity-based selection).
_THEME_AFFINITY: dict[Theme, tuple[str, ...]] = {
    Theme.MINIMAL_GEOMETRIC: ("geometric_lines", "dots_cluster"),
    Theme.CLASSIC_ACADEMIC:  ("floral_corner", "academic_flourish"),
}

# Corner assignment order — first chosen ornament → first corner, etc.
_CORNER_ORDER: tuple[Position, ...] = (
    "top-right", "bottom-left", "top-left", "bottom-right",
)


def pick_decorations(
    theme: Theme,
    count: int = 2,
    seed: int | None = None,
) -> list[DecorationSlot]:
    """Pick `count` decorations from the theme affinity pool.

    Deterministic when `seed` is provided.  Corners are assigned following
    _CORNER_ORDER.  Falls back to the full library when the affinity pool is
    smaller than `count`.

    Args:
        theme:  Theme enum value that drives ornament selection.
        count:  Number of corners to decorate (0–4).
        seed:   Optional RNG seed for deterministic output.

    Returns:
        List of DecorationSlot named-tuples, one per requested corner.

    Raises:
        ValueError: If count is outside [0, 4].
    """
    if not 0 <= count <= 4:
        raise ValueError(f"count must be in [0, 4], got {count}")
    if count == 0:
        return []

    rng   = random.Random(seed)
    pool  = list(_THEME_AFFINITY.get(theme, ()))
    if len(pool) < count:
        extras = [k for k in _LIBRARY if k not in pool]
        rng.shuffle(extras)
        pool.extend(extras)

    chosen = rng.sample(pool, count)
    return [
        DecorationSlot(position=_CORNER_ORDER[i], svg=_LIBRARY[name])
        for i, name in enumerate(chosen)
    ]
