from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from processor.names import find_teams_in_text, names_equivalent
from processor.schedule import Match

VS_RE = re.compile(r"(.+?)\s+vs\.?\s+(.+)", re.IGNORECASE)
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


def assign_pages(
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

    unmatched = [
        match.id
        for match in matches
        if not match_pages[match.id]
    ]
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
