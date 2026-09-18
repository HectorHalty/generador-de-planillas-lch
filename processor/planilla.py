from __future__ import annotations

import pymupdf as fitz

from processor import fonts
from processor.schedule import Match

A4 = fitz.paper_rect("a4")
GREEN = (0.09, 0.22, 0.16)
GREEN_SOFT = (0.16, 0.38, 0.28)
INK = (0.08, 0.09, 0.08)
MUTED = (0.35, 0.38, 0.35)
LINE = (0.76, 0.78, 0.74)
PAPER = (0.98, 0.96, 0.91)
HEADER_FILL = (0.09, 0.22, 0.16)
WOMEN_FILL = (0.45, 0.18, 0.22)


def _fontnames(page: fitz.Page) -> tuple[str, str]:
    regular = "sans"
    bold = "sansb"
    if fonts.REGULAR:
        page.insert_font(fontname=regular, fontfile=fonts.REGULAR)
    if fonts.BOLD:
        page.insert_font(fontname=bold, fontfile=fonts.BOLD)
    else:
        bold = regular
    return regular, bold


def _fill(page: fitz.Page, rect: fitz.Rect, color: tuple[float, float, float]) -> None:
    page.draw_rect(rect, color=color, fill=color, width=0)


def _textbox(
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    *,
    fontname: str,
    fontsize: float,
    color: tuple[float, float, float] = (1, 1, 1),
    align: int = 0,
) -> None:
    page.insert_textbox(
        rect,
        text,
        fontname=fontname,
        fontsize=fontsize,
        color=color,
        align=align,
    )


def draw_index_pages(doc: fitz.Document, matches: list[Match]) -> None:
    groups: dict[tuple[str, int], list[Match]] = {}
    for match in matches:
        groups.setdefault((match.category, match.court), []).append(match)

    page = doc.new_page(width=A4.width, height=A4.height)
    regular, bold = _fontnames(page)
    _fill(page, page.rect, PAPER)
    _fill(page, fitz.Rect(0, 0, page.rect.width, 92), HEADER_FILL)
    page.insert_text(
        (36, 48),
        "Planillas de cancha",
        fontname=bold,
        fontsize=22,
        color=(1, 1, 1),
    )
    page.insert_text(
        (36, 72),
        f"{len(matches)} partidos  ·  ordenados por cancha y horario",
        fontname=regular,
        fontsize=11,
        color=(0.85, 0.92, 0.86),
    )

    y = 112
    last_category = None
    for (category, court), court_matches in groups.items():
        needed = 28 + 18 * len(court_matches)
        if y + needed > page.rect.height - 40:
            page = doc.new_page(width=A4.width, height=A4.height)
            regular, bold = _fontnames(page)
            _fill(page, page.rect, PAPER)
            y = 48
        if category != last_category:
            color = HEADER_FILL if category == "Hombres" else WOMEN_FILL
            _fill(page, fitz.Rect(36, y, page.rect.width - 36, y + 26), color)
            _textbox(
                page,
                fitz.Rect(48, y + 4, page.rect.width - 48, y + 24),
                category.upper(),
                fontname=bold,
                fontsize=12,
            )
            y += 36
            last_category = category
        page.insert_text(
            (48, y + 12),
            f"Cancha {court}",
            fontname=bold,
            fontsize=12,
            color=GREEN,
        )
        y += 22
        for match in court_matches:
            page.insert_text(
                (48, y + 10),
                match.time,
                fontname=bold,
                fontsize=10,
                color=INK,
            )
            page.insert_text(
                (100, y + 10),
                f"{match.home}  vs  {match.away}",
                fontname=regular,
                fontsize=10,
                color=INK,
            )
            y += 18
        y += 10


def draw_match_planilla(
    doc: fitz.Document,
    match: Match,
    *,
    blank_slots: bool = False,
    extra_note: str | None = None,
) -> fitz.Page:
    page = doc.new_page(width=A4.width, height=A4.height)
    regular, bold = _fontnames(page)
    _fill(page, page.rect, (1, 1, 1))

    header_color = HEADER_FILL if match.category == "Hombres" else WOMEN_FILL
    _fill(page, fitz.Rect(0, 0, page.rect.width, 86), header_color)
    _textbox(
        page,
        fitz.Rect(28, 16, 360, 42),
        "PLANILLA DE CANCHA",
        fontname=bold,
        fontsize=18,
    )
    _textbox(
        page,
        fitz.Rect(28, 44, 360, 78),
        extra_note or "Torneo masivo  ·  conservá esta hoja en la mesa de control",
        fontname=regular,
        fontsize=9,
        color=(0.88, 0.92, 0.88),
    )

    court_value = "" if blank_slots else str(match.court)
    time_value = "" if blank_slots else match.time
    _draw_meta_box(page, 390, 14, "Categoría", match.category, regular, bold)
    _draw_meta_box(page, 390, 48, "Cancha:", court_value or "______", regular, bold)
    _draw_meta_box(page, 490, 48, "Hora:", time_value or "______", regular, bold)

    _draw_team_block(page, match.home, 28, 108, "LOCAL", regular, bold)
    _draw_team_block(page, match.away, 306, 108, "VISITANTE", regular, bold)

    y = 108 + 28 + 14 * 12 + 18
    page.draw_rect(
        fitz.Rect(28, y, page.rect.width - 28, y + 92),
        color=LINE,
        fill=(0.97, 0.97, 0.96),
        width=0.6,
    )
    page.insert_text((40, y + 22), "Resultado final", fontname=bold, fontsize=10, color=GREEN)
    page.insert_text((40, y + 48), "Local: ____    Visitante: ____", fontname=regular, fontsize=11, color=INK)
    page.insert_text((320, y + 22), "Árbitro / fiscal", fontname=bold, fontsize=10, color=GREEN)
    page.insert_text((320, y + 48), "Nombre: ________________", fontname=regular, fontsize=11, color=INK)
    page.insert_text((40, y + 78), "Firma local: ______________     Firma visitante: ______________", fontname=regular, fontsize=9, color=MUTED)

    footer = fitz.Rect(0, page.rect.height - 28, page.rect.width, page.rect.height)
    _fill(page, footer, header_color)
    label = f"Cancha {match.court}   ·   {match.time}   ·   {match.category}"
    if blank_slots:
        label = f"{match.category}   ·   {match.home} vs {match.away}"
    _textbox(
        page,
        fitz.Rect(28, page.rect.height - 24, page.rect.width - 28, page.rect.height - 4),
        label,
        fontname=bold,
        fontsize=10,
        align=1,
    )
    return page


def _draw_meta_box(
    page: fitz.Page,
    x: float,
    y: float,
    label: str,
    value: str,
    regular: str,
    bold: str,
) -> None:
    box = fitz.Rect(x, y, x + 92, y + 30)
    page.draw_rect(box, color=(1, 1, 1), fill=(1, 1, 1), width=0)
    page.insert_text((x + 6, y + 10), label, fontname=regular, fontsize=7, color=MUTED)
    page.insert_text((x + 6, y + 24), value, fontname=bold, fontsize=11, color=INK)


def _draw_team_block(
    page: fitz.Page,
    team: str,
    x: float,
    y: float,
    side: str,
    regular: str,
    bold: str,
) -> None:
    width = 262
    header = fitz.Rect(x, y, x + width, y + 36)
    page.draw_rect(header, color=GREEN, fill=GREEN_SOFT, width=0)
    page.insert_text((x + 10, y + 14), side, fontname=regular, fontsize=8, color=(0.85, 0.93, 0.88))
    page.insert_textbox(
        fitz.Rect(x + 8, y + 16, x + width - 8, y + 34),
        team,
        fontname=bold,
        fontsize=11,
        color=(1, 1, 1),
    )

    row_h = 14
    titles = [("N°", 28), ("Jugador", 150), ("DNI", 52), ("G", 16)]
    yy = y + 36
    page.draw_rect(fitz.Rect(x, yy, x + width, yy + row_h), color=LINE, fill=(0.93, 0.95, 0.93), width=0.4)
    cursor = x + 6
    for title, w in titles:
        page.insert_text((cursor, yy + 10), title, fontname=bold, fontsize=7, color=MUTED)
        cursor += w
    for index in range(1, 13):
        yy += row_h
        bg = (1, 1, 1) if index % 2 else (0.96, 0.97, 0.95)
        page.draw_rect(fitz.Rect(x, yy, x + width, yy + row_h), color=LINE, fill=bg, width=0.4)
        page.insert_text((x + 10, yy + 10), str(index), fontname=regular, fontsize=8, color=MUTED)
        cursor = x + 34
        for _, w in titles[1:]:
            page.draw_line(fitz.Point(cursor, yy), fitz.Point(cursor, yy + row_h), color=LINE, width=0.3)
            cursor += w
    page.draw_rect(fitz.Rect(x, y + 36, x + width, yy + row_h), color=LINE, width=0.6)
