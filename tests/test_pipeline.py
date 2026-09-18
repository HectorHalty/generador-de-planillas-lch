from pathlib import Path

import pymupdf as fitz

from processor.names import names_equivalent, normalize_name
from processor.pipeline import ProcessOptions, analyze_document, generate_document
from processor.planilla import draw_match_planilla
from processor.sample import EXTRA_MATCHES
from processor.schedule import parse_schedule, sort_matches

DEFAULT = """
Hombres:

Cancha 1
11:30: Mambo F.C. vs Echale Pesteke
13:00: As Broma vs Mimetizarte

Cancha 2
11:30: La República Chueca vs El Equipo del Banco

Mujeres:

Cancha 1
12:00: Wonka´s vs Es Contagioso
16:00: La Reserva vs Stella´s
""".strip()


def test_parse_counts_full_jornada():
    text = Path("public/horario-jornada.txt").read_text(encoding="utf-8")
    parsed = parse_schedule(text)
    assert parsed.errors == []
    assert len(parsed.matches) == 46
    assert len(parsed.teams) == 92
    men = [match for match in parsed.matches if match.category == "Hombres"]
    women = [match for match in parsed.matches if match.category == "Mujeres"]
    assert len(men) == 28
    assert len(women) == 18
    assert men[0].home == "Mambo F.C."
    assert men[0].court == 1
    assert men[0].time == "11:30"


def test_parse_handles_markdown_and_apostrophes():
    text = """
    **Mujeres:**
    *Cancha 4*
    * 15:00: Pase Libre vs Mandale Fruta
    * 12:00: Wonka´s vs Stella's
    """
    parsed = parse_schedule(text)
    assert len(parsed.matches) == 2
    assert parsed.matches[0].court == 4
    assert names_equivalent(parsed.matches[1].home, "Wonkas")


def test_normalize_ignores_fc_and_accents():
    assert normalize_name("C.F. Los Silos") == normalize_name("Los Silos")
    assert names_equivalent("Vasco Da Garça", "Vasco Da Garca")
    assert names_equivalent("Wonka´s", "Wonka's")
    assert names_equivalent("Eclécticos F.C.", "Eclecticos FC")


def _mixed_pdf() -> bytes:
    parsed = parse_schedule(DEFAULT)
    document = fitz.open()
    for match in sort_matches(parsed.matches):
        draw_match_planilla(document, match, blank_slots=True)
    for extra in EXTRA_MATCHES:
        draw_match_planilla(document, extra, blank_slots=True)
    payload = document.tobytes()
    document.close()
    return payload


def test_pipeline_drops_unscheduled_and_fills_slots():
    mixed = _mixed_pdf()
    analysis = analyze_document(mixed, DEFAULT)
    assert analysis["ok"] is True
    removed = " ".join(analysis["removedTeams"])
    assert "Los Descartados" in removed
    assert "Club Fantasma" in removed
    assert "Amigos del Bar" in removed

    pdf_out, summary = generate_document(
        mixed,
        DEFAULT,
        ProcessOptions(include_index=True, create_missing=True, sort_mode="category"),
    )
    assert summary["keptOriginalPages"] == 5
    output = fitz.open(stream=pdf_out, filetype="pdf")
    full_text = "\n".join(page.get_text("text") for page in output)
    assert "Los Descartados" not in full_text
    assert "Club Fantasma" not in full_text
    assert "Mambo F.C." in full_text
    assert "Cancha 1" in full_text
    assert "11:30" in full_text
    assert "Wonka" in full_text
    assert output.page_count == 6
    output.close()


def test_stamp_fills_court_and_time():
    document = fitz.open()
    match = parse_schedule(DEFAULT).matches[0]
    draw_match_planilla(document, match, blank_slots=True)
    from processor.stamp import stamp_page

    stamp_page(document[0], match)
    text = document[0].get_text("text")
    assert "Cancha 1" in text
    assert "11:30" in text
    assert "Mambo F.C." in text
    times = document[0].search_for("11:30")
    assert times
    assert any(rect.y0 < 90 for rect in times)
    document.close()


def test_creates_blank_planillas_when_pdf_missing_teams():
    document = fitz.open()
    document.new_page()
    empty_pdf = document.tobytes()
    document.close()

    pdf_out, summary = generate_document(
        empty_pdf,
        DEFAULT,
        ProcessOptions(include_index=False, create_missing=True),
    )
    assert summary["createdPlanillas"] == 5
    output = fitz.open(stream=pdf_out, filetype="pdf")
    assert output.page_count == 5
    first = output[0].get_text("text")
    assert "Mambo F.C." in first
    assert "11:30" in first
    output.close()
