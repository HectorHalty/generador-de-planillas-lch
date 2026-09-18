import { readFile } from "node:fs/promises";

import { NextResponse } from "next/server";

import { OUTPUT_PDF_NAME, outputPdfPath } from "@/lib/output-path";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ file: string }> },
) {
  const { file } = await context.params;
  if (file !== OUTPUT_PDF_NAME) {
    return NextResponse.json({ error: "No encuentro ese archivo." }, { status: 404 });
  }
  try {
    const data = await readFile(outputPdfPath());
    return new NextResponse(data, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${OUTPUT_PDF_NAME}"`,
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Todavía no armé el PDF. Tocá Armar planillas." },
      { status: 404 },
    );
  }
}
