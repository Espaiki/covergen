# covergen

Generador modular de carátulas imprimibles (PDF) para cuadernos y carpetas.
Pipeline: **Pydantic** (validación) → **Jinja2** (templating) → **WeasyPrint** (PDF print-grade).

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│  CLI / JSON  │──▶│  CoverData    │──▶│  HTML/CSS/SVG │──▶│   PDF    │
│   (Typer)    │    │  (Pydantic)  │    │   (Jinja2)   │    │(WeasyPrint)│
└──────────────┘    └──────────────┘    └──────────────┘    └──────────┘
```

---

## 1. Dependencias del sistema (WeasyPrint)

WeasyPrint depende de librerías nativas para renderizar PDF de alta fidelidad.
Instálalas **antes** del `pip install`.

### Linux (Ubuntu / Debian)
```bash
sudo apt update
sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
                    libcairo2 libgdk-pixbuf-2.0-0 libffi-dev \
                    fonts-liberation
```

### macOS (Homebrew)
```bash
brew install pango libffi
```

### Windows
1. Descargar e instalar **GTK3 runtime** desde:
   https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
2. Reiniciar la terminal después de instalar.
3. Verificar que `gtk-runtime` quedó en el PATH.

> Si WeasyPrint sigue rompiendo en tu entorno, ver la sección **Fallback**
> al final de este README.

---

## 2. Instalación del paquete

```bash
# Entrar al proyecto
cd covergen-project

# (Recomendado) entorno virtual
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows PowerShell

# Instalar covergen + dependencias
pip install -e .

# Verificar
covergen --help
```

Alternativa sin `pyproject.toml`:
```bash
pip install -r requirements.txt
python -m covergen --help
```

---

## 3. Uso

### Modo A — JSON config (recomendado para iteración rápida)
```bash
covergen generate --config examples/config.example.json
```

### Modo B — Flags CLI (uso ad-hoc)
```bash
covergen generate \
    --institution "UTPL" \
    --subject "Análisis de Redes" \
    --teacher "Dr. Carlos Mendoza" \
    --student "Adrian Valarezo" \
    --grade "Tercer Ciclo" \
    --year "2026-2027" \
    --format spiral_notebook \
    --theme minimal-geometric
```

### Modo C — JSON + override por flags
Los flags CLI sobrescriben los valores del JSON cuando se pasan explícitos:
```bash
covergen generate --config examples/config.example.json --theme classic-academic
```

### Output
El PDF se guarda en `./output/` con el formato:
```
caratula_<materia_slug>_<estudiante_slug>.pdf
```
Ejemplo: `caratula_analisis_de_redes_adrian_valarezo.pdf`

### Subcomandos auxiliares
```bash
covergen formats-list   # Lista formatos físicos con dimensiones
covergen themes-list    # Lista estilos visuales
```

---

## 4. Estructura del proyecto

```
covergen-project/
├── pyproject.toml
├── requirements.txt
├── README.md
├── examples/
│   └── config.example.json
└── covergen/
    ├── __init__.py
    ├── __main__.py          # python -m covergen
    ├── cli.py               # Typer CLI + Rich output
    ├── formats.py           # Phase 1: PaperFormat + registry
    ├── models.py            # Phase 1: CoverData (Pydantic validation)
    ├── themes.py            # Theme enum
    ├── context.py           # Phase 1: LayoutContextBuilder
    ├── renderer.py          # Phase 3: Jinja2 wrapper
    ├── exporter.py          # Phase 3: WeasyPrint + slugify
    └── templates/
        └── cover.html.j2    # Phase 2: dual-theme template
```

---

## 5. Formatos físicos disponibles

| ID                | Dimensiones      | Uso típico              |
|-------------------|------------------|-------------------------|
| `spiral_notebook` | 20.0 × 26.5 cm   | Cuaderno espiral A4-ish |
| `letter_folder`   | 21.0 × 27.0 cm   | Carpeta tamaño carta    |
| `small_notebook`  | 16.0 × 19.8 cm   | Cuaderno pequeño        |

---

## 6. Temas visuales

- **`minimal-geometric`** — Sans-serif (Inter / Space Grotesk), composición
  asimétrica, líneas verticales y un dot-grid sutil, marca geométrica
  cuadrado+círculo. Estética editorial moderna.
- **`classic-academic`** — Serif (Cormorant Garamond / EB Garamond), doble
  borde con ornamentos en las cuatro esquinas, fleurón central. Estética
  académica tradicional.

---

## 7. Fallback — alternativa si WeasyPrint falla

Si las deps nativas son demasiado dolor en tu entorno (Windows sin admin,
WSL roto, etc.), reemplaza `exporter.py` con un backend de **Playwright**:

```bash
pip install playwright
playwright install chromium
```

```python
# exporter.py — variante Playwright
from playwright.sync_api import sync_playwright

def export_with_playwright(html_string: str, out_path: Path,
                            width_cm: float, height_cm: float) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_string, wait_until="networkidle")
        page.pdf(
            path=str(out_path),
            width=f"{width_cm}cm",
            height=f"{height_cm}cm",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
```

Trade-off: +~150MB de binario Chromium, pero CSS support 100% completo y
zero deps nativas a instalar manualmente.

---

## 8. Extender el sistema

| Quieres añadir...          | Tocar archivo(s)                          |
|----------------------------|-------------------------------------------|
| Nuevo formato físico       | `formats.py` (enum + registry entry)      |
| Nuevo tema visual          | `themes.py` + bloque CSS en `cover.html.j2` |
| Nuevo campo en la carátula | `models.py` + `context.py` + template     |
| Nuevo backend de export    | Subclase de `PDFExporter` o nuevo módulo  |

---

## 9. Troubleshooting

| Síntoma                                              | Causa probable                                      |
|------------------------------------------------------|------------------------------------------------------|
| `OSError: cannot load library 'libgobject-2.0...'`   | Falta GTK / Pango. Ver sección 1.                   |
| Fonts se ven como Times New Roman en el PDF          | Sin internet (Google Fonts no descarga). Cachea las fuentes localmente o usa `@font-face` con TTF en disco. |
| `ValidationError: school_year ...`                   | El año debe ser `YYYY-YYYY` con años consecutivos. |
| Carátula sale cortada / overflow                      | Algún campo es demasiado largo. Ajustar `max-width` en el CSS o acortar el contenido. |

---

## License

MIT
