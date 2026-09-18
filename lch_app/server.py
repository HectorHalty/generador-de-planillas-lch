from __future__ import annotations

import html
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from lch_app.paths import output_pdf_path, public_dir, static_dir
from processor.dates import format_sheet_date, next_saturday, parse_iso_date
from processor.pipeline import ProcessOptions, analyze_document, generate_document
from processor.sample import write_sample_pdf

app = FastAPI(title="Generador de Planillas LCH")
STATIC = static_dir()
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    page = (static_dir() / "index.html").read_text(encoding="utf-8")
    schedule = _default_schedule()
    page = page.replace("__SCHEDULE__", html.escape(schedule))
    page = page.replace("__DATE__", next_saturday().isoformat())
    page = page.replace("__DATE_LABEL__", format_sheet_date(next_saturday()))
    return HTMLResponse(page, headers={"Cache-Control": "no-store"})


@app.get("/api/defaults")
def defaults() -> dict:
    parsed_day = next_saturday()
    return {
        "schedule": _default_schedule(),
        "date": parsed_day.isoformat(),
        "dateLabel": format_sheet_date(parsed_day),
        "hasMasivo": (public_dir() / "planillas-masivo.pdf").exists(),
        "hasEjemplo": (public_dir() / "planillas-ejemplo.pdf").exists(),
    }


@app.post("/api/analyze")
async def analyze(
    schedule: str = Form(""),
    source: str = Form("masivo"),
    pdf: UploadFile | None = File(None),
) -> JSONResponse:
    try:
        pdf_bytes = await _resolve_pdf(pdf, source, schedule)
        payload = analyze_document(pdf_bytes, schedule)
        if not payload.get("ok"):
            return JSONResponse({"error": payload.get("error") or "No pude analizar el PDF."}, status_code=400)
        return JSONResponse(_client_summary(payload))
    except Exception as error:  # noqa: BLE001
        return JSONResponse({"error": str(error)}, status_code=400)


@app.post("/api/generate")
async def generate(
    request: Request,
    schedule: str = Form(""),
    source: str = Form("masivo"),
    sort: str = Form("category"),
    index: str = Form("0"),
    blanks: str = Form("1"),
    date: str = Form(""),
    pdf: UploadFile | None = File(None),
) -> Response:
    try:
        pdf_bytes = await _resolve_pdf(pdf, source, schedule)
        options = ProcessOptions(
            sort_mode="court" if sort == "court" else "category",
            include_index=index == "1",
            create_missing=blanks != "0",
            match_date=parse_iso_date(date) or next_saturday(),
        )
        pdf_out, summary = generate_document(pdf_bytes, schedule, options)
        out = output_pdf_path()
        out.write_bytes(pdf_out)
        compact = _client_summary(summary, {"downloadUrl": "/api/output/planillas-cancha.pdf"})
        accept = (request.headers.get("accept") or "").lower()
        if "application/json" in accept or "application/pdf" not in accept:
            return JSONResponse(compact)
        headers = {
            "Content-Disposition": 'attachment; filename="planillas-cancha.pdf"',
            "X-Planillero-Summary": _header_json(compact),
            "Cache-Control": "no-store",
        }
        return Response(content=pdf_out, media_type="application/pdf", headers=headers)
    except Exception as error:  # noqa: BLE001
        return JSONResponse({"error": str(error)}, status_code=400)


@app.get("/api/output/planillas-cancha.pdf")
def download_output() -> Response:
    path = output_pdf_path()
    if not path.exists():
        return JSONResponse(
            {"error": "Todavía no armé el PDF. Tocá Armar planillas."},
            status_code=404,
        )
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="planillas-cancha.pdf",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/sample")
def sample() -> Response:
    out = public_dir() / "planillas-ejemplo.pdf"
    if out.exists():
        return Response(content=out.read_bytes(), media_type="application/pdf", headers={
            "Content-Disposition": 'attachment; filename="planillas-ejemplo.pdf"',
        })
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        path = Path(handle.name)
    write_sample_pdf(path, _default_schedule())
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="planillas-ejemplo.pdf"',
    })


def _default_schedule() -> str:
    path = public_dir() / "horario-jornada.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "Hombres:\n\nCancha 1\n11:30: Local vs Visitante\n"


async def _resolve_pdf(upload: UploadFile | None, source: str, schedule: str) -> bytes:
    if upload is not None and upload.filename:
        data = await upload.read()
        if data:
            return data
    folder = public_dir()
    if source in {"ejemplo", "sample"}:
        ejemplo = folder / "planillas-ejemplo.pdf"
        if ejemplo.exists():
            return ejemplo.read_bytes()
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            path = Path(handle.name)
        write_sample_pdf(path, schedule)
        data = path.read_bytes()
        path.unlink(missing_ok=True)
        return data
    masivo = folder / "planillas-masivo.pdf"
    if masivo.exists():
        return masivo.read_bytes()
    if source == "masivo":
        raise ValueError("No encuentro Planillas de Cancha - Masivo.pdf. Subilo con Elegir archivo.")
    raise ValueError("Subí un PDF: hacé clic en Elegir archivo o arrastralo.")


def _client_summary(summary: dict, extra: dict | None = None) -> dict:
    payload = {
        "ok": summary.get("ok"),
        "pageCount": summary.get("pageCount"),
        "outputPages": summary.get("outputPages"),
        "keptOriginalPages": summary.get("keptOriginalPages"),
        "createdPlanillas": summary.get("createdPlanillas"),
        "removedTeams": summary.get("removedTeams") or [],
        "unmatchedMatches": summary.get("unmatchedMatches") or [],
        "warnings": summary.get("warnings") or [],
        "matchDate": summary.get("matchDate"),
        "schedule": {
            "matchCount": (summary.get("schedule") or {}).get("matchCount", 0),
            "teamCount": (summary.get("schedule") or {}).get("teamCount", 0),
            "errors": (summary.get("schedule") or {}).get("errors", []),
        },
    }
    if extra:
        payload.update(extra)
    return payload


def _header_json(payload: dict) -> str:
    from urllib.parse import quote
    import json

    return quote(json.dumps(payload, ensure_ascii=False), safe="")


def run(host: str = "127.0.0.1", port: int = 43147) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")
