import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { htmlResponse, renderErrorPage, wantsHtml } from "@/lib/form-html";
import { OUTPUT_PDF_URL, outputPdfPath } from "@/lib/output-path";
import { resolveUploadedPdf } from "@/lib/pdf-source";
import { generatePdf } from "@/lib/run-processor";
import { compactClientSummary } from "@/lib/summary";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(request: Request) {
  const html = wantsHtml(request);
  try {
    const form = await request.formData();
    const schedule = String(form.get("schedule") ?? "");
    const source = String(form.get("source") ?? (form.get("sample") === "1" ? "ejemplo" : "masivo"));
    const sort = String(form.get("sort") ?? "category") === "court" ? "court" : "category";
    const includeIndex = false;
    const createMissing = false;
    const matchDate = String(form.get("date") ?? "").trim();
    const players = String(form.get("players") ?? "");
    const file = form.get("pdf");
    const pdf = await resolveUploadedPdf(file, source, schedule);
    const result = await generatePdf({
      pdf,
      schedule,
      sort,
      includeIndex,
      createMissing,
      matchDate: matchDate || undefined,
      players,
    });
    const outPath = outputPdfPath();
    await mkdir(path.dirname(outPath), { recursive: true });
    await writeFile(outPath, result.pdf);
    const compact = compactClientSummary(result.summary as Record<string, unknown>, {
      downloadUrl: OUTPUT_PDF_URL,
    });
    const accept = (request.headers.get("accept") ?? "").toLowerCase();
    if (html) {
      return htmlResponse(renderDownloadPage(compact));
    }
    if (accept.includes("application/json") || !accept.includes("application/pdf")) {
      return NextResponse.json(compact);
    }
    const bytes = new Uint8Array(result.pdf);
    return new NextResponse(bytes, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": 'attachment; filename="planillas-cancha.pdf"',
        "Cache-Control": "no-store",
        "X-Planillero-Summary": encodeURIComponent(JSON.stringify(compact)),
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "No pude armar el documento.";
    if (html) return htmlResponse(renderErrorPage(message), 400);
    return NextResponse.json({ error: message }, { status: 400 });
  }
}

function renderDownloadPage(summary: Record<string, unknown>) {
  const downloadUrl = String(summary.downloadUrl ?? OUTPUT_PDF_URL);
  return `<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta http-equiv="refresh" content="0;url=${downloadUrl}" />
    <title>Planillas listas</title>
  </head>
  <body>
    <p>PDF listo. Si no se baja solo, <a href="${downloadUrl}">tocá acá</a>.</p>
  </body>
</html>`;
}
