from pathlib import Path

import pymupdf as fitz

from processor.assign import extract_club
from processor.pipeline import ProcessOptions, analyze_document, generate_document
from processor.schedule import parse_schedule


def _club_page(doc: fitz.Document, club: str, extra_players: bool = False) -> None:
    page = doc.new_page(width=595, height=842)
    page.insert_text((40, 40), "PLANILLA DE CANCHA", fontsize=16)
    page.insert_text(
        (40, 62),
        f"Liga: Hombres C  |  Temporada: Clausura 2026  |  Club: {club}",
        fontsize=10,
    )
    page.insert_text((40, 90), "Horario: ________     Cancha N°: ________", fontsize=11)
    page.insert_text((40, 120), "1  Jugador Uno", fontsize=10)
    if extra_players:
        page = doc.new_page(width=595, height=842)
        page.insert_text((40, 40), "Firma Director Tecnico: _________________________", fontsize=10)
        page.insert_text((40, 60), "Firma Capitan: ___________________________________", fontsize=10)


def test_extract_club_from_liga_line():
    text = "Liga: Mujeres A \xa0 | \xa0 Temporada: Clausura 2026 \xa0 | \xa0 Club: ADN F.C."
    assert extract_club(text) == "ADN F.C."


def test_club_sheets_drop_extras_and_keep_continuations():
    schedule = """
    Hombres:
    Cancha 1
    11:30: Mambo F.C. vs Echale Pesteke
    """
    document = fitz.open()
    _club_page(document, "Mambo F.C.", extra_players=True)
    _club_page(document, "Ahí No Me Servís", extra_players=True)
    _club_page(document, "Echale Pesteke")
    mixed = document.tobytes()
    document.close()

    analysis = analyze_document(mixed, schedule)
    assert analysis["ok"] is True
    assert "Ahí No Me Servís" in analysis["removedTeams"]
    assert analysis["pageCount"] == 5
    kept = {page["page"] for page in analysis["keptPages"]}
    dropped = {page["page"] for page in analysis["removedPages"]}
    assert kept == {1, 2, 5}
    assert 3 in dropped and 4 in dropped

    pdf_out, summary = generate_document(mixed, schedule, ProcessOptions(include_index=False))
    assert summary["keptOriginalPages"] == 3
    output = fitz.open(stream=pdf_out, filetype="pdf")
    full = "\n".join(page.get_text("text") for page in output)
    assert "Ahí No Me Servís" not in full
    assert "Mambo F.C." in full
    assert "Echale Pesteke" in full
    assert "11:30" in full
    output.close()


def test_real_masivo_if_present():
    path = Path("public/planillas-masivo.pdf")
    if not path.exists():
        return
    schedule = Path("public/horario-jornada.txt").read_text(encoding="utf-8")
    analysis = analyze_document(path.read_bytes(), schedule)
    assert analysis["pageCount"] == 151
    removed = analysis["removedTeams"]
    assert "Ahí No Me Servís" in removed
    assert "Sarasa" in removed
    assert "Mambo F.C." not in removed
    parsed = parse_schedule(schedule)
    assert len(parsed.matches) == 46
    assert not analysis["unmatchedMatches"]
    assert len(removed) == 8
    assert len(analysis["keptPages"]) >= 92
