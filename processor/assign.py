from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from processor.names import find_teams_in_text, names_equivalent
from processor.schedule import Match

VS_RE = re.compile(r"(.+?)\s+vs\.?\s+(.+)", re.IGNORECASE)
CLUB_RE = re.compile(r"Club:\s*(.+)$", re.IGNORECASE)
SIDE_LABELS = {"local", "visitante", "equipo local", "equipo visitante", "equipo"}


@dataclass
class PageAnalysis:
    index: int
    text: str
    matched_teams: list[str]
    extra_teams: list[str]
    kind: str
    match_id: int | None
    action: str
    reason: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload.pop("text", None)
        return payload


@dataclass
class AssignmentResult:
    pages: list[PageAnalysis]
    match_pages: dict[int, list[int]]
    removed_teams: list[str]
    unmatched_matches: list[int]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pages": [page.to_dict() for page in self.pages],
            "matchPages": {str(key): value for key, value in self.match_pages.items()},
            "removedTeams": self.removed_teams,
            "unmatchedMatches": self.unmatched_matches,
            "warnings": self.warnings,
        }


def extract_club(text: str) -> str | None:
    for raw in (text or "").splitlines():
        line = raw.replace("\xa0", " ").strip()
        hit = CLUB_RE.search(line)
        if hit:
            name = re.sub(r"\s+", " ", hit.group(1)).strip(" |")
            if name:
                return name
    return None


def extract_named_sides(text: str) -> list[str]:
    names: list[str] = []
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line.lower() in SIDE_LABELS and index + 1 < len(lines):
            candidate = lines[index + 1].strip(" ·-")
            if 2 < len(candidate) <= 48:
                names.append(candidate)
        vs_hit = VS_RE.search(line)
        if vs_hit:
            home = vs_hit.group(1).split("·")[-1].strip()
            away = vs_hit.group(2).strip()
            if home:
                names.append(home)
            if away:
                names.append(away)
    return _unique_teams(names)


def assign_pages(
    page_texts: list[str],
    matches: list[Match],
) -> AssignmentResult:
    if any(extract_club(text) for text in page_texts):
        return _assign_club_sheets(page_texts, matches)
    return _assign_match_sheets(page_texts, matches)


def _scheduled_name(name: str, scheduled: list[str]) -> str | None:
    for team in scheduled:
        if names_equivalent(name, team):
            return team
    return None


def _assign_club_sheets(
    page_texts: list[str],
    matches: list[Match],
) -> AssignmentResult:
    scheduled_teams = [team for match in matches for team in match.teams]
    groups: list[dict] = []
    current: dict | None = None

    for index, text in enumerate(page_texts):
        club = extract_club(text)
        if club:
            current = {
                "club": club,
                "scheduled": _scheduled_name(club, scheduled_teams),
                "pages": [index],
            }
            groups.append(current)
        elif current is not None:
            current["pages"].append(index)

    team_pages: dict[str, list[int]] = {}
    leftover: list[str] = []
    keep_indexes: dict[int, tuple[int, str]] = {}

    for group in groups:
        scheduled = group["scheduled"]
        if scheduled:
            team_pages[scheduled] = group["pages"]
            match = next(
                item
                for item in matches
                if names_equivalent(scheduled, item.home) or names_equivalent(scheduled, item.away)
            )
            reason = f"Cancha {match.court} · {match.time} · {match.category}"
            for page_index in group["pages"]:
                keep_indexes[page_index] = (match.id, reason)
        else:
            leftover.append(group["club"])

    match_pages: dict[int, list[int]] = {match.id: [] for match in matches}
    for match in matches:
        match_pages[match.id] = [
            *team_pages.get(match.home, []),
            *team_pages.get(match.away, []),
        ]

    pages: list[PageAnalysis] = []
    for index, text in enumerate(page_texts):
        kept = keep_indexes.get(index)
        club = extract_club(text)
        if kept:
            match_id, reason = kept
            matched = []
            for match in matches:
                if match.id == match_id:
                    club_name = club or next(
                        (
                            team
                            for team, indexes in team_pages.items()
                            if index in indexes
                        ),
                        "",
                    )
                    matched = [club_name] if club_name else []
                    break
            pages.append(
                PageAnalysis(
                    index=index,
                    text=text[:4000],
                    matched_teams=matched,
                    extra_teams=[],
                    kind="team" if club else "continuation",
                    match_id=match_id,
                    action="keep",
                    reason=reason,
                )
            )
        else:
            extra = [club] if club and not _scheduled_name(club, scheduled_teams) else []
            pages.append(
                PageAnalysis(
                    index=index,
                    text=text[:4000],
                    matched_teams=[],
                    extra_teams=extra,
                    kind="team" if club else "continuation",
                    match_id=None,
                    action="drop",
                    reason="Equipos fuera de este horario" if extra or not club else "Sin equipos de este horario",
                )
            )

    unmatched = [match.id for match in matches if not match_pages[match.id]]
    return AssignmentResult(
        pages=pages,
        match_pages=match_pages,
        removed_teams=sorted(_unique_teams(leftover)),
        unmatched_matches=unmatched,
    )


def _match_for_teams(teams: list[str], matches: list[Match]) -> Match | None:
    if not teams:
        return None
    for match in matches:
        home_hit = any(names_equivalent(team, match.home) for team in teams)
        away_hit = any(names_equivalent(team, match.away) for team in teams)
        if home_hit and away_hit:
            return match
    if len(teams) == 1:
        for match in matches:
            if any(names_equivalent(teams[0], team) for team in match.teams):
                return match
    return None


def _assign_match_sheets(
    page_texts: list[str],
    matches: list[Match],
) -> AssignmentResult:
    scheduled_teams = [team for match in matches for team in match.teams]
    pages: list[PageAnalysis] = []
    match_pages: dict[int, list[int]] = {match.id: [] for match in matches}
    leftover: set[str] = set()
    warnings: list[str] = []
    empty_text_pages = 0

    for index, text in enumerate(page_texts):
        if not (text or "").strip():
            empty_text_pages += 1

        hits = find_teams_in_text(text, scheduled_teams)
        matched = _unique_teams([team for team, _ in hits])
        labeled = extract_named_sides(text)
        for side in labeled:
            for team in scheduled_teams:
                if names_equivalent(side, team):
                    matched = _unique_teams([*matched, team])
        extra = [
            name
            for name in labeled
            if not any(names_equivalent(name, team) for team in scheduled_teams)
            and name.lower() not in {"hombres", "mujeres", "local", "visitante"}
        ]
        leftover.update(extra)

        kind = "other"
        if len(matched) >= 3:
            kind = "multi"
        elif len(matched) == 2:
            kind = "match"
        elif len(matched) == 1:
            kind = "team"

        match = _match_for_teams(matched, matches)
        action = "drop"
        reason = "Sin equipos de este horario"
        match_id = match.id if match else None

        if extra and not matched:
            reason = "Equipos fuera de este horario"
        if kind == "multi":
            action = "drop"
            reason = "La hoja mezcla varios partidos: se reemplaza por planillas nuevas"
            warnings.append(
                f"Página {index + 1}: encontré {len(matched)} equipos. No la conservo tal cual para no mezclar horarios."
            )
        elif match and kind in {"match", "team"}:
            action = "keep"
            reason = f"Cancha {match.court} · {match.time} · {match.category}"
            match_pages[match.id].append(index)
        elif matched:
            action = "drop"
            reason = "Equipos fuera de este horario"

        pages.append(
            PageAnalysis(
                index=index,
                text=text[:4000],
                matched_teams=matched,
                extra_teams=extra,
                kind=kind,
                match_id=match_id,
                action=action,
                reason=reason,
            )
        )

    if empty_text_pages == len(page_texts) and page_texts:
        warnings.append(
            "El PDF no tiene texto seleccionable. Si es un escaneo, las planillas se arman de cero con el horario."
        )

    unmatched = [match.id for match in matches if not match_pages[match.id]]
    return AssignmentResult(
        pages=pages,
        match_pages=match_pages,
        removed_teams=sorted(leftover),
        unmatched_matches=unmatched,
        warnings=warnings,
    )


def _unique_teams(teams: list[str]) -> list[str]:
    result: list[str] = []
    for team in teams:
        cleaned = re.sub(r"\s+", " ", team).strip(" ·-|")
        if not cleaned:
            continue
        if not any(names_equivalent(cleaned, existing) for existing in result):
            result.append(cleaned)
    return result
