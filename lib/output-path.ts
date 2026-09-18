import path from "node:path";

export const OUTPUT_PDF_NAME = "planillas-cancha.pdf";
export const OUTPUT_PDF_URL = `/api/output/${OUTPUT_PDF_NAME}`;

export function outputPdfPath() {
  return path.join(process.cwd(), ".lch-output", OUTPUT_PDF_NAME);
}
