"""Visual style profiles. Shared by context builder, template, and CLI."""
from __future__ import annotations

from enum import Enum


class Theme(str, Enum):
    """Visual style profile for cover rendering.

    Values match the CSS class suffixes in the HTML template:
        body.theme-minimal-geometric / body.theme-classic-academic
    """

    MINIMAL_GEOMETRIC = "minimal-geometric"
    CLASSIC_ACADEMIC = "classic-academic"
