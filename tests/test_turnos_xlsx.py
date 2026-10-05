from pathlib import Path

import pymupdf as fitz
import pytest

from processor.schedule import parse_schedule
from processor.turnos_xlsx import (
    build_schedule_text,
    clubs_from_page_texts,
    read_fixture,
    resolve_abbreviations,
)

FIXTURE = Path(__file__).parent / "fixtures" / "turnos-y-canchas.xlsx"
MASIVO = Path(__file__).parent.parent / "public" / "planillas-masivo.pdf"


def _clubs():
    if not MASIVO.exists():
        pytest.skip("falta el masivo")
    document = fitz.open(MASIVO)
    texts = [page.get_text("text") for page in document]
    document.close()
    return clubs_from_page_texts(texts)


def test_uses_last_fixture_present_in_both_sheets():
    number, day, matches = read_fixture(FIXTURE.read_bytes())
    # la fecha 8 de hombres tiene un solo partido suelto: no es la jornada
    assert number == 7
    assert day.isoformat() == "2026-10-03"
    men = [m for m in matches if m.category == "Hombres"]
    women = [m for m in matches if m.category == "Mujeres"]
    assert len(men) == 28
    assert len(women) == 18


def test_court_times_follow_their_hour_column():
    _, _, matches = read_fixture(FIXTURE.read_bytes())
    by_court = {(m.category, m.court): m.time for m in matches}
    assert by_court[("Hombres", 1)] in {"11:30", "13:00", "14:30", "16:00"}
    first = {m.court: m.time for m in matches if m.category == "Hombres" and m.time < "12:00"}
    assert first[1] == first[3] == "11:30"
    assert first[5] == first[8] == "11:45"
    women_times = {m.time for m in matches if m.category == "Mujeres"}
    assert women_times == {"12:00", "13:00", "14:00", "15:00", "16:00"}


def test_abbreviations_resolve_to_real_club_names():
    result = build_schedule_text(FIXTURE.read_bytes(), _clubs())
    parsed = parse_schedule(result.text)
    assert parsed.errors == []
    assert result.matches == len(parsed.matches) == 45
    names = {team for match in parsed.matches for team in match.teams}
    for expected in (
        "El Equipo del Banco",
        "La República Chueca",
        "Ahí No Me Servís",
        "Para Que Te Traje",
        "C.A.R.U.",
        "Cortá Con Tanta Dulzura",
        "Los Nuñes",
        "La Mancha Ester",
        "La Sillita No Se Mancha",
    ):
        assert expected in names
    assert any("24/7" in warning for warning in result.warnings)


def test_manual_alias_fills_what_cannot_be_guessed():
    aliases = {"Mujeres": {"24/7": "Veinticuatrosiete"}}
    result = build_schedule_text(FIXTURE.read_bytes(), _clubs(), aliases)
    assert result.warnings == []
    assert result.matches == 46
    assert "Veinticuatrosiete" in result.text


def test_ambiguous_abbreviation_is_not_guessed():
    clubs = ["Los Tigres Norte", "Los Tigres Sur"]
    assert resolve_abbreviations(["tigres"], clubs) == {"tigres": None}


def test_abbreviation_taken_by_exact_match_does_not_steal_the_longer_name():
    clubs = ["La Mancha Ester", "La Sillita No Se Mancha"]
    result = resolve_abbreviations(["mancha", "sillita"], clubs)
    assert result == {"mancha": "La Mancha Ester", "sillita": "La Sillita No Se Mancha"}
