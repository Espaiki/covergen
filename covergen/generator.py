"""ControlNet image generation pipeline via Replicate API.

Usage:
    from covergen.generator import generate_cover_with_controlnet
    img_bytes = generate_cover_with_controlnet(sketch_bytes, subject="Matemática")
"""
from __future__ import annotations

import io
import os

import requests as _req

# ── Subject → visual-element mapping for rich ControlNet prompts ─────────────
# Each entry: frozenset of lowercase keywords → description of matching visuals.
_SUBJECT_VISUAL_MAP: list[tuple[frozenset[str], str]] = [
    (frozenset({"matemática", "matematica", "calculo", "cálculo", "álgebra", "algebra",
                "geometría", "geometria", "estadística", "estadistica", "trigonometría"}),
     "rulers, compasses, protractors, colorful geometric shapes (triangles, circles, cubes), "
     "number decorations, coordinate axes, graphs"),

    (frozenset({"lengua", "literatura", "lenguaje", "español", "comunicación",
                "comunicacion", "redacción", "lectura"}),
     "open books, quill pens, ink bottles, speech bubbles, fairy tale characters, "
     "colorful alphabet letters, story scrolls"),

    (frozenset({"biología", "biologia", "naturales", "ecología", "ecologia",
                "botánica", "botanica", "zoología", "zoologia"}),
     "colorful flowers and leaves, butterflies, DNA double helix, microscope, "
     "animal illustrations, cells, trees and nature elements"),

    (frozenset({"química", "quimica", "ciencias"}),
     "colorful test tubes, beakers with bubbling liquid, atoms, colorful molecules, "
     "periodic table motifs, laboratory equipment, flasks"),

    (frozenset({"física", "fisica", "óptica", "optica", "mecánica", "mecanica",
                "electromagnetismo", "termodinámica"}),
     "planets, atomic orbits, colorful energy waves, magnets, gears, "
     "lightning bolts, pendulums, prisms"),

    (frozenset({"historia", "sociales", "cívica", "civica", "geografía", "geografia",
                "ciudadanía", "ciudadania"}),
     "antique maps, globes, compass roses, colorful flags, ancient artifacts, "
     "historical buildings, hourglasses, scrolls"),

    (frozenset({"arte", "dibujo", "pintura", "plástica", "plastica", "visual"}),
     "paintbrushes, color palettes, easels, colorful paint splatters, "
     "watercolor effects, sculpting tools, rainbow art supplies"),

    (frozenset({"música", "musica", "musical", "canto", "solfeo"}),
     "colorful musical notes, treble clefs, guitars, pianos, trumpets, "
     "sound waves, headphones, sheet music decorations"),

    (frozenset({"computación", "computacion", "tecnología", "tecnologia", "informática",
                "informatica", "redes", "programación", "programacion", "sistemas",
                "digital"}),
     "computers, circuit board patterns, colorful gears and cogs, code symbols, "
     "Wi-Fi icons, robots, digital art elements"),

    (frozenset({"inglés", "ingles", "english", "idiomas", "francés", "frances",
                "alemán", "aleman", "portugués", "portugues"}),
     "colorful country flags, speech bubbles, open dictionaries, world maps, airplanes"),

    (frozenset({"educación física", "educacion fisica", "deporte", "deportes", "gimnasia"}),
     "colorful sports balls, athletic equipment, trophies, medals, running shoes"),

    (frozenset({"religión", "religion", "ética", "etica", "valores", "moral",
                "filosofía", "filosofia"}),
     "colorful doves, glowing hearts, stars, flowers, rainbow elements, light rays"),
]

# Replicate model — jagilley/controlnet-scribble (SD 1.5, optimised for hand-drawn input).
# Swap the version hash below to test other ControlNet flavours (Canny, Lineart, SDXL…).
_CONTROLNET_MODEL = (
    "jagilley/controlnet-scribble"
    ":435061a1b5a4c1e26740464bf786efdfa9cb3a3ac488595a2de23e143fdb0117"
)


def _get_subject_visuals(subject: str) -> str:
    """Return subject-specific decorative elements for the prompt."""
    sl = subject.lower()
    for keywords, visuals in _SUBJECT_VISUAL_MAP:
        if any(kw in sl for kw in keywords):
            return visuals
    return (
        "school supplies (colorful pencils, rulers, erasers, markers, books), "
        "stars, hearts, colorful doodles and playful shapes"
    )


def _build_controlnet_prompt(subject: str) -> str:
    """Build a rich, subject-aware ControlNet prompt."""
    visuals = _get_subject_visuals(subject)
    return (
        f"A high-quality, vibrant, vector-style digital illustration for a school "
        f"notebook cover, subject: {subject}. "
        f"Theme elements: {visuals}. "
        f"Style: polished cartoon vector art, bright digital illustration, "
        f"decorative illustrated border along all page edges, "
        f"clean lines, highly detailed, colorful, cheerful. "
        f"No text, no letters, no numbers anywhere in the image."
    )


def generate_cover_with_controlnet(
    sketch_bytes: bytes,
    subject: str,
) -> bytes:
    """Transform a hand-drawn sketch into a vibrant cover background via Replicate ControlNet.

    Reads REPLICATE_API_TOKEN from the environment (loaded from .env by the caller).

    Args:
        sketch_bytes: Raw bytes of the guide/sketch image (PNG or JPEG).
        subject:      Subject/materia name — used to personalise the prompt.

    Returns:
        Raw PNG bytes of the generated illustration.

    Raises:
        EnvironmentError: If REPLICATE_API_TOKEN is not set.
        RuntimeError:     If Replicate returns an unexpected output format.
    """
    token = os.getenv("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise EnvironmentError(
            "REPLICATE_API_TOKEN no encontrado en el entorno. "
            "Añade REPLICATE_API_TOKEN=r8_... a tu archivo .env y reinicia la app."
        )

    import replicate as _rep  # lazy — only imported when actually used

    # Set token explicitly so the client picks it up even if env was set after import.
    os.environ["REPLICATE_API_TOKEN"] = token

    prompt = _build_controlnet_prompt(subject)

    # Wrap bytes in a named BytesIO — Replicate SDK uses the name to infer MIME type.
    sketch_io = io.BytesIO(sketch_bytes)
    sketch_io.name = "sketch.png"

    output = _rep.run(
        _CONTROLNET_MODEL,
        input={
            "image": sketch_io,
            "prompt": prompt,
            "negative_prompt": (
                "text, watermark, signature, words, letters, numbers, "
                "low quality, blurry, distorted, ugly, dark"
            ),
            "a_prompt": "best quality, extremely detailed, vibrant colors",
            "num_samples": "1",
            "image_resolution": "512",
            "detect_resolution": 512,
            "ddim_steps": 25,
            "scale": 9,          # guidance scale — higher = closer to prompt
            "seed": -1,
        },
    )

    # Handle both modern FileOutput objects and legacy URL strings.
    items = list(output) if hasattr(output, "__iter__") and not isinstance(output, (str, bytes)) else [output]
    if not items:
        raise RuntimeError("Replicate devolvió una respuesta vacía.")

    first = items[0]

    # FileOutput (Replicate SDK >= 0.29)
    try:
        return bytes(first.read())
    except AttributeError:
        pass

    # URL string (Replicate SDK < 0.29 or direct string output)
    url = str(first)
    resp = _req.get(url, timeout=90)
    resp.raise_for_status()
    return resp.content
