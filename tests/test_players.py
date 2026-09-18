from datetime import date
from pathlib import Path

import pymupdf as fitz

from processor.pipeline import ProcessOptions, analyze_document, generate_document
from processor.players import apply_player_marks, parse_player_marks


def _roster_pdf(club: str, names: list[str]) -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((40, 40), "PLANILLA DE CANCHA", fontsize=16)
    page.insert_text((40, 62), f"Liga: Hombres C  |  Temporada: Clausura 2026  |  Club: {club}", fontsize=10)
    page.insert_text((65.25, 132), "NOMBRE DEL JUGADOR", fontsize=8)
    y = 156
    for index, name in enumerate(names, start=1):
        page.insert_text((42, y), str(index), fontsize=10)
        page.insert_text((65.25, y), name, fontsize=10)
        y += 22.5
    payload = document.tobytes()
    document.close()
    return payload


def test_parse_player_marks_format():
    players, errors = parse_player_marks(
        "Ezequiel Guzman (Mimetizarte)\n\nAgustin Ferreyra (Mimetizarte)\nmal formato\nJo (X)"
    )
    assert [item.raw for item in players] == [
        "Ezequiel Guzman (Mimetizarte)",
        "Agustin Ferreyra (Mimetizarte)",
    ]
    assert any("formato" in error for error in errors)
    assert any("nombre o el equipo" in error for error in errors)


def test_highlights_found_player_and_warns_missing():
    pdf = _roster_pdf("Mimetizarte", ["Agustín Ferreyra", "Bruno Lemma"])
    players, errors = parse_player_marks(
        "Agustin Ferreyra (Mimetizarte)\nEzequiel Guzman (Mimetizarte)\nNadie (Equipo Inventado)"
    )
    assert errors == []
    document = fitz.open(stream=pdf, filetype="pdf")
    marks = apply_player_marks(document, players)
    by_name = {item.name: item for item in marks}
    assert by_name["Agustin Ferreyra"].found is True
    assert by_name["Agustin Ferreyra"].page == 1
    assert by_name["Ezequiel Guzman"].found is False
    assert "No encuentro a Ezequiel Guzman" in (by_name["Ezequiel Guzman"].warning or "")
    assert by_name["Nadie"].found is False
    assert "planilla de Equipo Inventado" in (by_name["Nadie"].warning or "")
    annots = list(document[0].annots() or [])
    assert annots
    assert annots[0].type[1] == "Highlight"
    document.close()


def test_generate_paints_row_and_keeps_warning():
    pdf = _roster_pdf("Mimetizarte", ["Agustín Ferreyra", "Bruno Lemma"])
    schedule = """
Hombres:

Cancha 1
13:00: As Broma vs Mimetizarte
"""
    players, _ = parse_player_marks("Agustin Ferreyra (Mimetizarte)\nEzequiel Guzman (Mimetizarte)")
    pdf_out, summary = generate_document(
        pdf,
        schedule,
        ProcessOptions(match_date=date(2026, 9, 19), players=players),
    )
    marks = {item["name"]: item for item in summary["playerMarks"]}
    assert marks["Agustin Ferreyra"]["found"] is True
    assert marks["Ezequiel Guzman"]["found"] is False
    assert any("Ezequiel Guzman" in warning for warning in summary["warnings"])
    output = fitz.open(stream=pdf_out, filetype="pdf")
    annots = list(output[0].annots() or [])
    assert annots
    assert annots[0].type[1] == "Highlight"
    output.close()


def test_analyze_does_not_need_paint_but_reports_missing():
    pdf = _roster_pdf("Mimetizarte", ["Bruno Lemma"])
    schedule = """
Hombres:

Cancha 1
13:00: As Broma vs Mimetizarte
"""
    players, _ = parse_player_marks("Ezequiel Guzman (Mimetizarte)")
    payload = analyze_document(pdf, schedule, players=players)
    assert payload["ok"] is True
    assert payload["playerMarks"][0]["found"] is False
    assert "No encuentro a Ezequiel Guzman" in payload["warnings"][0]


def test_real_masivo_player_marks_if_present():
    path = Path("public/planillas-masivo.pdf")
    if not path.exists():
        return
    schedule = Path("public/horario-jornada.txt").read_text(encoding="utf-8")
    players, _ = parse_player_marks(
        "Agustin Ferreyra (Mimetizarte)\nEzequiel Guzman (Mimetizarte)"
    )
    pdf_out, summary = generate_document(
        path.read_bytes(),
        schedule,
        ProcessOptions(match_date=date(2026, 9, 19), players=players),
    )
    marks = {item["name"]: item for item in summary["playerMarks"]}
    assert marks["Agustin Ferreyra"]["found"] is True
    assert marks["Ezequiel Guzman"]["found"] is False
    assert "No encuentro a Ezequiel Guzman" in (marks["Ezequiel Guzman"]["warning"] or "")
    output = fitz.open(stream=pdf_out, filetype="pdf")
    page_index = (marks["Agustin Ferreyra"]["page"] or 1) - 1
    annots = list(output[page_index].annots() or [])
    assert annots
    output.close()
