"""Layout context builder. Bridges validated content + physical geometry + background."""
from __future__ import annotations

from typing import Any, TypedDict

from .formats import FormatProfile, PaperFormat, get_format
from .models import CoverData

# Palabras que deben mantenerse en minúscula en títulos en español
# (preposiciones, artículos y conjunciones de uso frecuente).
_SPANISH_LOWERCASE_WORDS: frozenset[str] = frozenset({
    "a", "al", "ante", "bajo", "con", "de", "del", "desde", "e", "el",
    "en", "entre", "hacia", "hasta", "la", "las", "lo", "los", "o",
    "para", "por", "sin", "sobre", "tras", "u", "un", "una", "unas",
    "unos", "y",
})


def _clean_spanish_title(text: str) -> str:
    """Title-case that preserves Spanish grammar.

    Capitalizes the first word unconditionally; subsequent words are kept
    lowercase if they belong to the preposition/article/conjunction list.
    """
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
    subject_name: str
    teacher_name: str
    student_name: str
    grade_course: str
    school_year: str

    # --- geometry ---
    format_id: str
    format_name: str
    width_cm: float
    height_cm: float
    width_mm: float
    height_mm: float
    width_px: int
    height_px: int
    aspect_ratio: float
    dpi: int

    # --- presentation ---
    background_image_b64: str | None   # raw base64 string, or None when no image
    course_label: str                  # "Grado" (Escuela) | "Curso" (Colegio/Universidad)


class LayoutContextBuilder:
    """
    Single Responsibility: assemble the normalized context dict.

    Kept as a class (not a free function) so future variants — bleed margins,
    safe-print zones, locale-specific casing rules — can subclass without
    touching the validated models.
    """

    def __init__(
        self,
        cover: CoverData,
        format_profile: FormatProfile,
        dpi: int = 300,
        background_image_b64: str | None = None,
        educational_level: str = "Colegio / Universidad",
    ) -> None:
        self._cover: CoverData = cover
        self._profile: FormatProfile = format_profile
        self._paper: PaperFormat = get_format(format_profile)
        self._dpi: int = dpi
        self._bg: str | None = background_image_b64
        self._educational_level: str = educational_level

    # --- normalization hooks (override-friendly under Open/Closed) ---

    def _normalize_institution(self, name: str) -> str:
        """Institutions render in uppercase by convention."""
        return name.upper()

    def _normalize_proper_name(self, name: str) -> str:
        """Title-case for student/teacher names."""
        return name.title()

    # --- build ---

    def build(self) -> LayoutContext:
        """Produce the flat, render-ready context dict."""
        width_px, height_px = self._paper.to_pixels(self._dpi)

        return LayoutContext(
            institution_name=self._normalize_institution(self._cover.institution_name),
            subject_name=_clean_spanish_title(self._cover.subject_name),
            teacher_name=self._cover.teacher_name,
            student_name=self._normalize_proper_name(self._cover.student_name),
            grade_course=self._cover.grade_course,
            school_year=self._cover.school_year,

            format_id=self._profile.value,
            format_name=self._paper.name,
            width_cm=self._paper.width_cm,
            height_cm=self._paper.height_cm,
            width_mm=self._paper.width_mm,
            height_mm=self._paper.height_mm,
            width_px=width_px,
            height_px=height_px,
            aspect_ratio=round(self._paper.aspect_ratio, 4),
            dpi=self._dpi,

            background_image_b64=self._bg,
            course_label="Grado" if self._educational_level == "Escuela" else "Curso",
        )


def generate_layout_context(
    cover: CoverData,
    format_profile: FormatProfile,
    dpi: int = 300,
    background_image_b64: str | None = None,
    educational_level: str = "Colegio / Universidad",
) -> dict[str, Any]:
    """
    Facade entry point. Returns a render-ready context dict for the template engine.

    Args:
        background_image_b64: Raw base64-encoded image bytes (no data-URI prefix),
            or None to fall back to the CSS gradient defined in the template.
        educational_level: "Escuela" → course_label="Grado";
            anything else → course_label="Curso".
    """
    return dict(
        LayoutContextBuilder(
            cover, format_profile, dpi, background_image_b64, educational_level
        ).build()
    )
