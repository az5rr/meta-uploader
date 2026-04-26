from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .config import CONTENT_DIR, OUTPUTS_DIR
from .models import LayoutConfig, PostDocument
from .renderer import render_post


def slugify(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in text.strip().lower())
    compact = "_".join(segment for segment in cleaned.split("_") if segment)
    return compact[:48] or "post"


def save_source_text(document: PostDocument) -> Path:
    category_dir = CONTENT_DIR / document.category / datetime.utcnow().strftime("%Y-%m-%d")
    category_dir.mkdir(parents=True, exist_ok=True)
    path = category_dir / f"{document.title}.json"
    path.write_text(json.dumps(document.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _existing_metadata_files(category: str):
    yield from CONTENT_DIR.glob(f"{category}/**/*.json")
    yield from OUTPUTS_DIR.glob(f"{category}/**/*.json")


def find_duplicate_source_text(source_text: str, category: str) -> Path | None:
    for path in _existing_metadata_files(category):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("source_text") == source_text:
            return path
    return None


def build_document(source_text: str, category: str, mode: str, title: str | None = None) -> PostDocument:
    return PostDocument(
        title=title or slugify(source_text[:32]),
        category=category,
        source_text=source_text,
        mode=mode,
    )


def generate_document(document: PostDocument, layout: LayoutConfig, allow_repeat: bool = False) -> dict:
    duplicate = find_duplicate_source_text(document.source_text, document.category)
    if duplicate and not allow_repeat:
        raise ValueError(
            f"Duplicate {document.category} text detected. Existing source already saved at: {duplicate}"
        )
    save_source_text(document)
    out_dir = OUTPUTS_DIR / document.category / datetime.utcnow().strftime("%Y-%m-%d")
    result = render_post(document, layout, out_dir)
    return result


def batch_generate(texts: Iterable[str], category: str, layout: LayoutConfig, allow_repeat: bool = False) -> list[dict]:
    results = []
    for index, text in enumerate(texts, start=1):
        title = f"{category}_{index:02d}"
        document = build_document(text, category=category, mode="batch", title=title)
        results.append(generate_document(document, layout, allow_repeat=allow_repeat))
    return results
