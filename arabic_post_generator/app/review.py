from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import DEFAULT_FONT_KEY, DEFAULT_TEXT, OUTPUTS_DIR, POST_HEIGHT, POST_WIDTH, STATIC_DIR, TEMPLATES_DIR
from .models import LayoutConfig
from .workflow import build_document, generate_document


app = FastAPI(title="Arabic Post Review")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/generated", StaticFiles(directory=str(OUTPUTS_DIR)), name="generated")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def latest_outputs() -> list[dict]:
    items = []
    for metadata in sorted(OUTPUTS_DIR.glob("*/*/*.json"), reverse=True):
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        payload["metadata_path"] = str(metadata)
        items.append(payload)
    return items[:20]


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "items": latest_outputs(), "default_text": DEFAULT_TEXT, "error": None},
    )


@app.post("/generate")
def generate(
    request: Request,
    text: str = Form(...),
    category: str = Form("duaa"),
    font: str = Form(DEFAULT_FONT_KEY),
    size: int = Form(78),
    allow_repeat: bool = Form(False),
):
    layout = LayoutConfig(
        width=POST_WIDTH,
        height=POST_HEIGHT,
        background="#EDE3D2",
        text_color="#111111",
        font_key=font,
        font_size=size,
        category=category,
    )
    document = build_document(text, category=category, mode="manual")
    try:
        generate_document(document, layout, allow_repeat=allow_repeat)
    except ValueError as exc:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "items": latest_outputs(),
                "default_text": text,
                "error": str(exc),
            },
            status_code=409,
        )
    return RedirectResponse("/", status_code=303)


@app.post("/approve")
def approve(metadata_path: str = Form(...)):
    path = Path(metadata_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Metadata file not found.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["approved"] = True
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return RedirectResponse("/", status_code=303)
