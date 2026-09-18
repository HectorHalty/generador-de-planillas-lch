import { readFile } from "node:fs/promises";
import path from "node:path";

import { buildSamplePdf } from "@/lib/run-processor";

export async function resolveUploadedPdf(
  file: FormDataEntryValue | null,
  source: string,
  schedule: string,
) {
  if (file instanceof File && file.size > 0) {
    return Buffer.from(await file.arrayBuffer());
  }

  const root = process.cwd();
  if (source === "ejemplo" || source === "sample") {
    try {
      return await readFile(path.join(root, "public", "planillas-ejemplo.pdf"));
    } catch {
      return buildSamplePdf(schedule);
    }
  }

  const masivo = path.join(root, "public", "planillas-masivo.pdf");
  try {
    return await readFile(masivo);
  } catch {
    if (source === "masivo") {
      throw new Error("No encuentro Planillas de Cancha - Masivo.pdf en el servidor.");
    }
  }

  throw new Error("Subí un PDF: hacé clic en el recuadro o arrastrá el archivo.");
}
