from __future__ import annotations

import re
from dataclasses import asdict, dataclass

import pymupdf as fitz
from rapidfuzz import fuzz

from processor.assign import extract_club
from processor.fonts import BOLD
from processor.names import names_equivalent, normalize_name

PLAYER_LINE = re.compile(r"^\s*(.+?)\s*\(\s*(.+?)\s*\)\s*$")
LIST_PREFIX = re.compile(r"^[\-\*\u2022\u00b7\#]+\s*")
HEADER_LINE = re.compile(
    r"^(suspendidos?|jugadores?|lista|sancionados?)\s*:?\s*$",
    re.IGNORECASE,
)
HEADER_LABELS = {"nombre del jugador", "nombre", "dni", "fecha nac", "dorsal", "firma"}
ROW_FILL = (0.68, 0.68, 0.68)
TABLE_LEFT = 37.5
TABLE_RIGHT = 558.0
ROW_HEIGHT_MIN = 15.0
ROW_HEIGHT_MAX = 28.0
SUSPENDIDO = "Suspendido"


@dataclass(frozen=True)
class MarkedPlayer:
    name: str
    team: str
    raw: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlayerMarkResult:
    name: str
    team: str
    found: bool
    page: int | None
    warning: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def parse_player_marks(text: str) -> tuple[list[MarkedPlayer], list[str]]:
    players: list[MarkedPlayer] = []
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for index, raw in enumerate((text or "").splitlines(), start=1):
        line = LIST_PREFIX.sub("", (raw or "").strip()).strip()
        if not line:
            continue
        if HEADER_LINE.match(line) or (line.endswith(":") and "(" not in line):
            continue
        hit = PLAYER_LINE.match(line)
        if not hit:
            errors.append(
                f"Línea {index}: usá el formato Nombre Apellido (Equipo), "
                "por ejemplo Ezequiel Guzman (Mimetizarte)."
            )
            continue
        name = re.sub(r"\s+", " ", hit.group(1)).strip(" -")
        team = re.sub(r"\s+", " ", hit.group(2)).strip(" -")
        if len(name) < 3 or len(team) < 2:
            errors.append(f"Línea {index}: faltan el nombre o el equipo.")
            continue
        key = (normalize_name(name), normalize_name(team))
        if key in seen:
            continue
        seen.add(key)
        players.append(MarkedPlayer(name=name, team=team, raw=line))
    return players, errors


def apply_player_marks(
    document: fitz.Document,
    players: list[MarkedPlayer],
    *,
    paint: bool = True,
) -> list[PlayerMarkResult]:
    if not players:
        return []
    clubs = _page_clubs(document)
    results: list[PlayerMarkResult] = []
    for player in players:
        page_indexes = [
            index
            for index, club in enumerate(clubs)
            if club and names_equivalent(club, player.team)
        ]
        if not page_indexes:
            results.append(
                PlayerMarkResult(
                    name=player.name,
                    team=player.team,
                    found=False,
                    page=None,
                    warning=f"No encuentro la planilla de {player.team}.",
                )
            )
            continue
        marked = False
        found_page = None
        for index in page_indexes:
            hit = _best_name_rect(document[index], player.name)
            if hit is None:
                continue
            if paint:
                _paint_row(document[index], hit)
            marked = True
            found_page = index + 1
            break
        if marked:
            results.append(
                PlayerMarkResult(
                    name=player.name,
                    team=player.team,
                    found=True,
                    page=found_page,
                    warning=None,
                )
            )
        else:
            results.append(
                PlayerMarkResult(
                    name=player.name,
                    team=player.team,
                    found=False,
                    page=None,
                    warning=f"No encuentro a {player.name} en la planilla de {player.team}.",
                )
            )
    return results


def highlight_player_row(page: fitz.Page, player_name: str) -> bool:
    target = _best_name_rect(page, player_name)
    if target is None:
        return False
    _paint_row(page, target)
    return True


def _paint_row(page: fitz.Page, name_rect: fitz.Rect) -> None:
    row = _row_rect(page, name_rect)
    page.draw_rect(row, color=None, fill=ROW_FILL, width=0, overlay=False)
    _write_suspendido(page, row)


def _row_rect(page: fitz.Page, name_rect: fitz.Rect) -> fitz.Rect:
    y_mid = (name_rect.y0 + name_rect.y1) / 2
    y0s: list[float] = []
    y1s: list[float] = []
    x0s: list[float] = []
    x1s: list[float] = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue
        if rect.width >= 3 or not (ROW_HEIGHT_MIN <= rect.height <= ROW_HEIGHT_MAX):
            continue
        if rect.x0 < TABLE_LEFT - 4 or rect.x0 > TABLE_RIGHT + 4:
            continue
        if rect.y0 - 1 <= y_mid <= rect.y1 + 1:
            y0s.append(rect.y0)
            y1s.append(rect.y1)
            x0s.append(rect.x0)
            x1s.append(rect.x1)
    if y0s and y1s:
        return fitz.Rect(
            min(x0s) if x0s else TABLE_LEFT,
            min(y0s),
            max(x1s) if x1s else TABLE_RIGHT,
            max(y1s),
        )
    return fitz.Rect(TABLE_LEFT, name_rect.y0 - 4, TABLE_RIGHT, name_rect.y1 + 5)


def _firma_rect(page: fitz.Page, row: fitz.Rect) -> fitz.Rect:
    xs: list[float] = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None or rect.width >= 3:
            continue
        if abs(rect.y0 - row.y0) > 1.5 or abs(rect.y1 - row.y1) > 1.5:
            continue
        if TABLE_LEFT - 4 <= rect.x0 <= TABLE_RIGHT + 4:
            xs.append(rect.x0)
    columns = sorted(set(round(x, 2) for x in xs))
    if len(columns) >= 2:
        return fitz.Rect(columns[-2], row.y0, min(columns[-1] + 0.8, row.x1), row.y1)
    width = min(84.0, max(row.width * 0.16, 60.0))
    return fitz.Rect(row.x1 - width, row.y0, row.x1, row.y1)


def _write_suspendido(page: fitz.Page, row: fitz.Rect) -> None:
    cell = _firma_rect(page, row)
    box = fitz.Rect(cell.x0 + 1, cell.y0 + 2, cell.x1 - 1.5, cell.y1 - 2)
    if box.width < 20 or box.height < 8:
        return
    fontname = "helv"
    if BOLD:
        page.insert_font(fontname="sansb", fontfile=BOLD)
        fontname = "sansb"
    page.insert_textbox(
        box,
        SUSPENDIDO,
        fontname=fontname,
        fontsize=7.5,
        color=(0, 0, 0),
        align=fitz.TEXT_ALIGN_CENTER,
    )


def _page_clubs(document: fitz.Document) -> list[str | None]:
    clubs: list[str | None] = []
    last: str | None = None
    for page in document:
        club = _page_club(page)
        if club:
            last = club
        clubs.append(club or last)
    return clubs


def _best_name_rect(page: fitz.Page, player_name: str) -> fitz.Rect | None:
    wanted = normalize_name(player_name)
    if not wanted:
        return None
    best: tuple[float, fitz.Rect] | None = None
    for text, rect in _player_name_lines(page):
        score = _name_score(wanted, normalize_name(text))
        if score < 88:
            continue
        if best is None or score > best[0]:
            best = (score, rect)
    return None if best is None else best[1]


def _name_score(wanted: str, candidate: str) -> float:
    if not wanted or not candidate:
        return 0.0
    if wanted == candidate:
        return 100.0
    if wanted in candidate or candidate in wanted:
        shorter, longer = (wanted, candidate) if len(wanted) <= len(candidate) else (candidate, wanted)
        if len(shorter) >= 8:
            return 96.0
    ratio = fuzz.ratio(wanted, candidate)
    tokens = wanted.split()
    if tokens and all(token in candidate.split() or token in candidate for token in tokens):
        return max(ratio, 93.0)
    return ratio


def _player_name_lines(page: fitz.Page) -> list[tuple[str, fitz.Rect]]:
    rows: list[tuple[str, fitz.Rect]] = []
    payload = page.get_text("dict")
    for block in payload.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            rect = fitz.Rect(line["bbox"])
            text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if rect.x0 < 55 or rect.x0 > 90 or rect.y0 < 138:
                continue
            folded = normalize_name(text)
            if not folded or folded in HEADER_LABELS:
                continue
            if re.fullmatch(r"\d+", text):
                continue
            rows.append((text, rect))
    return rows


def _page_club(page: fitz.Page) -> str | None:
    text = page.get_text("text") or ""
    club = extract_club(text)
    if club:
        return club
    return None
