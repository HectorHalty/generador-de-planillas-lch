from __future__ import annotations

import re
from dataclasses import asdict, dataclass

import pymupdf as fitz
from rapidfuzz import fuzz

from processor.assign import extract_club
from processor.names import names_equivalent, normalize_name

PLAYER_LINE = re.compile(r"^\s*(.+?)\s*\(\s*(.+?)\s*\)\s*$")
HEADER_LABELS = {"nombre del jugador", "nombre", "dni", "fecha nac", "dorsal", "firma"}
CELESTE = (0.62, 0.90, 0.98)
TABLE_LEFT = 37.5
TABLE_RIGHT = 558.0


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
        line = raw.strip()
        if not line:
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
    row = fitz.Rect(TABLE_LEFT, name_rect.y0 - 5, TABLE_RIGHT, name_rect.y1 + 11)
    annot = page.add_highlight_annot(row)
    annot.set_colors(stroke=CELESTE)
    annot.set_opacity(0.55)
    annot.update()


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
