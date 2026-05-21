"""covergen — Generador de carátulas imprimibles para cuadernos y carpetas."""
from __future__ import annotations

__version__ = "0.1.0"

from .formats import FormatProfile, PaperFormat
from .models import CoverData
from .themes import Theme

__all__ = ["CoverData", "FormatProfile", "PaperFormat", "Theme", "__version__"]
