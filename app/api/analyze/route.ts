import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { analyzePdf, buildSamplePdf } from "@/lib/run-processor";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const schedule = String(form.get("schedule") ?? "");
    const useSample = String(form.get("sample") ?? "") === "1";
    const file = form.get("pdf");
    const pdf = await resolvePdf(file, useSample, schedule);
    const payload = await analyzePdf(pdf, schedule);
    return NextResponse.json(payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "No pude analizar el documento.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}

async function resolvePdf(file: FormDataEntryValue | null, useSample: boolean, schedule: string) {
  if (file instanceof File && file.size > 0) {
    return Buffer.from(await file.arrayBuffer());
  }
  if (useSample) {
    const samplePath = path.join(process.cwd(), "public", "planillas-ejemplo.pdf");
    try {
      return await readFile(samplePath);
    } catch {
      return buildSamplePdf(schedule);
    }
  }
  throw new Error("Subí un PDF o usá la planilla de ejemplo.");
}
