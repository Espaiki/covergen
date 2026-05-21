"""Visual style profiles, palettes, and registry. Shared by context, template, and CLI."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Theme(str, Enum):
    """Visual style profile for cover rendering."""

    MINIMAL_GEOMETRIC = "minimal-geometric"
    CLASSIC_ACADEMIC  = "classic-academic"


class ThemePalette(BaseModel):
    """Color palette consumed by the template as CSS custom properties."""

    model_config = ConfigDict(frozen=True)

    primary:  str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    accent:   str = Field(default="#FDE047", pattern=r"^#[0-9A-Fa-f]{6}$")
    panel_bg: str = Field(default="rgba(0,0,0,0.38)")
    outline:  str = Field(default="rgba(0,0,0,0.85)")


# Registry keyed by (Theme, mode). mode ∈ {"light_text", "dark_text"}.
THEME_PALETTE_REGISTRY: dict[tuple[Theme, str], ThemePalette] = {
    (Theme.MINIMAL_GEOMETRIC, "light_text"): ThemePalette(
        primary="#FFFFFF", accent="#FDE047",
        panel_bg="rgba(0,0,0,0.38)", outline="rgba(0,0,0,0.85)"),
    (Theme.MINIMAL_GEOMETRIC, "dark_text"): ThemePalette(
        primary="#0F172A", accent="#B45309",
        panel_bg="rgba(255,255,255,0.55)", outline="rgba(255,255,255,0.90)"),
    (Theme.CLASSIC_ACADEMIC, "light_text"): ThemePalette(
        primary="#FFFFFF", accent="#FCD34D",
        panel_bg="rgba(30,20,10,0.45)", outline="rgba(0,0,0,0.90)"),
    (Theme.CLASSIC_ACADEMIC, "dark_text"): ThemePalette(
        primary="#1C1917", accent="#92400E",
        panel_bg="rgba(255,250,240,0.60)", outline="rgba(255,255,255,0.85)"),
}


def get_palette(theme: Theme, mode: str = "light_text") -> ThemePalette:
    """Return the ThemePalette for the given theme and contrast mode."""
    try:
        return THEME_PALETTE_REGISTRY[(theme, mode)]
    except KeyError:
        raise ValueError(f"No palette registered for ({theme!r}, {mode!r})")
