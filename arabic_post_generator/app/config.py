from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
CONTENT_DIR = BASE_DIR / "content"
OUTPUTS_DIR = BASE_DIR / "outputs"
FONTS_DIR = BASE_DIR / "fonts"
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

for directory in (CONTENT_DIR, OUTPUTS_DIR, FONTS_DIR, STATIC_DIR, TEMPLATES_DIR):
    directory.mkdir(parents=True, exist_ok=True)


DEFAULT_TEXT = (
    "اللَّهُمَّ أَحْسِنْ عَاقِبَتَنَا فِي الْأُمُورِ كُلِّهَا، "
    "وَأَجِرْنَا مِنْ خِزْيِ الدُّنْيَا وَعَذَابِ الْآخِرَةِ"
)

DEFAULT_FONT_KEY = "amiri"
FONT_FALLBACK_ORDER = ["amiri", "noto_naskh", "scheherazade"]
POST_WIDTH = 1080
POST_HEIGHT = 1080
