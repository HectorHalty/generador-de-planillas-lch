from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from processor.planilla import draw_match_planilla
from processor.schedule import Match, parse_schedule, sort_matches

EXTRA_MATCHES = [
    Match(
        id=9001,
        category="Hombres",
        court=9,
        time="18:00",
        home="Los Descartados",
        away="Equipo Prueba",
    ),
    Match(
        id=9002,
        category="Mujeres",
        court=9,
        time="18:00",
        home="Club Fantasma",
        away="No Juega Hoy",
    ),
    Match(
        id=9003,
        category="Hombres",
        court=10,
        time="19:00",
        home="Reserva B",
        away="Amigos del Bar",
    ),
]


def build_sample_pdf(schedule_text: str) -> bytes:
    parsed = parse_schedule(schedule_text)
    matches = sort_matches(parsed.matches, "category")
    document = fitz.open()
    for match in matches:
        draw_match_planilla(
            document,
            match,
            blank_slots=True,
            extra_note="Exportación masiva  ·  cancha y hora pendientes",
        )
    for extra in EXTRA_MATCHES:
        draw_match_planilla(
            document,
            extra,
            blank_slots=True,
            extra_note="FUERA DE JORNADA  ·  este partido no corresponde al horario actual",
        )
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def write_sample_pdf(path: Path, schedule_text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_sample_pdf(schedule_text))
    return path
