import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const ROOT = process.cwd();

type CliResult = {
  stdout: string;
  stderr: string;
  code: number;
};

function runPython(args: string[]): Promise<CliResult> {
  return new Promise((resolve, reject) => {
    const child = spawn("python3", ["-m", "processor.cli", ...args], {
      cwd: ROOT,
      env: { ...process.env, PYTHONPATH: ROOT, PYTHONUNBUFFERED: "1" },
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf8");
    });
    child.on("error", reject);
    child.on("close", (code) => {
      resolve({ stdout, stderr, code: code ?? 1 });
    });
  });
}

function parseJson(text: string): unknown {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end < start) {
    throw new Error(text.trim() || "El procesador no devolvió datos.");
  }
  return JSON.parse(text.slice(start, end + 1));
}

export async function parseScheduleText(schedule: string) {
  const folder = await mkdtemp(path.join(tmpdir(), "planillero-"));
  try {
    const schedulePath = path.join(folder, "horario.txt");
    await writeFile(schedulePath, schedule, "utf8");
    const result = await runPython(["parse", "--schedule", schedulePath]);
    if (result.code !== 0) {
      throw new Error(result.stderr || result.stdout || "No pude leer el horario.");
    }
    return parseJson(result.stdout);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
}

export async function analyzePdf(pdf: Buffer, schedule: string) {
  const folder = await mkdtemp(path.join(tmpdir(), "planillero-"));
  try {
    const pdfPath = path.join(folder, "entrada.pdf");
    const schedulePath = path.join(folder, "horario.txt");
    await writeFile(pdfPath, pdf);
    await writeFile(schedulePath, schedule, "utf8");
    const result = await runPython([
      "analyze",
      "--pdf",
      pdfPath,
      "--schedule",
      schedulePath,
    ]);
    if (result.code !== 0) {
      throw new Error(result.stderr || result.stdout || "No pude analizar el PDF.");
    }
    return parseJson(result.stdout);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
}

export async function generatePdf(options: {
  pdf: Buffer;
  schedule: string;
  sort: "category" | "court";
  includeIndex: boolean;
  createMissing: boolean;
}) {
  const folder = await mkdtemp(path.join(tmpdir(), "planillero-"));
  try {
    const pdfPath = path.join(folder, "entrada.pdf");
    const schedulePath = path.join(folder, "horario.txt");
    const outPath = path.join(folder, "planillas.pdf");
    await writeFile(pdfPath, options.pdf);
    await writeFile(schedulePath, options.schedule, "utf8");
    const args = [
      "generate",
      "--pdf",
      pdfPath,
      "--schedule",
      schedulePath,
      "--out",
      outPath,
      "--sort",
      options.sort,
    ];
    if (!options.includeIndex) args.push("--no-index");
    if (!options.createMissing) args.push("--no-blanks");
    const result = await runPython(args);
    if (result.code !== 0) {
      throw new Error(result.stderr || result.stdout || "No pude armar el PDF.");
    }
    const pdf = await readFile(outPath);
    const summaryRaw = await readFile(path.join(folder, "planillas.json"), "utf8");
    return { pdf, summary: JSON.parse(summaryRaw) };
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
}

export async function buildSamplePdf(schedule: string) {
  const folder = await mkdtemp(path.join(tmpdir(), "planillero-"));
  try {
    const schedulePath = path.join(folder, "horario.txt");
    const outPath = path.join(folder, "ejemplo.pdf");
    await writeFile(schedulePath, schedule, "utf8");
    const result = await runPython([
      "sample",
      "--schedule",
      schedulePath,
      "--out",
      outPath,
    ]);
    if (result.code !== 0) {
      throw new Error(result.stderr || result.stdout || "No pude crear el PDF de ejemplo.");
    }
    return readFile(outPath);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
}
