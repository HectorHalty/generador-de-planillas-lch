from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

CATEGORY_RE = re.compile(
    r"^\s*[*#_]*\s*(hombres|mujeres|masculino|femenino|caballeros|damas)\s*:?\s*[*#_]*\s*$",
    re.IGNORECASE,
)
COURT_RE = re.compile(
    r"^\s*[*#_]*\s*cancha\s+(\d+)\s*:?\s*[*#_]*\s*$",
    re.IGNORECASE,
)
MATCH_RE = re.compile(
    r"^\s*[*#-]*\s*(\d{1,2}[:.]\d{2})\s*[:.\-–]\s*(.+?)\s+vs\.?\s+(.+?)\s*[*]*\s*$",
    re.IGNORECASE,
)

CATEGORY_ALIASES = {
    "hombres": "Hombres",
    "masculino": "Hombres",
    "caballeros": "Hombres",
    "mujeres": "Mujeres",
    "femenino": "Mujeres",
    "damas": "Mujeres",
}


@dataclass(frozen=True)
class Match:
    id: int
    category: str
    court: int
    time: str
    home: str
    away: str

    @property
    def minutes(self) -> int:
        hours, mins = self.time.split(":")
        return int(hours) * 60 + int(mins)

    @property
    def teams(self) -> tuple[str, str]:
        return self.home, self.away

    def to_dict(self) -> dict:
        data = asdict(self)
        data["label"] = f"{self.home} vs {self.away}"
        return data


@dataclass
class ParseResult:
    matches: list[Match] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    teams: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "matches": [match.to_dict() for match in self.matches],
            "errors": self.errors,
            "teams": self.teams,
            "matchCount": len(self.matches),
            "teamCount": len(self.teams),
        }


def _clean_team(raw: str) -> str:
    text = raw.strip().strip("*").strip()
    text = re.sub(r"\s+", " ", text)
    return text.rstrip(" ;,").strip()


def _normalize_time(raw: str) -> str:
    hours, mins = re.split(r"[:.]", raw)
    return f"{int(hours):02d}:{int(mins):02d}"


def parse_schedule(text: str) -> ParseResult:
    result = ParseResult()
    category: str | None = None
    court: int | None = None
    seen_pairs: set[tuple[str, str, str, int, str]] = set()

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        category_hit = CATEGORY_RE.match(line)
        if category_hit:
            category = CATEGORY_ALIASES[category_hit.group(1).lower()]
            court = None
            continue

        court_hit = COURT_RE.match(line)
        if court_hit:
            court = int(court_hit.group(1))
            continue

        match_hit = MATCH_RE.match(line)
        if match_hit:
            if category is None:
                result.errors.append(
                    f"Línea {line_number}: hay un partido sin categoría (Hombres/Mujeres)."
                )
                continue
            if court is None:
                result.errors.append(
                    f"Línea {line_number}: hay un partido sin cancha."
                )
                continue
            time = _normalize_time(match_hit.group(1))
            home = _clean_team(match_hit.group(2))
            away = _clean_team(match_hit.group(3))
            if not home or not away:
                result.errors.append(f"Línea {line_number}: faltan equipos.")
                continue
            key = (category, time, home.lower(), court, away.lower())
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            result.matches.append(
                Match(
                    id=len(result.matches) + 1,
                    category=category,
                    court=court,
                    time=time,
                    home=home,
                    away=away,
                )
            )
            continue

        if re.search(r"\bvs\.?\b", line, re.IGNORECASE):
            result.errors.append(
                f"Línea {line_number}: no pude leer el partido «{line}»."
            )

    teams: list[str] = []
    seen_teams: set[str] = set()
    for match in result.matches:
        for team in match.teams:
            marker = team.lower()
            if marker not in seen_teams:
                seen_teams.add(marker)
                teams.append(team)
    result.teams = teams

    if not result.matches:
        result.errors.append("No encontré partidos en el horario.")

    return result


def sort_matches(matches: list[Match], mode: str = "category") -> list[Match]:
    if mode == "court":
        return sorted(
            matches,
            key=lambda item: (item.court, item.minutes, item.category, item.id),
        )
    return sorted(
        matches,
        key=lambda item: (
            0 if item.category == "Hombres" else 1,
            item.court,
            item.minutes,
            item.id,
        ),
    )
