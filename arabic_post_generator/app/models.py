from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

from .config import DEFAULT_FONT_KEY, POST_HEIGHT, POST_WIDTH


@dataclass
class LayoutConfig:
    width: int = POST_WIDTH
    height: int = POST_HEIGHT
    background: str = "#EDE3D2"
    text_color: str = "#111111"
    font_key: str = DEFAULT_FONT_KEY
    font_size: int = 78
    line_height: float = 1.45
    outer_margin: int = 120
    text_align: str = "center"
    vertical_align: str = "middle"
    max_lines: int = 8
    category: str = "duaa"
    subtitle_font_size: int = 34
    subtitle_line_height: float = 1.35
    subtitle_text_color: str = "#6A6A6A"
    subtitle_gap: int = 36
    subtitle_max_width_ratio: float = 0.72
    subtitle_font_path: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    def to_dict(self):
        return asdict(self)


@dataclass
class PostDocument:
    title: str
    category: str
    source_text: str
    mode: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    layout: dict | None = None
    approved: bool = False
    image_path: str | None = None
    caption_text: str | None = None

    def to_dict(self):
        payload = asdict(self)
        payload["layout"] = self.layout or {}
        return payload
