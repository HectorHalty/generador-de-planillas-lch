import { NextResponse } from "next/server";

import { htmlResponse, renderErrorPage, wantsHtml } from "@/lib/form-html";
import { resolveUploadedPdf } from "@/lib/pdf-source";
import { generatePdf } from "@/lib/run-processor";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(request: Request) {
  const html = wantsHtml(request);
  try {
    const form = await request.formData();
    const schedule = String(form.get("schedule") ?? "");
    const source = String(form.get("source") ?? (form.get("sample") === "1" ? "ejemplo" : "masivo"));
    const sort = String(form.get("sort") ?? "category") === "court" ? "court" : "category";
    const includeIndex = String(form.get("index") ?? "0") === "1";
    const createMissing = String(form.get("blanks") ?? "1") !== "0";
    const matchDate = String(form.get("date") ?? "").trim();
    const file = form.get("pdf");
    const pdf = await resolveUploadedPdf(file, source, schedule);
    const result = await generatePdf({
      pdf,
      schedule,
      sort,
      includeIndex,
      createMissing,
      matchDate: matchDate || undefined,
    });
    const compact = compactSummary(result.summary);
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

function compactSummary(summary: Record<string, unknown>) {
  const schedule = (summary.schedule ?? {}) as Record<string, unknown>;
  return {
    ok: summary.ok,
    pageCount: summary.pageCount,
    outputPages: summary.outputPages,
    keptOriginalPages: summary.keptOriginalPages,
    createdPlanillas: summary.createdPlanillas,
    matchDate: summary.matchDate,
    removedTeams: summary.removedTeams,
    unmatchedMatches: summary.unmatchedMatches,
    warnings: summary.warnings,
    keptPages: summary.keptPages,
    removedPages: summary.removedPages,
    schedule: {
      matchCount: schedule.matchCount ?? 0,
      teamCount: schedule.teamCount ?? 0,
      errors: schedule.errors ?? [],
      matches: [],
      teams: [],
    },
  };
}
