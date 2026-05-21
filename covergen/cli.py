"""Command-line interface for covergen. Built on Typer + Rich."""
import base64
import json
from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .context import LayoutContextBuilder
from .exporter import PDFExporter, build_filename
from .formats import FormatProfile
from .models import CoverData
from .renderer import TemplateRenderer

app = typer.Typer(
    name="covergen",
    help="Generador de carátulas imprimibles para cuadernos y carpetas.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()

_CONTENT_KEYS = (
    "institution_name",
    "subject_name",
    "teacher_name",
    "student_name",
    "grade_course",
    "school_year",
)

_MIME: dict[str, str] = {
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _load_config(path: Path) -> dict:
    if not path.is_file():
        console.print(f"[red]Config file not found:[/] {path}")
        raise typer.Exit(code=1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in {path}:[/] {e}")
        raise typer.Exit(code=1)


def _image_to_b64(path: Path) -> str:
    """Read an image file and return a plain base64 string (no data-URI prefix)."""
    if not path.is_file():
        console.print(f"[red]Background image not found:[/] {path}")
        raise typer.Exit(code=1)
    return base64.b64encode(path.read_bytes()).decode()


def _resolve_inputs(
    config_path: Optional[Path],
    cli_fields: dict,
    cli_format: FormatProfile,
    cli_background: Optional[Path],
    cli_dpi: int,
) -> tuple[dict, FormatProfile, str | None, int]:
    """Merge JSON config + CLI flags. CLI flags win when passed explicitly."""
    bg_b64: str | None = None

    if config_path is not None:
        data = _load_config(config_path)
        fmt = FormatProfile(data.pop("format", cli_format.value))
        dpi = int(data.pop("dpi", cli_dpi))
        bg_path_str: str = data.pop("background", "")
        for k, v in cli_fields.items():
            if v is not None:
                data[k] = v
        # CLI --background wins over JSON "background" key
        if cli_background is not None:
            bg_b64 = _image_to_b64(cli_background)
        elif bg_path_str:
            bg_b64 = _image_to_b64(Path(bg_path_str))
        return data, fmt, bg_b64, dpi

    missing = [k for k, v in cli_fields.items() if v is None]
    if missing:
        console.print(
            f"[red]Missing required fields:[/] {', '.join(missing)}\n"
            "[dim]Pass them as flags or use --config <file.json>.[/]"
        )
        raise typer.Exit(code=1)

    if cli_background is not None:
        bg_b64 = _image_to_b64(cli_background)

    return dict(cli_fields), cli_format, bg_b64, cli_dpi


@app.command()
def generate(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c",
        help="Ruta a archivo JSON con campos de contenido y/o ajustes."
    ),
    institution: Optional[str] = typer.Option(None, "--institution"),
    subject:     Optional[str] = typer.Option(None, "--subject"),
    teacher:     Optional[str] = typer.Option(None, "--teacher"),
    student:     Optional[str] = typer.Option(None, "--student"),
    grade:       Optional[str] = typer.Option(None, "--grade"),
    year:        Optional[str] = typer.Option(None, "--year"),
    format_profile: FormatProfile = typer.Option(
        FormatProfile.SPIRAL_NOTEBOOK, "--format", "-f",
        case_sensitive=False,
    ),
    background: Optional[Path] = typer.Option(
        None, "--background", "-b",
        help="Ruta a una imagen PNG/JPG para usar como fondo de la carátula.",
    ),
    output_dir: Path = typer.Option(Path("./output"), "--output-dir", "-o"),
    dpi: int = typer.Option(300, "--dpi"),
) -> None:
    """Genera una carátula PDF desde JSON config y/o flags CLI."""

    cli_fields = {
        "institution_name": institution,
        "subject_name":     subject,
        "teacher_name":     teacher,
        "student_name":     student,
        "grade_course":     grade,
        "school_year":      year,
    }

    data, format_profile, bg_b64, dpi = _resolve_inputs(
        config, cli_fields, format_profile, background, dpi
    )

    try:
        cover = CoverData(**{k: data[k] for k in _CONTENT_KEYS if k in data})
    except ValidationError as e:
        console.print(Panel(str(e), title="[red]Validation Error", border_style="red"))
        raise typer.Exit(code=1)
    except KeyError as e:
        console.print(f"[red]Missing field in config: {e}[/]")
        raise typer.Exit(code=1)

    context = dict(LayoutContextBuilder(
        cover=cover,
        format_profile=format_profile,
        dpi=dpi,
        background_image_b64=bg_b64,
    ).build())

    renderer = TemplateRenderer()
    html_string = renderer.render("cover.html.j2", context)

    filename = build_filename(cover.subject_name, cover.student_name)
    exporter = PDFExporter(output_dir=output_dir)
    out_path = exporter.export(html_string, filename, base_url=str(renderer.templates_dir))

    summary = Table(show_header=False, box=None, padding=(0, 1))
    summary.add_row("[bold]Institución[/]", cover.institution_name)
    summary.add_row("[bold]Materia[/]",     cover.subject_name)
    summary.add_row("[bold]Estudiante[/]",  cover.student_name)
    summary.add_row(
        "[bold]Formato[/]",
        f"{context['format_name']} ({context['width_cm']}×{context['height_cm']} cm)",
    )
    bg_label = "imagen personalizada" if bg_data_uri else "gradiente CSS (sin imagen)"
    summary.add_row("[bold]Fondo[/]",  bg_label)
    summary.add_row("[bold]Output[/]", str(out_path.resolve()))
    console.print(Panel(summary, title="[green]✓ Carátula generada", border_style="green"))


@app.command()
def formats_list() -> None:
    """Lista los formatos físicos disponibles con sus dimensiones."""
    from .formats import FORMAT_REGISTRY

    table = Table(title="Formatos físicos disponibles")
    table.add_column("ID",     style="cyan")
    table.add_column("Nombre", style="bold")
    table.add_column("Ancho",  justify="right")
    table.add_column("Alto",   justify="right")
    table.add_column("Ratio",  justify="right", style="dim")

    for profile, paper in FORMAT_REGISTRY.items():
        table.add_row(
            profile.value, paper.name,
            f"{paper.width_cm} cm", f"{paper.height_cm} cm",
            f"{paper.aspect_ratio:.3f}",
        )
    console.print(table)


@app.command()
def backgrounds_list() -> None:
    """Lista las imágenes de fondo disponibles en assets/backgrounds/."""
    assets_dir = Path(__file__).parent.parent / "assets" / "backgrounds"
    if not assets_dir.is_dir():
        console.print("[yellow]Directorio assets/backgrounds/ no encontrado.[/]")
        raise typer.Exit()

    table = Table(title="Fondos predefinidos disponibles")
    table.add_column("Archivo",  style="cyan")
    table.add_column("Tamaño",   justify="right")

    imgs = [p for p in sorted(assets_dir.iterdir()) if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    if not imgs:
        console.print("[dim]Sin imágenes en assets/backgrounds/.[/]")
        raise typer.Exit()

    for p in imgs:
        size_kb = p.stat().st_size / 1024
        table.add_row(p.name, f"{size_kb:.1f} KB")
    console.print(table)


if __name__ == "__main__":
    app()
