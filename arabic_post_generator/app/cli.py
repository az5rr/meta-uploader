from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import DEFAULT_FONT_KEY, DEFAULT_TEXT, POST_HEIGHT, POST_WIDTH
from .models import LayoutConfig
from .workflow import batch_generate, build_document, generate_document


def _base_parser(name: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=name)
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--font", default=DEFAULT_FONT_KEY)
    parser.add_argument("--size", type=int, default=78)
    parser.add_argument("--category", default="duaa")
    parser.add_argument("--title")
    parser.add_argument("--allow-repeat", action="store_true")
    return parser


def _layout_from_args(args) -> LayoutConfig:
    return LayoutConfig(
        width=POST_WIDTH,
        height=POST_HEIGHT,
        background="#EDE3D2",
        text_color="#111111",
        font_key=args.font,
        font_size=args.size,
        line_height=1.45,
        outer_margin=120,
        category=args.category,
    )


def generate_duaa_post():
    args = _base_parser("generate_duaa_post").parse_args()
    layout = _layout_from_args(args)
    document = build_document(args.text, category=args.category, mode="manual", title=args.title)
    print(json.dumps(generate_document(document, layout, allow_repeat=args.allow_repeat), ensure_ascii=False, indent=2))


def generate_azkar_post():
    parser = _base_parser("generate_azkar_post")
    parser.set_defaults(category="azkar")
    args = parser.parse_args()
    layout = _layout_from_args(args)
    document = build_document(args.text, category=args.category, mode="manual", title=args.title)
    print(json.dumps(generate_document(document, layout, allow_repeat=args.allow_repeat), ensure_ascii=False, indent=2))


def generate_batch_posts():
    parser = argparse.ArgumentParser(prog="generate_batch_posts")
    parser.add_argument("--input", required=True)
    parser.add_argument("--font", default=DEFAULT_FONT_KEY)
    parser.add_argument("--size", type=int, default=78)
    parser.add_argument("--category", default="duaa")
    parser.add_argument("--allow-repeat", action="store_true")
    args = parser.parse_args()

    texts = [
        line.strip()
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    layout = _layout_from_args(args)
    print(
        json.dumps(
            batch_generate(texts, category=args.category, layout=layout, allow_repeat=args.allow_repeat),
            ensure_ascii=False,
            indent=2,
        )
    )
