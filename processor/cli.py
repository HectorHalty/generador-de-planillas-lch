from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from processor.pipeline import ProcessOptions, analyze_document, generate_document, load_default_schedule
from processor.sample import write_sample_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Armar planillas de cancha desde un PDF y un horario.")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze")
    _add_io_args(analyze)

    generate = sub.add_parser("generate")
    _add_io_args(generate)
    generate.add_argument("--out", required=True)
    generate.add_argument("--sort", choices=("category", "court"), default="category")
    generate.add_argument("--date", help="Fecha de la jornada (YYYY-MM-DD). Por defecto, el sábado próximo.")
    index_group = generate.add_mutually_exclusive_group()
    index_group.add_argument(
        "--index",
        dest="include_index",
        action="store_true",
        help="Agregar las hojas de cruces al frente.",
    )
    index_group.add_argument(
        "--no-index",
        dest="include_index",
        action="store_false",
        help="No incluir las hojas de cruces (predeterminado).",
    )
    generate.set_defaults(include_index=False)
    generate.add_argument("--no-blanks", action="store_true")

    sample = sub.add_parser("sample")
    sample.add_argument("--out", required=True)
    sample.add_argument("--schedule")

    parse = sub.add_parser("parse")
    parse.add_argument("--schedule")

    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent

    if args.command == "sample":
        schedule = Path(args.schedule).read_text(encoding="utf-8") if args.schedule else load_default_schedule(root)
        write_sample_pdf(Path(args.out), schedule)
        return 0

    if args.command == "parse":
        from processor.schedule import parse_schedule

        text = Path(args.schedule).read_text(encoding="utf-8") if args.schedule else sys.stdin.read()
        print(json.dumps(parse_schedule(text).to_dict(), ensure_ascii=False))
        return 0

    pdf_bytes = Path(args.pdf).read_bytes() if args.pdf else b""
    schedule = Path(args.schedule).read_text(encoding="utf-8") if args.schedule else load_default_schedule(root)

    if args.command == "analyze":
        print(json.dumps(analyze_document(pdf_bytes, schedule), ensure_ascii=False))
        return 0

    from processor.dates import parse_iso_date

    options = ProcessOptions(
        sort_mode=args.sort,
        include_index=args.include_index,
        create_missing=not args.no_blanks,
        match_date=parse_iso_date(args.date),
    )
    pdf_out, summary = generate_document(pdf_bytes, schedule, options)
    Path(args.out).write_bytes(pdf_out)
    summary_path = Path(args.out).with_suffix(".json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "out": args.out, "summary": str(summary_path)}, ensure_ascii=False))
    return 0


def _add_io_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pdf")
    parser.add_argument("--schedule")


if __name__ == "__main__":
    raise SystemExit(main())
