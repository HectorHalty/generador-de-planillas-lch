export type ProcessRequestFields = {
  schedule: string;
  source: string;
  sort: string;
  date: string;
  players: string;
  file: FormDataEntryValue | null;
};

export async function readProcessRequest(request: Request): Promise<ProcessRequestFields> {
  const contentType = request.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const body = (await request.json()) as Record<string, unknown>;
    return {
      schedule: String(body.schedule ?? ""),
      source: String(body.source ?? "masivo"),
      sort: String(body.sort ?? "category"),
      date: String(body.date ?? ""),
      players: String(body.players ?? ""),
      file: null,
    };
  }

  const form = await request.formData();
  const uploaded = form.get("pdf");
  const file = uploaded instanceof File && uploaded.size > 0 ? uploaded : null;
  return {
    schedule: String(form.get("schedule") ?? ""),
    source: String(form.get("source") ?? (form.get("sample") === "1" ? "ejemplo" : "masivo")),
    sort: String(form.get("sort") ?? "category"),
    date: String(form.get("date") ?? ""),
    players: String(form.get("players") ?? ""),
    file,
  };
}
