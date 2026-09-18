from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pymupdf as fitz

from processor.assign import AssignmentResult, assign_pages
from processor.dates import format_sheet_date, next_saturday
from processor.planilla import draw_index_pages, draw_match_planilla
from processor.schedule import Match, ParseResult, parse_schedule, sort_matches
from processor.stamp import stamp_page


@dataclass
class ProcessOptions:
    sort_mode: str = "category"
    include_index: bool = False
    create_missing: bool = True
    match_date: date | None = None


def analyze_document(pdf_bytes: bytes, schedule_text: str) -> dict:
    parsed = parse_schedule(schedule_text)
    if not parsed.matches:
        return {
            "ok": False,
            "schedule": parsed.to_dict(),
            "error": parsed.errors[0] if parsed.errors else "Horario vacío",
        }

    page_texts, page_count = _extract_page_texts(pdf_bytes)
    assignment = assign_pages(page_texts, parsed.matches)
    payload = _summary(parsed, assignment, page_count)
    payload["ok"] = True
    return payload


def generate_document(
    pdf_bytes: bytes,
    schedule_text: str,
    options: ProcessOptions | None = None,
) -> tuple[bytes, dict]:
    options = options or ProcessOptions()
    parsed = parse_schedule(schedule_text)
    if not parsed.matches:
        raise ValueError(parsed.errors[0] if parsed.errors else "Horario vacío")

    matches = sort_matches(parsed.matches, options.sort_mode)
    source = fitz.open(stream=pdf_bytes, filetype="pdf") if pdf_bytes else fitz.open()
    page_texts = [page.get_text("text") or "" for page in source]
    assignment = assign_pages(page_texts, parsed.matches)
    day = format_sheet_date(options.match_date or next_saturday())

    output = fitz.open()
    if options.include_index:
        draw_index_pages(output, matches)

    kept_original = 0
    created_blank = 0
    for match in matches:
        page_indexes = assignment.match_pages.get(match.id, [])
        if page_indexes:
            for page_index in page_indexes:
                output.insert_pdf(source, from_page=page_index, to_page=page_index)
                stamp_page(output[-1], match, day=day)
                kept_original += 1
        elif options.create_missing:
            draw_match_planilla(output, match, day=day)
            created_blank += 1

    source.close()
    pdf_out = output.tobytes()
    output.close()

    summary = _summary(parsed, assignment, len(page_texts))
    summary["ok"] = True
    summary["outputPages"] = _page_count(pdf_out)
    summary["keptOriginalPages"] = kept_original
    summary["createdPlanillas"] = created_blank
    summary["matchDate"] = day
    return pdf_out, summary


def _extract_page_texts(pdf_bytes: bytes) -> tuple[list[str], int]:
    if not pdf_bytes:
        return [], 0
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    texts = [page.get_text("text") or "" for page in document]
    count = document.page_count
    document.close()
    return texts, count


def _page_count(pdf_bytes: bytes) -> int:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = document.page_count
    document.close()
    return count


def _summary(parsed: ParseResult, assignment: AssignmentResult, page_count: int) -> dict:
    matches_by_id = {match.id: match for match in parsed.matches}
    removed_pages = [
        {
            "page": page.index + 1,
            "teams": page.matched_teams,
            "extraTeams": page.extra_teams,
            "reason": page.reason,
        }
        for page in assignment.pages
        if page.action == "drop"
    ]
    unmatched = [matches_by_id[match_id].to_dict() for match_id in assignment.unmatched_matches]
    return {
        "schedule": parsed.to_dict(),
        "pageCount": page_count,
        "removedPages": removed_pages,
        "removedTeams": assignment.removed_teams,
        "unmatchedMatches": unmatched,
        "warnings": assignment.warnings + parsed.errors,
        "keptPages": [
            {
                "page": page.index + 1,
                "matchId": page.match_id,
                "teams": page.matched_teams,
                "reason": page.reason,
            }
            for page in assignment.pages
            if page.action == "keep"
        ],
    }


def load_default_schedule(root: Path | None = None) -> str:
    base = root or Path(__file__).resolve().parent.parent
    return (base / "public" / "horario-jornada.txt").read_text(encoding="utf-8")
