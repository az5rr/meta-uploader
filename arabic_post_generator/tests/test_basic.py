from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import LayoutConfig
from app.workflow import build_document, find_duplicate_source_text, generate_document
from app.renderer import validate_text_integrity


def test_integrity_preserves_exact_text():
    text = "اللَّهُمَّ أَحْسِنْ عَاقِبَتَنَا"
    result = validate_text_integrity(text, text)
    assert result["exact_match"] is True
    assert result["tashkeel_count"] > 0


def test_document_build():
    doc = build_document("نَصٌّ عَرَبِيٌّ", category="duaa", mode="manual")
    assert doc.category == "duaa"
    assert doc.mode == "manual"


def test_duplicate_duaa_blocked(tmp_path, monkeypatch):
    from app import workflow

    monkeypatch.setattr(workflow, "CONTENT_DIR", tmp_path / "content")
    monkeypatch.setattr(workflow, "OUTPUTS_DIR", tmp_path / "outputs")
    workflow.CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    workflow.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    text = "اللَّهُمَّ اغْفِرْ لَنَا"
    doc = build_document(text, category="duaa", mode="manual", title="one")
    layout = LayoutConfig()
    generate_document(doc, layout, allow_repeat=True)

    duplicate = find_duplicate_source_text(text, "duaa")
    assert duplicate is not None

    second = build_document(text, category="duaa", mode="manual", title="two")
    try:
        generate_document(second, layout)
        assert False, "Expected duplicate duaa rejection"
    except ValueError as exc:
        assert "Duplicate duaa text detected" in str(exc)
