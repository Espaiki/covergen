"""Physical paper format definitions. Immutable, single source of truth."""
from __future__ import annotations

from enum import Enum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

# 1 inch = 2.54 cm. Hardcoded to avoid runtime import overhead.
_CM_PER_INCH: Final[float] = 2.54


class PaperFormat(BaseModel):
    """
    Immutable physical dimensions for a printable cover.

    All units are centimeters at the model boundary; conversions
    (mm, inches, pixels) are derived properties to keep one source of truth.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=2, max_length=64)
    width_cm: float = Field(gt=0, le=100)
    height_cm: float = Field(gt=0, le=100)

    @property
    def aspect_ratio(self) -> float:
        """width / height. Useful for layout engines that auto-scale."""
        return self.width_cm / self.height_cm

    @property
    def width_mm(self) -> float:
        return self.width_cm * 10

    @property
    def height_mm(self) -> float:
        return self.height_cm * 10

    def to_pixels(self, dpi: int = 300) -> tuple[int, int]:
        """
        Convert physical dimensions to integer pixels at the given DPI.

        300 DPI is the print-grade default; 150 is acceptable for draft prints.
        """
        if dpi <= 0:
            raise ValueError(f"dpi must be positive, got {dpi}")
        w_px = round(self.width_cm / _CM_PER_INCH * dpi)
        h_px = round(self.height_cm / _CM_PER_INCH * dpi)
        return w_px, h_px


class FormatProfile(str, Enum):
    """Stable identifiers for the supported physical formats."""

    SPIRAL_NOTEBOOK = "spiral_notebook"
    LETTER_FOLDER = "letter_folder"
    SMALL_NOTEBOOK = "small_notebook"


# Open/Closed: add new profiles by extending the enum + this map.
# Consumers never instantiate PaperFormat directly — they go through this registry.
FORMAT_REGISTRY: Final[dict[FormatProfile, PaperFormat]] = {
    FormatProfile.SPIRAL_NOTEBOOK: PaperFormat(
        name="Spiral Notebook",
        width_cm=20.0,
        height_cm=26.5,
    ),
    FormatProfile.LETTER_FOLDER: PaperFormat(
        name="Letter Folder",
        width_cm=21.0,
        height_cm=27.0,
    ),
    FormatProfile.SMALL_NOTEBOOK: PaperFormat(
        name="Small Notebook",
        width_cm=16.0,
        height_cm=19.8,
    ),
}


def get_format(profile: FormatProfile) -> PaperFormat:
    """Resolve a profile to its PaperFormat. Single chokepoint for lookup."""
    try:
        return FORMAT_REGISTRY[profile]
    except KeyError as e:
        raise ValueError(f"Unregistered format profile: {profile}") from e
