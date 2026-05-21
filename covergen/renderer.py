"""Jinja2 rendering layer. Thin, opinionated wrapper around the Environment."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

# Default templates directory ships inside the package.
DEFAULT_TEMPLATES_DIR: Path = Path(__file__).parent / "templates"


class TemplateRenderer:
    """
    Wraps a Jinja2 Environment with print-template defaults:
      - autoescape on for HTML safety (defensive even on local files)
      - StrictUndefined raises on missing context vars (fail fast > silent gaps)
      - FileSystemLoader rooted at the package templates dir by default
    """

    def __init__(self, templates_dir: Path = DEFAULT_TEMPLATES_DIR) -> None:
        if not templates_dir.is_dir():
            raise FileNotFoundError(f"Templates dir not found: {templates_dir}")
        self._templates_dir = templates_dir
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "j2", "xml")),
            undefined=StrictUndefined,
            trim_blocks=False,
            lstrip_blocks=False,
            keep_trailing_newline=True,
        )

    @property
    def templates_dir(self) -> Path:
        return self._templates_dir

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template by name. Raises if template or any var is missing."""
        template = self._env.get_template(template_name)
        return template.render(**context)
