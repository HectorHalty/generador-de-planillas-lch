import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { buildSamplePdf } from "@/lib/run-processor";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function GET() {
  const samplePath = path.join(process.cwd(), "public", "planillas-ejemplo.pdf");
  try {
    const pdf = await readFile(samplePath);
    return pdfResponse(pdf);
  } catch {
    const schedule = await readFile(
      path.join(process.cwd(), "public", "horario-jornada.txt"),
      "utf8",
    );
    const pdf = await buildSamplePdf(schedule);
    return pdfResponse(pdf);
  }
}

function pdfResponse(pdf: Buffer) {
  return new NextResponse(new Uint8Array(pdf), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": 'attachment; filename="planillas-ejemplo.pdf"',
    },
  });
}
