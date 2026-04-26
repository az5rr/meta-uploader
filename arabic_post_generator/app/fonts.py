from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import DEFAULT_FONT_KEY, FONT_FALLBACK_ORDER, FONTS_DIR


@dataclass(frozen=True)
class FontSpec:
    key: str
    family: str
    path: Path


FONT_CANDIDATES = {
    "amiri": [
        FONTS_DIR / "Amiri-Regular.ttf",
        FONTS_DIR / "amiri-1.003" / "Amiri-Regular.ttf",
        FONTS_DIR / "amiri" / "Amiri-Regular.ttf",
    ],
    "noto_naskh": [
        FONTS_DIR / "NotoNaskhArabic-Regular.ttf",
    ],
    "scheherazade": [
        FONTS_DIR / "ScheherazadeNew-Regular.ttf",
        FONTS_DIR / "scheherazade" / "ScheherazadeNew-Regular.ttf",
        FONTS_DIR / "ScheherazadeNew" / "ScheherazadeNew-Regular.ttf",
    ],
}


def available_fonts() -> list[FontSpec]:
    discovered: dict[str, FontSpec] = {}
    for key, candidates in FONT_CANDIDATES.items():
        for candidate in candidates:
            if candidate.exists():
                discovered[key] = FontSpec(key=key, family=key.replace("_", " "), path=candidate)
                break
    return [discovered[key] for key in FONT_FALLBACK_ORDER if key in discovered]


def resolve_font(key: str | None = None) -> FontSpec:
    fonts = available_fonts()
    if not fonts:
        raise RuntimeError("No supported Arabic fonts found in the local fonts directory.")

    requested = key or DEFAULT_FONT_KEY
    if requested:
        for font in fonts:
            if font.key == requested:
                return font
        raise RuntimeError(f"Requested font '{requested}' is not available.")
    return fonts[0]
