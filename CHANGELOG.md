# Changelog

## [unreleased]

### Added
- **Print safe-zone** (`formats.py`, `context.py`, `cover.html.j2`): `PaperFormat` now carries
  `safe_margin_cm = 1.8` (configurable per format). The cover shell uses
  `padding: {{ safe_margin_cm }}cm 1.5cm` instead of a fixed `5vh` — institution text
  is guaranteed ≥ 1.5 cm from the physical page edge on all formats.

- **Theme palette system** (`themes.py`, `context.py`, `cover.html.j2`): `ThemePalette`
  Pydantic model + `THEME_PALETTE_REGISTRY` with four entries
  `(Theme, mode) → ThemePalette`. Template now uses CSS custom properties
  (`--color-primary`, `--color-accent`, `--color-panel-bg`, `--color-outline`)
  — zero hardcoded `#hex` colors remain in the template.

- **Auto-contrast engine** (`contrast.py` — new file): Pillow-powered mean-luminance
  analysis selects `light_text` or `dark_text` palette mode automatically when a
  background image is present. White bg → dark text; dark bg → white text.

- **SVG corner decoration system** (`decorations.py` — new file): Four vector ornaments
  (`floral_corner`, `geometric_lines`, `academic_flourish`, `dots_cluster`) rendered
  via `currentColor` — fully palette-aware and print-crisp at any zoom. Controlled by
  `pick_decorations(theme, count, seed)`.

### Changed
- **Meta data block centering** (`cover.html.j2`): Replaced flex layout with CSS table
  (`display: table / table-row / table-cell`). Labels right-align; values left-align;
  the whole block auto-centers via `margin: 0 auto`. Removed the `width: 65%` artifact.

- **CLI** (`cli.py`): Fixed pre-existing `NameError` on `bg_data_uri` (now `bg_b64`).
  Added `--theme`, `--decorations N`, and `--auto-contrast / --no-auto-contrast` flags.
  `formats-list` table now includes the `safe_margin_cm` column.

- **Streamlit UI** (`app.py`): Added Tema Visual selector, Añadir decoraciones toggle
  + slider (1–4), and Auto-contraste toggle. All three wired into `generate_layout_context`.
