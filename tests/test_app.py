from datetime import date

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from lch_app.server import app
from processor.pipeline import ProcessOptions, generate_document
from processor.schedule import parse_schedule


client = TestClient(app)


def test_home_renders_brand():
    response = client.get("/")
    assert response.status_code == 200
    assert "Generador de Planillas LCH" in response.text
    assert "Día de la jornada" in response.text


def test_generate_ejemplo_without_index():
    schedule = """
Hombres:

Cancha 1
11:30: Mambo F.C. vs Echale Pesteke
"""
    response = client.post(
        "/api/generate",
        data={
            "schedule": schedule,
            "source": "ejemplo",
            "sort": "category",
            "index": "0",
            "blanks": "1",
            "date": "2026-09-19",
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content[:4] == b"%PDF"


def test_direct_generate_has_saturday_and_no_footer():
    from pathlib import Path

    schedule = Path("public/horario-jornada.txt").read_text(encoding="utf-8")
    ejemplo = Path("public/planillas-ejemplo.pdf")
    if not ejemplo.exists():
        pytest.skip("falta el PDF de ejemplo")
    pdf_out, summary = generate_document(
        ejemplo.read_bytes(),
        schedule,
        ProcessOptions(include_index=False, match_date=date(2026, 9, 19)),
    )
    assert summary["matchDate"] == "19 / 09 / 2026"
    import pymupdf as fitz

    doc = fitz.open(stream=pdf_out, filetype="pdf")
    first = doc[0].get_text("text")
    assert "Planillas de cancha" not in first
    assert "Cancha 1   ·   11:30" not in first
    parsed = parse_schedule(schedule)
    assert len(parsed.matches) == 46
    doc.close()
