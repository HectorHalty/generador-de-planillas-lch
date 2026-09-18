import { NextResponse } from "next/server";

import { parseScheduleText } from "@/lib/run-processor";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const schedule = String(body.schedule ?? "");
    const payload = await parseScheduleText(schedule);
    return NextResponse.json(payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "No pude leer el horario.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
