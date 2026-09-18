from __future__ import annotations

import pymupdf as fitz

from processor import fonts
from processor.schedule import Match

GREEN = (0.09, 0.22, 0.16)
WINE = (0.45, 0.18, 0.22)
INK = (0.08, 0.09, 0.08)
WHITE = (1, 1, 1)


def stamp_page(page: fitz.Page, match: Match) -> None:
    fontname = _fontname(page)
    for rect, value in _value_ops(page, ["Cancha:", "CANCHA:"], str(match.court)):
        _paint_value(page, rect, value, fontname)
    for rect, value in _value_ops(page, ["Hora:", "Horario:", "HORA:"], match.time):
        _paint_value(page, rect, value, fontname)

    color = GREEN if match.category == "Hombres" else WINE
    footer = fitz.Rect(0, page.rect.height - 26, page.rect.width, page.rect.height)
    page.draw_rect(footer, color=color, fill=color, width=0)
    page.insert_textbox(
        fitz.Rect(16, page.rect.height - 22, page.rect.width - 16, page.rect.height - 4),
        f"Cancha {match.court}   ·   {match.time}   ·   {match.category}   ·   {match.home} vs {match.away}",
        fontname=fontname,
        fontsize=9,
        color=WHITE,
        align=1,
    )


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
    candidates = [
        rect
        for rect in page.search_for("______")
        if rect.x0 >= label_rect.x0 - 6
        and label_rect.y0 - 2 <= rect.y0 <= label_rect.y1 + 20
    ]
    if candidates:
        candidates.sort(key=lambda rect: (abs(rect.x0 - label_rect.x0), rect.y0))
        target = candidates[0] + (-1, -1, 8, 2)
        return [(target, value)]
    return [
        (
            fitz.Rect(
                label_rect.x0,
                label_rect.y1 + 1,
                min(label_rect.x0 + 88, page.rect.width - 8),
                label_rect.y1 + 16,
            ),
            value,
        )
    ]
