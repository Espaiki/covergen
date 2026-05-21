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

load_dotenv()  # carga .env antes de cualquier os.getenv()

from covergen.context import generate_layout_context
from covergen.exporter import build_filename
from covergen.formats import FormatProfile
from covergen.generator import generate_cover_with_controlnet
from covergen.models import CoverData
from covergen.renderer import TemplateRenderer

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

_IMG_EXTS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})

# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_b64(raw: bytes) -> str:
    """Encode image bytes to raw base64 (no data-URI prefix)."""
    return base64.b64encode(raw).decode()


def _file_hash(raw: bytes) -> str:
    """MD5 hash of file bytes — used to detect when the sketch changes."""
    return hashlib.md5(raw).hexdigest()


def _scan_presets() -> dict[str, Path]:
    """Return {filename: Path} for all images in ASSETS_DIR."""
    if not ASSETS_DIR.is_dir():
        return {}
    return {
        p.name: p
        for p in sorted(ASSETS_DIR.iterdir())
        if p.suffix.lower() in _IMG_EXTS
    }


def _check_replicate_token() -> str | None:
    """Return the token if set, or None if missing."""
    return os.getenv("REPLICATE_API_TOKEN", "").strip() or None


# ── Session state ─────────────────────────────────────────────────────────────
_STATE_DEFAULTS: dict[str, object] = {
    "pdf_bytes":             None,
    "pdf_filename":          "caratula.pdf",
    "controlnet_bg_b64":     None,   # b64 del fondo generado por ControlNet
    "controlnet_sketch_hash": None,  # hash del boceto usado en la última generación
}
for _k, _v in _STATE_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎨 CoverGen")
    st.caption("Generador de Carátulas · ControlNet Edition")
    st.divider()

    # ── Datos del documento ──────────────────────────────────────────────────
    st.subheader("Datos del Documento")
    institution = st.text_input(
        "Institución",
        value="Universidad Técnica Particular de Loja",
        placeholder="Nombre de la institución",
    )
    subject = st.text_input(
        "Materia / Asignatura",
        value="Análisis de Redes",
        placeholder="Nombre de la materia",
    )
    teacher = st.text_input(
        "Docente",
        value="Dr. Carlos Mendoza",
        placeholder="Prof. / Dr. / Ing. Apellido",
    )
    student = st.text_input(
        "Estudiante",
        value="Adrian Valarezo",
        placeholder="Nombre completo",
    )
    grade = st.text_input(
        "Curso / Paralelo",
        value="Tercer Ciclo - Paralelo A",
        placeholder="Ej: Primer Año — Paralelo B",
    )
    year = st.text_input(
        "Año Lectivo",
        value="2026-2027",
        placeholder="YYYY-YYYY",
        max_chars=9,
    )

    st.divider()

    # ── Configuración ────────────────────────────────────────────────────────
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
        index=1,
        horizontal=True,
    )

    st.divider()

    # ── Boceto Guía (ControlNet input) ───────────────────────────────────────
    st.subheader("Boceto Guía")
    st.caption(
        "Sube un boceto dibujado a mano (PNG/JPG). "
        "ControlNet lo usará como guía espacial para generar el arte final."
    )
    sketch_file = st.file_uploader(
        "Subir boceto",
        type=["png", "jpg", "jpeg"],
        key="sketch_uploader",
        help="El boceto define la composición; ControlNet añade el estilo y el color.",
    )

    # Estado del boceto cargado
    if sketch_file is not None:
        st.image(sketch_file, caption="Boceto cargado", use_container_width=True)
        sketch_file.seek(0)  # reset para lectura posterior
    elif st.session_state["controlnet_bg_b64"]:
        st.info("Fondo ControlNet en caché. Sube un nuevo boceto para regenerarlo.")

    st.divider()

    # ── Fondo alternativo (sin boceto) ───────────────────────────────────────
    st.subheader("Fondo Alternativo")
    st.caption("Se usa si no hay boceto cargado o fondo IA activo.")

    manual_upload = st.file_uploader(
        "Subir imagen de fondo",
        type=["png", "jpg", "jpeg"],
        key="bg_uploader",
        help="Imagen PNG/JPG que se usa como fondo directo (sin ControlNet).",
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
        type="primary",
        use_container_width=True,
    )

# ── Área principal ────────────────────────────────────────────────────────────
st.title("Vista Previa de Carátula")

# Comprobación de token Replicate — aviso no bloqueante en la zona principal
replicate_token = _check_replicate_token()
if replicate_token is None:
    st.warning(
        "**REPLICATE_API_TOKEN no configurado.** "
        "Añade `REPLICATE_API_TOKEN=r8_...` a tu archivo `.env` y reinicia la app. "
        "Sin él, el boceto no será procesado por ControlNet "
        "(puedes seguir generando carátulas con fondo manual o degradado CSS).",
        icon="⚠️",
    )

if generate_btn:

    # ── Paso 1: resolver fondo ─────────────────────────────────────────────
    bg_b64: str | None = None

    if sketch_file is not None and replicate_token:
        sketch_bytes = sketch_file.read()
        current_hash = _file_hash(sketch_bytes)

        cached_same = (
            st.session_state["controlnet_bg_b64"] is not None
            and st.session_state["controlnet_sketch_hash"] == current_hash
        )

        if cached_same:
            # Mismo boceto que la última vez → reutiliza el resultado
            bg_b64 = st.session_state["controlnet_bg_b64"]
            st.info("Reutilizando fondo ControlNet en caché (boceto sin cambios).")
        else:
            # Boceto nuevo → llamada a Replicate ControlNet
            with st.spinner(
                f"Generando arte con ControlNet para «{subject}»… (~30 seg.)"
            ):
                try:
                    img_bytes = generate_cover_with_controlnet(sketch_bytes, subject)
                    bg_b64 = _to_b64(img_bytes)

                    # Persiste en session_state
                    st.session_state["controlnet_bg_b64"]      = bg_b64
                    st.session_state["controlnet_sketch_hash"] = current_hash

                    # Guarda también en assets/ para referencia
                    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
                    (ASSETS_DIR / "controlnet_result.png").write_bytes(img_bytes)

                    st.success("Arte generado con ControlNet.")

                except EnvironmentError as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Error en ControlNet: {exc}")

    elif st.session_state["controlnet_bg_b64"] and sketch_file is None:
        # No hay boceto nuevo pero hay uno cacheado → lo mantiene
        bg_b64 = st.session_state["controlnet_bg_b64"]

    elif manual_upload is not None:
        bg_b64 = _to_b64(manual_upload.read())
        st.session_state["controlnet_bg_b64"] = None  # upload manual borra caché IA

    elif selected_preset != preset_options[0]:
        bg_b64 = _to_b64(presets[selected_preset].read_bytes())

    # ── Paso 2: compilar PDF ───────────────────────────────────────────────
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
                cover,
                selected_format,
                background_image_b64=bg_b64,
                educational_level=nivel_educativo,
            )
            renderer = TemplateRenderer()
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
        f"""<iframe
            src="data:application/pdf;base64,{b64_pdf}"
            width="100%"
            height="740px"
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
        "Sube un boceto en el panel lateral y presiona "
        "**⚙️ Generar / Actualizar Vista Previa** para ver el resultado."
    )
