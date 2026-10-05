from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile as StarletteUploadFile

from lch_app.paths import alias_paths, output_pdf_path, public_dir, static_dir
from processor.dates import format_sheet_date, next_saturday, parse_iso_date
from processor.pipeline import ProcessOptions, analyze_document, generate_document
from processor.players import parse_player_marks
from processor.sample import write_sample_pdf
from processor.turnos_xlsx import (
    TurnosResult,
    build_schedule_text,
    clubs_from_page_texts,
    load_manual_aliases,
)

app = FastAPI(title="Generador de Planillas LCH")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Planillero-Summary"],
)
STATIC = static_dir()
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    page = (static_dir() / "index.html").read_text(encoding="utf-8")
    page = page.replace("__DATE__", next_saturday().isoformat())
    page = page.replace("__DATE_LABEL__", format_sheet_date(next_saturday()))
    return HTMLResponse(page, headers={"Cache-Control": "no-store"})


@app.get("/api/defaults")
def defaults() -> dict:
    parsed_day = next_saturday()
    return {
        "date": parsed_day.isoformat(),
        "dateLabel": format_sheet_date(parsed_day),
        "hasMasivo": (public_dir() / "planillas-masivo.pdf").exists(),
        "hasEjemplo": (public_dir() / "planillas-ejemplo.pdf").exists(),
    }


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "hasMasivo": (public_dir() / "planillas-masivo.pdf").exists()}


@app.post("/api/analyze")
async def analyze(request: Request) -> JSONResponse:
    try:
        fields, uploads = await _read_request_fields(request)
        source = fields.get("source", "masivo") or "masivo"
        players = fields.get("players", "")
        pdf_bytes = await _resolve_pdf(uploads.get("pdf"), source)
        turnos = await _resolve_turnos(uploads.get("turnos"), pdf_bytes)
        marked, parse_errors = parse_player_marks(players)
        payload = analyze_document(pdf_bytes, turnos.text, players=marked)
        if not payload.get("ok"):
            return JSONResponse({"error": payload.get("error") or "No pude analizar el PDF."}, status_code=400)
        payload["warnings"] = [*turnos.warnings, *(payload.get("warnings") or []), *parse_errors]
        return JSONResponse(_client_summary(payload, {"turnos": turnos.to_dict()}))
    except Exception as error:  # noqa: BLE001
        return JSONResponse({"error": str(error)}, status_code=400)


@app.post("/api/generate")
async def generate(request: Request) -> Response:
    try:
        fields, uploads = await _read_request_fields(request)
        source = fields.get("source", "masivo") or "masivo"
        sort = fields.get("sort", "category")
        date = fields.get("date", "")
        players = fields.get("players", "")
        pdf_bytes = await _resolve_pdf(uploads.get("pdf"), source)
        turnos = await _resolve_turnos(uploads.get("turnos"), pdf_bytes)
        marked, parse_errors = parse_player_marks(players)
        options = ProcessOptions(
            sort_mode="court" if sort == "court" else "category",
            include_index=False,
            create_missing=False,
            match_date=parse_iso_date(date) or next_saturday(),
            players=marked,
        )
        pdf_out, summary = generate_document(pdf_bytes, turnos.text, options)
        out = output_pdf_path()
        out.write_bytes(pdf_out)
        summary["warnings"] = [*turnos.warnings, *(summary.get("warnings") or []), *parse_errors]
        compact = _client_summary(
            summary,
            {"downloadUrl": "/api/output/planillas-cancha.pdf", "turnos": turnos.to_dict()},
        )
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


async def _read_request_fields(request: Request) -> tuple[dict[str, str], dict[str, UploadFile]]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            raw = await request.json()
        except Exception as error:  # noqa: BLE001
            raise ValueError("No pude leer el pedido. Recargá la página e intentá de nuevo.") from error
        if not isinstance(raw, dict):
            raise ValueError("El pedido JSON tiene que ser un objeto.")
        fields = {str(key): "" if value is None else str(value) for key, value in raw.items()}
        return fields, {}

    try:
        form = await request.form()
    except Exception as error:  # noqa: BLE001
        raise ValueError("No pude leer el formulario. Recargá la página e intentá de nuevo.") from error

    uploads: dict[str, UploadFile] = {}
    fields: dict[str, str] = {}
    for key, value in form.multi_items():
        if isinstance(value, (UploadFile, StarletteUploadFile)):
            if key in {"pdf", "turnos"} and getattr(value, "filename", None):
                uploads[key] = value
            continue
        fields[str(key)] = str(value)
    return fields, uploads


async def _resolve_turnos(upload: UploadFile | None, pdf_bytes: bytes) -> TurnosResult:
    data = await upload.read() if upload is not None and upload.filename else b""
    if not data:
        raise ValueError("Subí el Excel de turnos y canchas (elegilo en el paso 2).")
    clubs = clubs_from_page_texts(_pdf_page_texts(pdf_bytes))
    if not any(clubs.values()):
        raise ValueError("El masivo no tiene líneas «Club: …»: no puedo identificar los equipos del Excel.")
    result = build_schedule_text(data, clubs, load_manual_aliases(alias_paths()))
    if not result.matches:
        raise ValueError(result.warnings[0] if result.warnings else "No encontré partidos en el Excel.")
    return result


def _pdf_page_texts(pdf_bytes: bytes) -> list[str]:
    import pymupdf

    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        return [page.get_text("text") or "" for page in document]
    finally:
        document.close()


async def _resolve_pdf(upload: UploadFile | None, source: str) -> bytes:
    if upload is not None and upload.filename:
        data = await upload.read()
        if data:
            return data
    folder = public_dir()
    if source in {"ejemplo", "sample"}:
        ejemplo = folder / "planillas-ejemplo.pdf"
        if ejemplo.exists():
            return ejemplo.read_bytes()
        raise ValueError("No encuentro el PDF de ejemplo.")
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
        "playerMarks": summary.get("playerMarks") or [],
        "matchDate": summary.get("matchDate"),
        "schedule": {
            "matchCount": (summary.get("schedule") or {}).get("matchCount", 0),
            "teamCount": (summary.get("schedule") or {}).get("teamCount", 0),
            "matches": (summary.get("schedule") or {}).get("matches", []),
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

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        timeout_keep_alive=120,
        timeout_graceful_shutdown=10,
    )
