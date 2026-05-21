"""Layout context builder. Bridges validated content + physical geometry + theme."""
from __future__ import annotations

from typing import Any, TypedDict

from .decorations import DecorationSlot
from .formats import FormatProfile, PaperFormat, get_format
from .models import CoverData
from .themes import Theme, ThemePalette, get_palette

# Palabras que deben mantenerse en minúscula en títulos en español.
_SPANISH_LOWERCASE_WORDS: frozenset[str] = frozenset({
    "a", "al", "ante", "bajo", "con", "de", "del", "desde", "e", "el",
    "en", "entre", "hacia", "hasta", "la", "las", "lo", "los", "o",
    "para", "por", "sin", "sobre", "tras", "u", "un", "una", "unas",
    "unos", "y",
})


def _clean_spanish_title(text: str) -> str:
    """Title-case that preserves Spanish grammar (prepositions stay lowercase)."""
    words = text.split()
    result: list[str] = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in _SPANISH_LOWERCASE_WORDS:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)


class LayoutContext(TypedDict):
    """Explicit shape of the dict consumed by the template engine."""

    # --- content (normalized) ---
    institution_name: str
    subject_name:     str
    teacher_name:     str
    student_name:     str
    grade_course:     str
    school_year:      str

    # --- geometry ---
    format_id:       str
    format_name:     str
    width_cm:        float
    height_cm:       float
    width_mm:        float
    height_mm:       float
    width_px:        int
    height_px:       int
    aspect_ratio:    float
    dpi:             int
    safe_margin_cm:  float        # Phase 1 — print-safe clearance

    # --- presentation ---
    background_image_b64: str | None
    course_label:         str
    palette_primary:      str    # Phase 2 — CSS custom properties
    palette_accent:       str
    palette_panel_bg:     str
    palette_outline:      str
    decorations:          list[dict] | None   # Phase 4 — SVG corner slots


class LayoutContextBuilder:
    """
    Single Responsibility: assemble the normalized context dict.

    Kept as a class so future variants (bleed margins, locale rules) can
    subclass without touching the validated models.
    """

    def __init__(
        self,
        cover:               CoverData,
        format_profile:      FormatProfile,
        dpi:                 int = 300,
        background_image_b64: str | None = None,
        educational_level:   str = "Colegio / Universidad",
        theme:               Theme = Theme.MINIMAL_GEOMETRIC,
        palette:             ThemePalette | None = None,
        decorations:         list[DecorationSlot] | None = None,
    ) -> None:
        self._cover        = cover
        self._profile      = format_profile
        self._paper: PaperFormat = get_format(format_profile)
        self._dpi          = dpi
        self._bg           = background_image_b64
        self._educational_level = educational_level
        self._theme        = theme
        # If no palette supplied, fall back to light_text for the given theme.
        self._palette      = palette if palette is not None else get_palette(theme, "light_text")
        self._decorations  = decorations or []

    # --- normalization ---

    def _normalize_institution(self, name: str) -> str:
        return name.upper()

    def _normalize_proper_name(self, name: str) -> str:
        return name.title()

    # --- build ---

    def build(self) -> LayoutContext:
        """Produce the flat, render-ready context dict."""
        width_px, height_px = self._paper.to_pixels(self._dpi)

        return LayoutContext(
            institution_name=self._normalize_institution(self._cover.institution_name),
            subject_name    =_clean_spanish_title(self._cover.subject_name),
            teacher_name    =self._cover.teacher_name,
            student_name    =self._normalize_proper_name(self._cover.student_name),
            grade_course    =self._cover.grade_course,
            school_year     =self._cover.school_year,

            format_id    =self._profile.value,
            format_name  =self._paper.name,
            width_cm     =self._paper.width_cm,
            height_cm    =self._paper.height_cm,
            width_mm     =self._paper.width_mm,
            height_mm    =self._paper.height_mm,
            width_px     =width_px,
            height_px    =height_px,
            aspect_ratio =round(self._paper.aspect_ratio, 4),
            dpi          =self._dpi,
            safe_margin_cm=self._paper.safe_margin_cm,

            background_image_b64=self._bg,
            course_label=("Grado" if self._educational_level == "Escuela" else "Curso"),

            palette_primary =self._palette.primary,
            palette_accent  =self._palette.accent,
            palette_panel_bg=self._palette.panel_bg,
            palette_outline =self._palette.outline,

            decorations=[{"position": d.position, "svg": d.svg}
                         for d in self._decorations] or None,
        )


def generate_layout_context(
    cover:                CoverData,
    format_profile:       FormatProfile,
    dpi:                  int = 300,
    background_image_b64: str | None = None,
    educational_level:    str = "Colegio / Universidad",
    theme:                Theme = Theme.MINIMAL_GEOMETRIC,
    palette:              ThemePalette | None = None,
    decorations:          list[DecorationSlot] | None = None,
) -> dict[str, Any]:
    """Facade entry point — returns a render-ready context dict for the template."""
    return dict(
        LayoutContextBuilder(
            cover, format_profile, dpi,
            background_image_b64, educational_level,
            theme, palette, decorations,
        ).build()
    )
