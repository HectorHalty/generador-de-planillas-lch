from __future__ import annotations

import pymupdf as fitz

from processor import fonts
from processor.schedule import Match

INK = (0.08, 0.09, 0.08)
WHITE = (1, 1, 1)


def stamp_page(page: fitz.Page, match: Match, day: str | None = None) -> None:
    write_day_at = None
    if day:
        write_day_at = _redact_day_blank(page)
        if write_day_at is not None:
            page.apply_redactions()
    fontname = _fontname(page)
    if day and write_day_at is not None:
        page.insert_text(
            write_day_at,
            f"Día: {day}",
            fontname=fontname,
            fontsize=10,
            color=INK,
        )
    for rect, value in _value_ops(
        page,
        ["Cancha N°:", "Cancha N:", "Cancha N", "Cancha:", "CANCHA:"],
        str(match.court),
    ):
        _paint_value(page, rect, value, fontname)
    for rect, value in _value_ops(
        page,
        ["Horario:", "Hora:", "HORA:", "Horario"],
        match.time,
    ):
        _paint_value(page, rect, value, fontname)


def _redact_day_blank(page: fitz.Page) -> tuple[float, float] | None:
    hits: list[fitz.Rect] = []
    for label in ("Día:", "Dia:", "DÍA:", "DIA:"):
        hits.extend(page.search_for(label))
    if not hits:
        return None
    label_rect = sorted(hits, key=lambda item: (item.y0, item.x0))[0]
    horario_hits = [
        rect
        for needle in ("Horario:", "Horario")
        for rect in page.search_for(needle)
        if abs(rect.y0 - label_rect.y0) <= 8
    ]
    x1 = (
        min(rect.x0 for rect in horario_hits) - 6
        if horario_hits
        else min(label_rect.x1 + 110, page.rect.width - 8)
    )
    cover = fitz.Rect(label_rect.x0 - 1, label_rect.y0 - 1, x1, label_rect.y1 + 1)
    page.add_redact_annot(cover, fill=WHITE)
    return (label_rect.x0, label_rect.y1 - 3)


def _paint_value(page: fitz.Page, rect: fitz.Rect, value: str, fontname: str) -> None:
    page.draw_rect(rect, color=WHITE, fill=WHITE, width=0)
    page.insert_text(
        (rect.x0 + 2, rect.y1 - 3),
        value,
        fontname=fontname,
        fontsize=11,
        color=INK,
    )


def _fontname(page: fitz.Page) -> str:
    existing = {item[4] for item in page.get_fonts()}
    if "sansb" in existing:
        return "sansb"
    if "sans" in existing:
        return "sans"
    name = "stampfont"
    if fonts.BOLD:
        page.insert_font(fontname=name, fontfile=fonts.BOLD)
        return name
    if fonts.REGULAR:
        page.insert_font(fontname=name, fontfile=fonts.REGULAR)
        return name
    return "helv"


def _value_ops(page: fitz.Page, labels: list[str], value: str) -> list[tuple[fitz.Rect, str]]:
    hits: list[fitz.Rect] = []
    for label in labels:
        hits.extend(page.search_for(label))
    if not hits:
        return []
    label_rect = sorted(hits, key=lambda item: (item.y0, item.x0))[0]
    blanks: list[fitz.Rect] = []
    for needle in ("________", "______", "_______"):
        blanks.extend(page.search_for(needle))
    candidates = [
        rect
        for rect in blanks
        if rect.x0 >= label_rect.x0 - 6
        and abs(rect.y0 - label_rect.y0) <= 8
    ]
    if not candidates:
        candidates = [
            rect
            for rect in blanks
            if rect.x0 >= label_rect.x0 - 6
            and label_rect.y0 - 2 <= rect.y0 <= label_rect.y1 + 20
        ]
    if candidates:
        candidates.sort(key=lambda rect: (abs(rect.y0 - label_rect.y0), abs(rect.x0 - label_rect.x1)))
        target = candidates[0] + (-1, -2, 18, 2)
        return [(target, value)]
    return [
        (
            fitz.Rect(
                label_rect.x1 + 4,
                label_rect.y0 - 1,
                min(label_rect.x1 + 72, page.rect.width - 8),
                label_rect.y1 + 2,
            ),
            value,
        )
    ]
