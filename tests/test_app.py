from datetime import date

import pymupdf as fitz
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
    assert "Descargar PDF" in response.text
    assert "Suspendidos" in response.text
    assert 'name="players"' in response.text
    assert "Ezequiel Guzman (Mimetizarte)" in response.text
    assert "Jugadores a marcar" not in response.text
    assert "Completar faltantes" not in response.text
    assert "Ejemplo de prueba" not in response.text
    assert "Descargar ejemplo" not in response.text
    assert "Equipos Libres" in response.text
    assert "Sin suspender" in response.text
    assert "Jugador:" in response.text
    assert "Equipos fuera de la jornada" not in response.text
    assert "Filas en celeste" not in response.text
    assert "No están en la planilla" not in response.text
    assert "application/json" in response.text
    assert "No pude hablar con el generador" in response.text
    assert "new FormData(form)" not in response.text


def test_health_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_analyze_accepts_json_and_cors():
    schedule = """
Hombres:

Cancha 1
11:30: Mambo F.C. vs Echale Pesteke
"""
    response = client.post(
        "/api/analyze",
        json={"schedule": schedule, "source": "ejemplo", "players": "Ezequiel Guzman (Mimetizarte)"},
        headers={"Origin": "http://localhost:3000", "Accept": "application/json"},
    )
    assert response.status_code == 200, response.text
    assert response.headers.get("access-control-allow-origin") == "*"
    payload = response.json()
    assert payload["ok"] is True
    assert payload["playerMarks"]


def test_generate_accepts_json():
    schedule = """
Hombres:

Cancha 1
11:30: Mambo F.C. vs Echale Pesteke
"""
    response = client.post(
        "/api/generate",
        json={
            "schedule": schedule,
            "source": "ejemplo",
            "sort": "category",
            "date": "2026-09-19",
        },
        headers={"Accept": "application/json", "Origin": "http://127.0.0.1:4173"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ok"] is True
    assert payload["downloadUrl"] == "/api/output/planillas-cancha.pdf"
    assert response.headers.get("access-control-allow-origin") == "*"


def test_cors_preflight_generate():
    response = client.options(
        "/api/generate",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,accept",
        },
    )
    assert response.status_code in {200, 204}
    assert response.headers.get("access-control-allow-origin") == "*"


def test_analyze_ignores_empty_pdf_file():
    schedule = """
Hombres:

Cancha 1
11:30: Mambo F.C. vs Echale Pesteke
"""
    response = client.post(
        "/api/analyze",
        data={"schedule": schedule, "source": "ejemplo"},
        files={"pdf": ("", b"", "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True


def test_analyze_returns_compact_json():
    schedule = """
Hombres:

Cancha 1
11:30: Mambo F.C. vs Echale Pesteke
"""
    response = client.post(
        "/api/analyze",
        data={"schedule": schedule, "source": "ejemplo"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ok"] is True
    assert "keptPages" not in payload
    assert "removedPages" not in payload
    assert isinstance(payload["removedTeams"], list)


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
    payload = response.json()
    assert payload["ok"] is True
    assert payload["downloadUrl"] == "/api/output/planillas-cancha.pdf"
    download = client.get(payload["downloadUrl"])
    assert download.status_code == 200
    assert download.content[:4] == b"%PDF"


def test_generate_marks_player_and_warns_when_missing():
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((40, 40), "PLANILLA DE CANCHA", fontsize=16)
    page.insert_text((40, 62), "Liga: Hombres C  |  Club: Mimetizarte", fontsize=10)
    page.insert_text((65.25, 156), "Agustín Ferreyra", fontsize=10)
    pdf = document.tobytes()
    document.close()
    schedule = """
Hombres:

Cancha 1
13:00: As Broma vs Mimetizarte
"""
    response = client.post(
        "/api/generate",
        data={
            "schedule": schedule,
            "source": "upload",
            "sort": "category",
            "date": "2026-09-19",
            "players": "Agustin Ferreyra (Mimetizarte)\nEzequiel Guzman (Mimetizarte)",
        },
        files={"pdf": ("planilla.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    marks = {item["name"]: item for item in payload["playerMarks"]}
    assert marks["Agustin Ferreyra"]["found"] is True
    assert marks["Ezequiel Guzman"]["found"] is False
    assert any("Ezequiel Guzman" in warning for warning in payload["warnings"])
    download = client.get(payload["downloadUrl"])
    assert download.status_code == 200
    assert download.content[:4] == b"%PDF"


def test_analyze_rejects_bad_player_line():
    schedule = """
Hombres:

Cancha 1
11:30: Mambo F.C. vs Echale Pesteke
"""
    response = client.post(
        "/api/analyze",
        data={"schedule": schedule, "source": "ejemplo", "players": "sin parentesis"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert any("formato" in warning for warning in payload["warnings"])


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
