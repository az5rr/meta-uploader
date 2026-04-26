from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "runtime" / "generated_posts"
WIDTH = 1080
HEIGHT = 1350

ITEMS = [
    {
        "filename": "post1_fadhkuruni.png",
        "bg": "white",
        "fg": "black",
        "arabic": "فَاذْكُرُونِي أَذْكُرْكُمْ",
        "translation": "So remember Me; I will remember you.",
    },
    {
        "filename": "post2_rabbana.png",
        "bg": "black",
        "fg": "white",
        "arabic": "رَبَّنَا لَا تُزِغْ قُلُوبَنَا بَعْدَ إِذْ هَدَيْتَنَا وَهَبْ لَنَا مِنْ لَدُنْكَ رَحْمَةً ۚ إِنَّكَ أَنْتَ الْوَهَّابُ",
        "translation": "Our Lord, do not let our hearts deviate after You have guided us.",
    },
    {
        "filename": "post3_yusra.png",
        "bg": "white",
        "fg": "black",
        "arabic": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا",
        "translation": "Indeed, with hardship comes ease.",
    },
]


def shape_arabic(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def wrap_arabic(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        shaped = shape_arabic(candidate)
        bbox = draw.textbbox((0, 0), shaped, font=font, direction="rtl")
        if bbox[2] - bbox[0] <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def get_font_path() -> str:
    result = subprocess.check_output(
        ["fc-match", "-f", "%{file}\n", "DejaVu Sans"],
        text=True,
    ).strip()
    if not result:
        raise RuntimeError("Could not locate a system font")
    return result.splitlines()[0]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    font_path = get_font_path()

    for item in ITEMS:
        image = Image.new("RGB", (WIDTH, HEIGHT), item["bg"])
        draw = ImageDraw.Draw(image)

        arabic_font_size = 82 if len(item["arabic"]) < 40 else 60
        translation_font_size = 34
        arabic_font = ImageFont.truetype(font_path, arabic_font_size)
        translation_font = ImageFont.truetype(font_path, translation_font_size)

        lines = wrap_arabic(draw, item["arabic"], arabic_font, int(WIDTH * 0.78))
        shaped_lines = [shape_arabic(line) for line in lines]
        boxes = [draw.textbbox((0, 0), line, font=arabic_font, direction="rtl") for line in shaped_lines]
        heights = [box[3] - box[1] for box in boxes]

        translation_box = draw.textbbox((0, 0), item["translation"], font=translation_font)
        translation_height = translation_box[3] - translation_box[1]
        total_height = sum(heights) + (len(heights) - 1) * 24 + 60 + translation_height
        y = (HEIGHT - total_height) // 2 - 30

        for line, box, height in zip(shaped_lines, boxes, heights):
            line_width = box[2] - box[0]
            x = (WIDTH - line_width) // 2
            draw.text((x, y), line, fill=item["fg"], font=arabic_font, direction="rtl")
            y += height + 24

        y += 36
        translation_color = "#666666" if item["bg"] == "white" else "#bfbfbf"
        translation_width = translation_box[2] - translation_box[0]
        draw.text(((WIDTH - translation_width) // 2, y), item["translation"], fill=translation_color, font=translation_font)

        output = OUT_DIR / item["filename"]
        image.save(output, format="PNG")
        print(output)


if __name__ == "__main__":
    main()
