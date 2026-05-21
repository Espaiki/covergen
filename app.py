"""CoverGen — Streamlit web interface.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

import requests as req_lib
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from covergen.context import generate_layout_context
from covergen.contrast import auto_select_palette
from covergen.decorations import pick_decorations
from covergen.exporter import build_filename
from covergen.formats import FormatProfile
from covergen.generator import generate_cover_with_controlnet
from covergen.models import CoverData
from covergen.renderer import TemplateRenderer
from covergen.themes import Theme, get_palette

ASSETS_DIR = Path(__file__).parent / "assets" / "backgrounds"

st.set_page_config(
    page_title="CoverGen · Generador de Carátulas",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constantes de UI ──────────────────────────────────────────────────────────

_FORMAT_LABELS: dict[str, str] = {
    FormatProfile.SPIRAL_NOTEBOOK.value: "Espiral (20 × 26.5 cm)",
    FormatProfile.LETTER_FOLDER.value:   "Carpeta Oficio (21 × 27 cm)",
    FormatProfile.SMALL_NOTEBOOK.value:  "Cuaderno Pequeño (16 × 19.8 cm)",
}

_THEME_LABELS: dict[str, str] = {
    Theme.MINIMAL_GEOMETRIC.value: "Minimal Geométrico",
    Theme.CLASSIC_ACADEMIC.value:  "Clásico Académico",
}

_IMG_EXTS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})

# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()

def _file_hash(raw: bytes) -> str:
    return hashlib.md5(raw).hexdigest()

def _scan_presets() -> dict[str, Path]:
    if not ASSETS_DIR.is_dir():
        return {}
    return {p.name: p for p in sorted(ASSETS_DIR.iterdir())
            if p.suffix.lower() in _IMG_EXTS}

def _check_replicate_token() -> str | None:
    return os.getenv("REPLICATE_API_TOKEN", "").strip() or None

# ── Session state ─────────────────────────────────────────────────────────────
_STATE_DEFAULTS: dict[str, object] = {
    "pdf_bytes":              None,
    "pdf_filename":           "caratula.pdf",
    "controlnet_bg_b64":      None,
    "controlnet_sketch_hash": None,
}
for _k, _v in _STATE_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎨 CoverGen")
    st.caption("Generador de Carátulas · ControlNet Edition")
    st.divider()

    # ── Datos del documento ──
    st.subheader("Datos del Documento")
    institution = st.text_input("Institución",
        value="Universidad Técnica Particular de Loja")
    subject = st.text_input("Materia / Asignatura", value="Análisis de Redes")
    teacher = st.text_input("Docente", value="Dr. Carlos Mendoza",
        placeholder="Prof. / Dr. / Ing. Apellido")
    student = st.text_input("Estudiante", value="Adrian Valarezo")
    grade   = st.text_input("Curso / Paralelo", value="Tercer Ciclo - Paralelo A")
    year    = st.text_input("Año Lectivo", value="2026-2027", max_chars=9)

    st.divider()

    # ── Configuración ──
    st.subheader("Configuración")

    selected_format_id: str = st.selectbox(  # type: ignore[assignment]
        "Formato de Hoja",
        options=[p.value for p in FormatProfile],
        format_func=lambda v: _FORMAT_LABELS.get(v, v),
    )
    selected_format = FormatProfile(selected_format_id)

    nivel_educativo: str = st.radio(  # type: ignore[assignment]
        "Nivel Educativo",
        options=["Escuela", "Colegio / Universidad"],
        index=1, horizontal=True,
    )

    # PHASE 6 — Theme selector
    selected_theme_id: str = st.selectbox(  # type: ignore[assignment]
        "Tema Visual",
        options=[t.value for t in Theme],
        format_func=lambda v: _THEME_LABELS.get(v, v),
    )
    selected_theme = Theme(selected_theme_id)

    # PHASE 6 — Decoration controls
    use_decorations: bool = st.toggle("Añadir decoraciones", value=False)
    n_deco = 2
    if use_decorations:
        n_deco = st.slider("Cantidad de ornamentos", min_value=1, max_value=4, value=2)

    # PHASE 6 — Auto-contrast toggle
    auto_contrast_enabled: bool = st.toggle(
        "Auto-contraste",
        value=True,
        help="Ajusta el color del texto al brillo del fondo automáticamente.",
    )

    st.divider()

    # ── Boceto Guía (ControlNet) ──
    st.subheader("Boceto Guía")
    st.caption("Sube un boceto a mano. ControlNet lo convierte en arte final.")
    sketch_file = st.file_uploader(
        "Subir boceto", type=["png", "jpg", "jpeg"], key="sketch_uploader",
    )
    if sketch_file is not None:
        st.image(sketch_file, caption="Boceto cargado", use_container_width=True)
        sketch_file.seek(0)
    elif st.session_state["controlnet_bg_b64"]:
        st.info("Fondo ControlNet en caché. Sube nuevo boceto para regenerar.")

    st.divider()

    # ── Fondo Alternativo ──
    st.subheader("Fondo Alternativo")
    manual_upload = st.file_uploader(
        "Subir imagen de fondo", type=["png", "jpg", "jpeg"], key="bg_uploader",
    )
    presets = _scan_presets()
    preset_options = ["(gradiente CSS — sin imagen)"] + list(presets.keys())
    selected_preset: str = st.selectbox(  # type: ignore[assignment]
        "O elegir fondo predefinido",
        options=preset_options,
        disabled=manual_upload is not None,
    )

    st.divider()
    generate_btn = st.button(
        "⚙️ Generar / Actualizar Vista Previa",
        type="primary", use_container_width=True,
    )

# ── Área principal ────────────────────────────────────────────────────────────
st.title("Vista Previa de Carátula")

replicate_token = _check_replicate_token()
if replicate_token is None:
    st.warning(
        "**REPLICATE_API_TOKEN no configurado.** "
        "Añade la clave a tu `.env` y reinicia la app.",
        icon="⚠️",
    )

if generate_btn:

    # ── Paso 1: resolver fondo ──────────────────────────────────────────────
    bg_b64: str | None = None
    bg_bytes_raw: bytes | None = None  # needed for auto-contrast

    if sketch_file is not None and replicate_token:
        sketch_bytes = sketch_file.read()
        current_hash = _file_hash(sketch_bytes)
        cached_same  = (
            st.session_state["controlnet_bg_b64"] is not None
            and st.session_state["controlnet_sketch_hash"] == current_hash
        )
        if cached_same:
            bg_b64 = st.session_state["controlnet_bg_b64"]
            st.info("Reutilizando fondo ControlNet en caché.")
        else:
            with st.spinner(f"Generando arte con ControlNet para «{subject}»… (~30 seg.)"):
                try:
                    img_bytes = generate_cover_with_controlnet(sketch_bytes, subject)
                    bg_b64    = _to_b64(img_bytes)
                    bg_bytes_raw = img_bytes
                    st.session_state["controlnet_bg_b64"]      = bg_b64
                    st.session_state["controlnet_sketch_hash"] = current_hash
                    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
                    (ASSETS_DIR / "controlnet_result.png").write_bytes(img_bytes)
                    st.success("Arte generado con ControlNet.")
                except EnvironmentError as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Error en ControlNet: {exc}")

    elif st.session_state["controlnet_bg_b64"] and sketch_file is None:
        bg_b64 = st.session_state["controlnet_bg_b64"]

    elif manual_upload is not None:
        raw_bytes = manual_upload.read()
        bg_b64    = _to_b64(raw_bytes)
        bg_bytes_raw = raw_bytes
        st.session_state["controlnet_bg_b64"] = None

    elif selected_preset != preset_options[0]:
        raw_bytes = presets[selected_preset].read_bytes()
        bg_b64    = _to_b64(raw_bytes)
        bg_bytes_raw = raw_bytes

    # ── Paso 2: resolver paleta (PHASE 5 — auto-contrast) ──────────────────
    if bg_b64 and auto_contrast_enabled:
        # Decode raw bytes for analysis (use bg_bytes_raw if fresh, else decode b64)
        analysis_bytes = bg_bytes_raw or base64.b64decode(bg_b64)
        palette = auto_select_palette(analysis_bytes, selected_theme)
    else:
        palette = get_palette(selected_theme, "light_text")

    # ── Paso 3: resolver decoraciones (PHASE 4) ────────────────────────────
    deco_slots = (
        pick_decorations(selected_theme, count=n_deco, seed=42)
        if use_decorations else None
    )

    # ── Paso 4: compilar PDF ────────────────────────────────────────────────
    with st.spinner("Compilando PDF con WeasyPrint…"):
        try:
            cover = CoverData(
                institution_name=institution,
                subject_name=subject,
                teacher_name=teacher,
                student_name=student,
                grade_course=grade,
                school_year=year,
            )
            context = generate_layout_context(
                cover, selected_format,
                background_image_b64=bg_b64,
                educational_level=nivel_educativo,
                theme=selected_theme,
                palette=palette,
                decorations=deco_slots,
            )
            renderer    = TemplateRenderer()
            html_string = renderer.render("cover.html.j2", context)

            from weasyprint import HTML  # noqa: PLC0415

            pdf_bytes: bytes = HTML(string=html_string).write_pdf()
            st.session_state["pdf_bytes"]    = pdf_bytes
            st.session_state["pdf_filename"] = build_filename(subject, student)
            st.success("¡Carátula generada exitosamente!")

        except Exception as exc:  # noqa: BLE001
            st.error(f"Error al compilar PDF: {exc}")

# ── Vista previa + descarga ───────────────────────────────────────────────────
if st.session_state["pdf_bytes"]:
    b64_pdf = base64.b64encode(st.session_state["pdf_bytes"]).decode()
    st.markdown(
        f"""<iframe src="data:application/pdf;base64,{b64_pdf}"
            width="100%" height="740px"
            style="border:none;border-radius:8px;box-shadow:0 2px 16px rgba(0,0,0,.12);">
        </iframe>""",
        unsafe_allow_html=True,
    )
    st.download_button(
        label="⬇️ Descargar PDF",
        data=st.session_state["pdf_bytes"],
        file_name=st.session_state["pdf_filename"],
        mime="application/pdf",
        use_container_width=True,
    )
else:
    st.info(
        "Completa los datos en el panel lateral y presiona "
        "**⚙️ Generar / Actualizar Vista Previa** para ver el resultado."
    )
