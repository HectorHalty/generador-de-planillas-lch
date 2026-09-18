import { NextResponse } from "next/server";

import { htmlResponse, renderAnalyzePage, renderErrorPage, wantsHtml } from "@/lib/form-html";
import { resolveUploadedPdf } from "@/lib/pdf-source";
import { analyzePdf } from "@/lib/run-processor";
import type { ProcessSummary } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  const html = wantsHtml(request);
  try {
    const form = await request.formData();
    const schedule = String(form.get("schedule") ?? "");
    const source = String(form.get("source") ?? (form.get("sample") === "1" ? "ejemplo" : "masivo"));
    const sort = String(form.get("sort") ?? "category");
    const index = String(form.get("index") ?? "0");
    const blanks = String(form.get("blanks") ?? "1");
    const date = String(form.get("date") ?? "");
    const file = form.get("pdf");
    const pdf = await resolveUploadedPdf(file, source, schedule);
    const payload = (await analyzePdf(pdf, schedule)) as ProcessSummary;
    if (html) {
      return htmlResponse(
        renderAnalyzePage(payload, { schedule, source, sort, index, blanks, date }),
      );
    }
    return NextResponse.json(payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "No pude analizar el documento.";
    if (html) return htmlResponse(renderErrorPage(message), 400);
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
