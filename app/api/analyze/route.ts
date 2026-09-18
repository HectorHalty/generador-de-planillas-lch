import { NextResponse } from "next/server";

import { resolveUploadedPdf } from "@/lib/pdf-source";
import { analyzePdf } from "@/lib/run-processor";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const schedule = String(form.get("schedule") ?? "");
    const source = String(form.get("source") ?? (form.get("sample") === "1" ? "ejemplo" : "masivo"));
    const file = form.get("pdf");
    const pdf = await resolveUploadedPdf(file, source, schedule);
    const payload = await analyzePdf(pdf, schedule);
    return NextResponse.json(payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "No pude analizar el documento.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
