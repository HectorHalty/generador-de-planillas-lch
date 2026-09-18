"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  CalendarDays,
  Download,
  FileText,
  LoaderCircle,
  MapPinned,
  Trash2,
  Upload,
  Users,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import type { MatchInfo, ProcessSummary, SchedulePayload } from "@/lib/types";
import { parseSchedule } from "@/lib/parse-schedule";
import { formatSheetDate } from "@/lib/dates";
import { cn } from "@/lib/utils";

type Props = {
  defaultSchedule: string;
  defaultMatchDate: string;
};

export function PlanilleroApp({ defaultSchedule, defaultMatchDate }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [schedule, setSchedule] = useState(defaultSchedule);
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState<"masivo" | "ejemplo" | "upload">("masivo");
  const [dragOver, setDragOver] = useState(false);
  const [sortMode, setSortMode] = useState<"category" | "court">("category");
  const [includeIndex, setIncludeIndex] = useState(false);
  const [createMissing, setCreateMissing] = useState(true);
  const [matchDate, setMatchDate] = useState(defaultMatchDate);
  const [parsed, setParsed] = useState<SchedulePayload>(() => parseSchedule(defaultSchedule));
  const [parseError, setParseError] = useState<string | null>(
    () => parseSchedule(defaultSchedule).errors[0] ?? null,
  );
  const [busy, setBusy] = useState<"analyze" | "generate" | null>(null);
  const [summary, setSummary] = useState<ProcessSummary | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const next = parseSchedule(schedule);
    setParsed(next);
    setParseError(next.errors[0] ?? null);
  }, [schedule]);

  useEffect(() => {
    return () => {
      if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    };
  }, [downloadUrl]);

  const grouped = useMemo(() => groupMatches(parsed.matches), [parsed]);
  const sourceLabel =
    file?.name ??
    (source === "masivo"
      ? "Planillas de Cancha - Masivo.pdf"
      : source === "ejemplo"
        ? "Planilla de ejemplo"
        : "Sin documento");

  function onPickFile(next: File | null, nextSource: "masivo" | "ejemplo" | "upload" = "upload") {
    setFile(next);
    setSource(next ? "upload" : nextSource);
    setSummary(null);
    setError(null);
    if (!next && inputRef.current) inputRef.current.value = "";
    if (downloadUrl) {
      URL.revokeObjectURL(downloadUrl);
      setDownloadUrl(null);
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const kind = submitter?.value === "generate" ? "generate" : "analyze";
    event.preventDefault();
    void submit(kind);
  }

  async function submit(kind: "analyze" | "generate") {
    setBusy(kind);
    setError(null);
    try {
      if (!parsed.matchCount) {
        throw new Error("El horario no tiene partidos. Revisá el texto de canchas y horarios.");
      }
      const form = new FormData();
      form.set("schedule", schedule);
      form.set("source", file ? "upload" : source);
      form.set("sort", sortMode);
      form.set("index", includeIndex ? "1" : "0");
      form.set("blanks", createMissing ? "1" : "0");
      form.set("date", matchDate);
      if (file) form.set("pdf", file);

      if (kind === "analyze") {
        const response = await fetch("/api/analyze", {
          method: "POST",
          body: form,
          headers: { Accept: "application/json" },
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "No pude analizar el PDF.");
        setSummary(payload as ProcessSummary);
        return;
      }

      const response = await fetch("/api/generate", {
        method: "POST",
        body: form,
        headers: { Accept: "application/pdf,application/json" },
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({ error: "No pude armar el PDF." }));
        throw new Error(payload.error || "No pude armar el PDF.");
      }
      const header = response.headers.get("X-Planillero-Summary");
      if (header) {
        setSummary(JSON.parse(decodeURIComponent(header)) as ProcessSummary);
      }
      const blob = await response.blob();
      if (downloadUrl) URL.revokeObjectURL(downloadUrl);
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
      const link = document.createElement("a");
      link.href = url;
      link.download = "planillas-cancha.pdf";
      link.click();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Algo salió mal.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="min-h-full bg-background">
      <header className="border-b border-white/10 bg-[var(--pitch)] text-primary-foreground">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-8 sm:px-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-medium tracking-[0.28em] uppercase text-[oklch(0.86_0.05_145)]">
              Mesa de control
            </p>
            <h1 className="font-heading text-4xl leading-none sm:text-5xl">Planillero</h1>
            <p className="max-w-xl text-sm text-primary-foreground/80">
              El masivo de esta jornada ya está cargado. Si querés usar otro PDF, elegilo abajo.
              El documento nuevo queda ordenado, con cancha, hora y el sábado de la jornada,
              sin las hojas de cruces ni la franja de margen.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatChip icon={Users} label="Partidos" value={parsed.matchCount || "—"} />
            <StatChip icon={MapPinned} label="Equipos" value={parsed.teamCount || "—"} />
            <StatChip
              icon={Trash2}
              label="A borrar"
              value={summary?.removedTeams.length ?? "—"}
            />
          </div>
        </div>
      </header>

      <form
        action="/api/generate"
        method="post"
        encType="multipart/form-data"
        onSubmit={handleSubmit}
      >
        <input type="hidden" name="source" value={file ? "upload" : source} />
        <input type="hidden" name="sort" value={sortMode} />
        <input type="hidden" name="index" value={includeIndex ? "1" : "0"} />
        <input type="hidden" name="blanks" value={createMissing ? "1" : "0"} />

        <div className="sticky top-0 z-20 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
          <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-2">
            <SubmitAction
              id="preview-planillas"
              value="analyze"
              formAction="/api/analyze"
              variant="outline"
              busy={busy === "analyze"}
              disabled={busy !== null}
              idleIcon={Users}
              idleLabel="Previsualizar"
              busyLabel="Leyendo el PDF…"
            />
            <SubmitAction
              id="armar-planillas"
              value="generate"
              formAction="/api/generate"
              busy={busy === "generate"}
              disabled={busy !== null}
              idleIcon={Download}
              idleLabel="Armar planillas"
              busyLabel="Armando el PDF…"
            />
            {downloadUrl ? (
              <a
                className={cn(buttonVariants({ variant: "secondary" }))}
                href={downloadUrl}
                download="planillas-cancha.pdf"
              >
                Descargar de nuevo
              </a>
            ) : null}
            {busy ? (
              <p className="text-sm">
                {busy === "analyze"
                  ? "Estoy leyendo las planillas…"
                  : "Estoy armando el PDF nuevo…"}
              </p>
            ) : (
              <p className="text-muted-foreground text-sm">
                {parsed.matchCount} partidos · documento {sourceLabel}
              </p>
            )}
          </div>
        </div>

        <main className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="space-y-6">
            <Card className="bg-card/90">
              <CardHeader>
                <CardTitle>1. Cómo subir el PDF</CardTitle>
                <CardDescription>
                  El archivo que mandaste,{" "}
                  <span className="font-medium">Planillas de Cancha - Masivo.pdf</span>, ya está
                  en el servidor. Para reemplazarlo: Elegir archivo → Descargas → Abrir.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <label
                  htmlFor="pdf-file"
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(event) => {
                    event.preventDefault();
                    setDragOver(false);
                    const next = event.dataTransfer.files[0];
                    if (next) onPickFile(next);
                  }}
                  className={cn(
                    "flex w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-4 py-8 text-center transition-colors",
                    dragOver
                      ? "border-primary bg-secondary"
                      : "border-border bg-[oklch(0.97_0.015_95)] hover:border-primary/50",
                  )}
                >
                  <Upload className="size-6 text-primary" />
                  <div>
                    <p className="font-medium">{sourceLabel}</p>
                    <p className="text-muted-foreground text-sm">
                      {file
                        ? "Listo. Si no es ese, elegí otro PDF abajo."
                        : source === "masivo"
                          ? "Ya está el masivo de esta jornada. Solo subí otro si querés reemplazarlo."
                          : "Clic acá o usá Elegir archivo. También sirve arrastrarlo."}
                    </p>
                  </div>
                </label>
                <input
                  ref={inputRef}
                  id="pdf-file"
                  name="pdf"
                  type="file"
                  accept="application/pdf,.pdf"
                  className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-foreground"
                  onChange={(event) => {
                    const next = event.target.files?.[0];
                    if (next) onPickFile(next);
                  }}
                />
                <ol className="text-muted-foreground list-decimal space-y-1 pl-5 text-sm">
                  <li>Tocá <span className="font-medium text-foreground">Elegir archivo</span>.</li>
                  <li>
                    En el explorador andá a <span className="font-medium text-foreground">Descargas</span>.
                  </li>
                  <li>
                    Elegí <span className="font-medium text-foreground">Planillas de Cancha - Masivo.pdf</span> y
                    Abrir.
                  </li>
                  <li>Revisá el horario y tocá <span className="font-medium text-foreground">Armar planillas</span>.</li>
                </ol>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant={source === "masivo" && !file ? "default" : "outline"}
                    onClick={() => onPickFile(null, "masivo")}
                  >
                    <FileText data-icon="inline-start" />
                    Usar el masivo
                  </Button>
                  <Button
                    type="button"
                    variant={source === "ejemplo" && !file ? "default" : "outline"}
                    onClick={() => onPickFile(null, "ejemplo")}
                  >
                    Ejemplo de prueba
                  </Button>
                  <a className={cn(buttonVariants({ variant: "outline" }))} href="/api/sample">
                    Descargar ejemplo
                  </a>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>2. Horario por cancha</CardTitle>
                <CardDescription>
                  Pegá la lista o editá la jornada. Formato: categoría, cancha, y
                  <span className="font-mono"> hora: Local vs Visitante</span>.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  name="schedule"
                  value={schedule}
                  onChange={(event) => setSchedule(event.target.value)}
                  className="field-sizing-fixed h-64 resize-y overflow-auto font-mono text-xs leading-5"
                  aria-label="Horario de canchas"
                />
                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setSchedule(defaultSchedule)}
                  >
                    Restaurar jornada
                  </Button>
                  <label className="text-muted-foreground inline-flex cursor-pointer items-center gap-2 text-sm">
                    Cargar .txt
                    <input
                      type="file"
                      accept=".txt,.md,.csv"
                      className="hidden"
                      onChange={async (event) => {
                        const next = event.target.files?.[0];
                        if (!next) return;
                        setSchedule(await next.text());
                      }}
                    />
                  </label>
                  {parseError ? (
                    <p className="text-destructive text-sm">{parseError}</p>
                  ) : (
                    <p className="text-muted-foreground text-sm">
                      {parsed.matchCount
                        ? `${parsed.matchCount} partidos listos`
                        : "Leyendo horario…"}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>3. Cómo armar el PDF</CardTitle>
                <CardDescription>
                  Se conservan las hojas de equipos que sí juegan, se completa día, cancha y
                  hora, y se tiran las que no están en el horario. No se agregan las hojas de
                  cruces ni la franja de margen.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="flex flex-col gap-2 rounded-lg border border-border p-3">
                    <span className="flex items-center gap-2 font-medium">
                      <CalendarDays className="size-4 text-primary" />
                      Día de la jornada
                    </span>
                    <input
                      type="date"
                      name="date"
                      value={matchDate}
                      onChange={(event) => setMatchDate(event.target.value)}
                      className="h-9 rounded-lg border border-input bg-transparent px-2.5 text-sm"
                    />
                    <span className="text-muted-foreground text-sm">
                      Se completa el campo Día con el sábado próximo
                      {matchDate ? ` (${formatSheetDate(matchDate)})` : ""}.
                    </span>
                  </label>
                  <label className="flex items-start gap-2 rounded-lg border border-border p-3">
                    <input
                      type="checkbox"
                      className="mt-1 size-4 accent-[oklch(0.38_0.08_155)]"
                      checked={createMissing}
                      onChange={(event) => setCreateMissing(event.target.checked)}
                    />
                    <span>
                      <span className="block font-medium">Completar faltantes</span>
                      <span className="text-muted-foreground text-sm">
                        Si un partido no está en el PDF, se crea una planilla en blanco.
                      </span>
                    </span>
                  </label>
                  <label className="flex items-start gap-2 rounded-lg border border-border p-3 sm:col-span-2">
                    <input
                      type="checkbox"
                      className="mt-1 size-4 accent-[oklch(0.38_0.08_155)]"
                      checked={includeIndex}
                      onChange={(event) => setIncludeIndex(event.target.checked)}
                    />
                    <span>
                      <span className="block font-medium">Hojas de cruces al frente</span>
                      <span className="text-muted-foreground text-sm">
                        Apagado: el PDF arranca en las planillas, sin el índice de partidos ni
                        la franja de margen.
                      </span>
                    </span>
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant={sortMode === "category" ? "default" : "outline"}
                    onClick={() => setSortMode("category")}
                  >
                    Hombres, después mujeres
                  </Button>
                  <Button
                    type="button"
                    variant={sortMode === "court" ? "default" : "outline"}
                    onClick={() => setSortMode("court")}
                  >
                    Solo cancha y hora
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  <SubmitAction
                    id="preview-planillas-footer"
                    value="analyze"
                    formAction="/api/analyze"
                    variant="outline"
                    busy={busy === "analyze"}
                    disabled={busy !== null}
                    idleIcon={Users}
                    idleLabel="Previsualizar"
                    busyLabel="Leyendo el PDF…"
                  />
                  <SubmitAction
                    id="armar-planillas-footer"
                    value="generate"
                    formAction="/api/generate"
                    busy={busy === "generate"}
                    disabled={busy !== null}
                    idleIcon={Download}
                    idleLabel="Armar planillas"
                    busyLabel="Armando el PDF…"
                  />
                  {downloadUrl ? (
                    <a
                      className={cn(buttonVariants({ variant: "secondary" }))}
                      href={downloadUrl}
                      download="planillas-cancha.pdf"
                    >
                      Descargar de nuevo
                    </a>
                  ) : null}
                </div>
                {busy ? (
                  <p className="rounded-lg bg-secondary px-3 py-2 text-sm">
                    {busy === "analyze"
                      ? "Estoy leyendo las planillas. Puede tardar unos segundos."
                      : "Estoy armando el PDF nuevo. No cierres esta pestaña."}
                  </p>
                ) : null}
                {error ? (
                  <Alert variant="destructive">
                    <AlertTriangle />
                    <AlertTitle>No se pudo armar el documento</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                ) : null}
                {summary ? <SummaryPanel summary={summary} /> : null}
              </CardContent>
            </Card>
          </div>

          <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
            <Card>
              <CardHeader>
                <CardTitle>Jornada</CardTitle>
                <CardDescription>Orden de impresión según el horario cargado.</CardDescription>
              </CardHeader>
              <CardContent>
                {parsed.matches.length ? (
                  <div className="h-[min(70vh,640px)] space-y-5 overflow-auto pr-3">
                    {grouped.map((group) => (
                      <section key={`${group.category}-${group.court}`}>
                        <div className="mb-2 flex items-center justify-between gap-2">
                          <p className="font-heading text-base">
                            {group.category} · Cancha {group.court}
                          </p>
                          <Badge variant="secondary">{group.matches.length}</Badge>
                        </div>
                        <ul className="space-y-2">
                          {group.matches.map((match) => (
                            <li
                              key={match.id}
                              className="rounded-lg border border-border bg-[oklch(0.99_0.01_95)] px-3 py-2"
                            >
                              <p className="flex items-center gap-1 text-xs font-medium text-primary">
                                <Clock3 className="size-3.5" />
                                {match.time}
                              </p>
                              <p className="text-sm leading-snug">
                                {match.home}
                                <span className="text-muted-foreground"> vs </span>
                                {match.away}
                              </p>
                            </li>
                          ))}
                        </ul>
                      </section>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm">
                    Cuando el horario sea válido, los partidos aparecen acá agrupados por cancha.
                  </p>
                )}
              </CardContent>
            </Card>
          </aside>
        </main>
      </form>
    </div>
  );
}

function SubmitAction({
  id,
  value,
  formAction,
  variant,
  busy,
  disabled,
  idleIcon: IdleIcon,
  idleLabel,
  busyLabel,
}: {
  id: string;
  value: "analyze" | "generate";
  formAction: string;
  variant?: "outline";
  busy: boolean;
  disabled: boolean;
  idleIcon: typeof Users;
  idleLabel: string;
  busyLabel: string;
}) {
  return (
    <button
      id={id}
      type="submit"
      name="intent"
      value={value}
      formAction={formAction}
      className={cn(buttonVariants({ variant, size: "lg" }), "min-h-11 px-4")}
      disabled={disabled}
    >
      {busy ? (
        <LoaderCircle className="animate-spin" data-icon="inline-start" />
      ) : (
        <IdleIcon data-icon="inline-start" />
      )}
      {busy ? busyLabel : idleLabel}
    </button>
  );
}

function StatChip({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Users;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl bg-white/8 px-4 py-3 backdrop-blur-sm">
      <p className="flex items-center gap-1 text-[11px] tracking-wide uppercase text-primary-foreground/70">
        <Icon className="size-3.5" />
        {label}
      </p>
      <p className="font-heading text-2xl leading-none">{value}</p>
    </div>
  );
}

function SummaryPanel({ summary }: { summary: ProcessSummary }) {
  const dropped = summary.removedPages.filter((page) =>
    page.reason.toLowerCase().includes("fuera"),
  );
  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-3">
        <MiniStat label="Hojas originales" value={summary.pageCount} />
        <MiniStat label="Se conservan" value={summary.keptOriginalPages ?? summary.keptPages.length} />
        <MiniStat label="PDF final" value={summary.outputPages ?? "—"} />
      </div>
      {summary.matchDate ? (
        <p className="text-sm">
          Día completado: <span className="font-medium">{summary.matchDate}</span>
        </p>
      ) : null}
      {summary.removedTeams.length ? (
        <Alert variant="destructive">
          <Trash2 />
          <AlertTitle>Equipos fuera de la jornada</AlertTitle>
          <AlertDescription>
            {summary.removedTeams.join(" · ")}
          </AlertDescription>
        </Alert>
      ) : (
        <Alert>
          <CheckCircle2 />
          <AlertTitle>Nadie de más</AlertTitle>
          <AlertDescription>
            Todos los equipos del documento están en el horario, o el PDF se armó de cero.
          </AlertDescription>
        </Alert>
      )}
      {dropped.length ? (
        <p className="text-muted-foreground text-sm">
          Se eliminan {dropped.length} hoja{dropped.length === 1 ? "" : "s"} con equipos que no
          juegan.
        </p>
      ) : null}
      {summary.unmatchedMatches.length ? (
        <p className="text-sm">
          {summary.unmatchedMatches.length} partido
          {summary.unmatchedMatches.length === 1 ? "" : "s"} no estaban en el PDF original y
          {summary.createdPlanillas
            ? ` se crearon ${summary.createdPlanillas} planillas nuevas.`
            : " quedaron pendientes."}
        </p>
      ) : null}
      {summary.warnings.length ? (
        <ul className="text-muted-foreground list-disc space-y-1 pl-4 text-sm">
          {summary.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-secondary px-3 py-2">
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className="font-heading text-xl">{value}</p>
    </div>
  );
}

function groupMatches(matches: MatchInfo[]) {
  const groups: { category: string; court: number; matches: MatchInfo[] }[] = [];
  for (const match of matches) {
    const current = groups[groups.length - 1];
    if (current && current.category === match.category && current.court === match.court) {
      current.matches.push(match);
    } else {
      groups.push({ category: match.category, court: match.court, matches: [match] });
    }
  }
  return groups;
}
