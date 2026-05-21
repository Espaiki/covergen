"""PDF export layer: HTML → PDF via WeasyPrint + filename normalization."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def slugify(text: str, max_length: int = 40) -> str:
    """
    Normalize an arbitrary string into a filesystem-safe slug.

    Steps:
      1. NFD-decompose Unicode (á → a + combining-acute).
      2. Strip combining marks → pure ASCII letters.
      3. Lowercase.
      4. Collapse non-alphanumeric runs into single underscores.
      5. Trim leading/trailing underscores and truncate.

    Example: "Análisis de Redes" → "analisis_de_redes"
    """
    normalized = unicodedata.normalize("NFD", text)
    ascii_only = "".join(c for c in normalized if not unicodedata.combining(c))
    lowered = ascii_only.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    return slug[:max_length] or "untitled"


def build_filename(subject: str, student: str, suffix: str = ".pdf") -> str:
    """Construct the canonical output filename."""
    return f"caratula_{slugify(subject)}_{slugify(student)}{suffix}"


class PDFExporter:
    """
    High-fidelity HTML → PDF exporter using WeasyPrint.

    WeasyPrint respects CSS Paged Media (`@page`), physical units (cm/mm),
    inline SVG, and modern CSS — exactly what the Phase 2 template depends on.
    """

    def __init__(self, output_dir: Path = Path("./output")) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def export(
        self,
        html_string: str,
        filename: str,
        base_url: str | None = None,
    ) -> Path:
        """
        Render an HTML string to PDF and persist to `output_dir / filename`.

        `base_url` controls how relative paths (fonts, images) are resolved.
        Defaults to current working dir.
        """
        # Lazy import: WeasyPrint has heavy native deps (Pango/Cairo).
        # Keeping it inside the method means slugify/build_filename remain
        # usable in test/CI environments without the full toolchain.
        from weasyprint import HTML

        out_path = self._output_dir / filename
        HTML(string=html_string, base_url=base_url or ".").write_pdf(str(out_path))
        return out_path
