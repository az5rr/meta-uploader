from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import freetype
import uharfbuzz as hb
from PIL import Image, ImageColor, ImageDraw, ImageFont

from .fonts import FontSpec, resolve_font
from .models import LayoutConfig, PostDocument


RTL_DIRECTION = "rtl"


@dataclass
class GlyphPlacement:
    glyph_id: int
    x_offset: float
    y_offset: float
    x_advance: float
    y_advance: float
    cluster: int


@dataclass
class LineLayout:
    text: str
    glyphs: list[GlyphPlacement]
    width: float
    ascent: float
    descent: float


def validate_text_integrity(source_text: str, rendered_text: str) -> dict:
    if source_text != rendered_text:
        raise ValueError("Rendered text does not exactly match the stored source text.")

    source_tashkeel = sum(1 for ch in source_text if unicodedata.combining(ch))
    rendered_tashkeel = sum(1 for ch in rendered_text if unicodedata.combining(ch))
    if source_tashkeel != rendered_tashkeel:
        raise ValueError("Tashkeel count mismatch detected.")

    arabic_letters = [ch for ch in source_text if "\u0600" <= ch <= "\u06FF"]
    if not arabic_letters:
        raise ValueError("Arabic source text is empty.")

    return {
        "exact_match": True,
        "tashkeel_count": source_tashkeel,
        "arabic_characters": len(arabic_letters),
    }


def _load_font_bytes(font: FontSpec) -> bytes:
    return font.path.read_bytes()


def _shape_text(face: freetype.Face, font_bytes: bytes, text: str) -> list[GlyphPlacement]:
    hb_face = hb.Face(font_bytes)
    hb_font = hb.Font(hb_face)
    hb_font.scale = (face.size.x_ppem * 64, face.size.y_ppem * 64)
    hb.ot_font_set_funcs(hb_font)

    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.direction = RTL_DIRECTION
    buffer.script = "arab"
    buffer.language = "ar"
    hb.shape(hb_font, buffer)

    infos = buffer.glyph_infos
    positions = buffer.glyph_positions
    glyphs: list[GlyphPlacement] = []
    for info, pos in zip(infos, positions):
        glyphs.append(
            GlyphPlacement(
                glyph_id=info.codepoint,
                x_offset=pos.x_offset / 64.0,
                y_offset=pos.y_offset / 64.0,
                x_advance=pos.x_advance / 64.0,
                y_advance=pos.y_advance / 64.0,
                cluster=info.cluster,
            )
        )
    return glyphs


def _measure_line(face: freetype.Face, glyphs: list[GlyphPlacement]) -> tuple[float, float, float]:
    width = 0.0
    max_ascent = 0.0
    max_descent = 0.0
    pen_x = 0.0
    for glyph in glyphs:
        face.load_glyph(glyph.glyph_id, freetype.FT_LOAD_RENDER)
        slot = face.glyph
        bitmap_top = float(slot.bitmap_top)
        rows = float(slot.bitmap.rows)
        ascent = bitmap_top - glyph.y_offset
        descent = max(0.0, rows - bitmap_top + glyph.y_offset)
        max_ascent = max(max_ascent, ascent)
        max_descent = max(max_descent, descent)
        pen_x += glyph.x_advance
        width = max(width, pen_x)
    return width, max_ascent, max_descent


def _split_words(text: str) -> list[str]:
    return [word for word in text.split() if word]


def _fit_lines(face: freetype.Face, font_bytes: bytes, text: str, max_width: float, max_lines: int) -> list[LineLayout]:
    words = _split_words(text)
    if not words:
        return []

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        glyphs = _shape_text(face, font_bytes, candidate)
        width, ascent, descent = _measure_line(face, glyphs)
        if width <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)

    if len(lines) > max_lines:
        raise ValueError("Text exceeds maximum line count for the chosen layout.")

    layouts: list[LineLayout] = []
    for line in lines:
        glyphs = _shape_text(face, font_bytes, line)
        width, ascent, descent = _measure_line(face, glyphs)
        layouts.append(LineLayout(text=line, glyphs=glyphs, width=width, ascent=ascent, descent=descent))
    return layouts


def _draw_glyph_line(image: Image.Image, face: freetype.Face, line: LineLayout, x: float, baseline_y: float, text_rgb):
    alpha = Image.new("L", image.size, 0)
    pen_x = x
    for glyph in line.glyphs:
        face.load_glyph(glyph.glyph_id, freetype.FT_LOAD_RENDER)
        bitmap = face.glyph.bitmap
        if bitmap.width and bitmap.rows:
            glyph_image = Image.frombytes("L", (bitmap.width, bitmap.rows), bytes(bitmap.buffer))
            draw_x = pen_x + glyph.x_offset + face.glyph.bitmap_left
            draw_y = baseline_y - face.glyph.bitmap_top - glyph.y_offset
            alpha.paste(glyph_image, (round(draw_x), round(draw_y)), glyph_image)
        pen_x += glyph.x_advance
    fill = Image.new("RGBA", image.size, text_rgb + (0,))
    fill.putalpha(alpha)
    image.alpha_composite(fill)


def _wrap_subtitle(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
    words = [word for word in text.split() if word]
    if not words:
        return []
    lines = [words[0]]
    for word in words[1:]:
        candidate = f"{lines[-1]} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def render_post(document: PostDocument, layout: LayoutConfig, output_dir: Path) -> dict:
    font = resolve_font(layout.font_key)
    font_bytes = _load_font_bytes(font)
    face = freetype.Face(str(font.path))
    face.set_char_size(layout.font_size * 64)

    validation = validate_text_integrity(document.source_text, document.source_text)
    max_width = layout.width - (layout.outer_margin * 2)
    lines = _fit_lines(face, font_bytes, document.source_text, max_width=max_width, max_lines=layout.max_lines)

    line_box_heights = [line.ascent + line.descent for line in lines]
    total_height = sum(line_box_heights) + (len(lines) - 1) * (layout.font_size * (layout.line_height - 1))

    background_rgb = ImageColor.getrgb(layout.background)
    text_rgb = ImageColor.getrgb(layout.text_color)
    image = Image.new("RGBA", (layout.width, layout.height), background_rgb + (255,))
    draw = ImageDraw.Draw(image)

    subtitle_lines: list[str] = []
    subtitle_font = None
    subtitle_line_box = 0.0
    subtitle_total_height = 0.0
    if document.caption_text:
        subtitle_font = ImageFont.truetype(layout.subtitle_font_path, layout.subtitle_font_size)
        subtitle_max_width = layout.width * layout.subtitle_max_width_ratio
        subtitle_lines = _wrap_subtitle(draw, document.caption_text.strip(), subtitle_font, subtitle_max_width)
        subtitle_line_box = layout.subtitle_font_size * layout.subtitle_line_height
        subtitle_total_height = len(subtitle_lines) * subtitle_line_box

    combined_height = total_height
    if subtitle_lines:
        combined_height += layout.subtitle_gap + subtitle_total_height
    start_y = (layout.height - combined_height) / 2

    cursor_y = start_y
    for index, line in enumerate(lines):
        baseline_y = cursor_y + line.ascent
        draw_x = (layout.width - line.width) / 2
        _draw_glyph_line(image, face, line, draw_x, baseline_y, text_rgb)
        cursor_y += line_box_heights[index] + (layout.font_size * (layout.line_height - 1))

    if subtitle_lines and subtitle_font is not None:
        cursor_y += layout.subtitle_gap
        subtitle_rgb = ImageColor.getrgb(layout.subtitle_text_color)
        for line in subtitle_lines:
            text_width = draw.textlength(line, font=subtitle_font)
            draw.text(
                ((layout.width - text_width) / 2, cursor_y),
                line,
                fill=subtitle_rgb,
                font=subtitle_font,
            )
            cursor_y += subtitle_line_box

    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / f"{document.title}.png"
    image.save(png_path)

    metadata = document.to_dict()
    metadata["layout"] = layout.to_dict()
    metadata["validation"] = validation
    metadata["line_count"] = len(lines)
    metadata["font_path"] = str(font.path)
    metadata["image_path"] = str(png_path)
    metadata_path = output_dir / f"{document.title}.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "image_path": str(png_path),
        "metadata_path": str(metadata_path),
        "validation": validation,
        "line_count": len(lines),
    }
