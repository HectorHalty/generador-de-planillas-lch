import { NextResponse } from "next/server";

import { htmlResponse, renderAnalyzePage, renderErrorPage, wantsHtml } from "@/lib/form-html";
import { resolveUploadedPdf } from "@/lib/pdf-source";
import { readProcessRequest } from "@/lib/read-process-request";
import { analyzePdf } from "@/lib/run-processor";
import { compactClientSummary } from "@/lib/summary";
import type { ProcessSummary } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  const html = wantsHtml(request);
  try {
    const fields = await readProcessRequest(request);
    const { schedule, source, sort, date, players, file } = fields;
    const pdf = await resolveUploadedPdf(file, source, schedule);
    const payload = (await analyzePdf(pdf, schedule, players)) as ProcessSummary;
    const compact = compactClientSummary(payload as unknown as Record<string, unknown>) as ProcessSummary;
    if (html) {
      return htmlResponse(
        renderAnalyzePage(compact, { schedule, source, sort, date, players }),
      );
    }
    return NextResponse.json(compact);
  } catch (error) {
    const message = error instanceof Error ? error.message : "No pude analizar el documento.";
    if (html) return htmlResponse(renderErrorPage(message), 400);
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
