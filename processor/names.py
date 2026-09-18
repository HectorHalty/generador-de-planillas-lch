from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

SUFFIXES = re.compile(r"\b(f\.?\s*c\.?|c\.?\s*f\.?|club|a\.?\s*f\.?|l\.?\s*v\.?)\b")
NON_ALNUM = re.compile(r"[^a-z0-9]+")
APOSTROPHES = str.maketrans("", "", "´’‘`'ʼ′")


def normalize_name(name: str) -> str:
    text = (name or "").strip().lower().translate(APOSTROPHES)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace(".", " ")
    text = SUFFIXES.sub(" ", text)
    text = NON_ALNUM.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def token_boundary_hit(needle: str, haystack: str) -> bool:
    if not needle:
        return False
    if needle in haystack:
        if len(needle) <= 4:
            return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None
        return True
    return False


def score_team_in_text(team: str, page_text: str) -> float:
    needle = normalize_name(team)
    haystack = normalize_name(page_text)
    if not needle or not haystack:
        return 0.0
    if token_boundary_hit(needle, haystack):
        return 100.0
    return 0.0


def find_teams_in_text(
    page_text: str,
    teams: list[str],
    *,
    cutoff: float = 90.0,
) -> list[tuple[str, float]]:
    hits: list[tuple[str, float]] = []
    for team in teams:
        score = score_team_in_text(team, page_text)
        if score >= cutoff:
            hits.append((team, score))
    hits.sort(key=lambda item: item[1], reverse=True)
    return hits


def names_equivalent(left: str, right: str) -> bool:
    a, b = normalize_name(left), normalize_name(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return fuzz.ratio(a, b) >= 94
