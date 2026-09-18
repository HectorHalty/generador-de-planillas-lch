import type { ProcessSummary } from "@/lib/types";

export function wantsHtml(request: Request) {
  const accept = request.headers.get("accept") ?? "";
  if (accept.includes("application/json") && !accept.includes("text/html")) {
    return false;
  }
  const dest = request.headers.get("sec-fetch-dest");
  if (dest === "document" || dest === "iframe") return true;
  return accept.includes("text/html");
}

export function htmlResponse(html: string, status = 200) {
  return new Response(html, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

export function renderErrorPage(message: string) {
  return shell({
    title: "No se pudo armar el documento",
    body: `
      <div class="card">
        <p class="kicker">Error</p>
        <h1>No se pudo armar el documento</h1>
        <p>${escapeHtml(message)}</p>
        <p><a class="btn" href="/">Volver a Planillero</a></p>
      </div>
    `,
  });
}

export function renderAnalyzePage(
  summary: ProcessSummary,
  fields: {
    schedule: string;
    source: string;
    sort: string;
    index: string;
    blanks: string;
    date: string;
  },
) {
  const removed = summary.removedTeams ?? [];
  const unmatched = summary.unmatchedMatches ?? [];
  const warnings = summary.warnings ?? [];
  const dropped = (summary.removedPages ?? []).filter((page) =>
    page.reason.toLowerCase().includes("fuera"),
  );

  const extras = removed.length
    ? `<ul class="chips">${removed.map((name) => `<li>${escapeHtml(name)}</li>`).join("")}</ul>`
    : `<p>Ningún equipo de más: todos los del PDF están en el horario, o el documento se arma de cero.</p>`;

  const pending = unmatched.length
    ? `<p>${unmatched.length} partido${unmatched.length === 1 ? "" : "s"} no estaban en el PDF original.${
        summary.createdPlanillas
          ? ` Al armar, se crean ${summary.createdPlanillas} planillas nuevas.`
          : " Marcá “Completar faltantes” para crearlas."
      }</p>`
    : `<p>Los ${summary.schedule?.matchCount ?? 0} partidos del horario tienen hoja en el masivo.</p>`;

  const warn = warnings.length
    ? `<ul>${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "";

  return shell({
    title: "Previsualización de planillas",
    body: `
      <div class="card">
        <p class="kicker">Previsualización</p>
        <h1>Listo para armar</h1>
        <p>Leí el PDF contra el horario. Revisá qué se tira y después descargá el documento nuevo.</p>
        <div class="stats">
          <div><span>Hojas originales</span><strong>${summary.pageCount}</strong></div>
          <div><span>Se conservan</span><strong>${summary.keptOriginalPages ?? summary.keptPages?.length ?? "—"}</strong></div>
          <div><span>Equipos a borrar</span><strong>${removed.length}</strong></div>
        </div>
        <h2>Equipos fuera de la jornada</h2>
        ${extras}
        ${dropped.length ? `<p>Se eliminan ${dropped.length} hoja${dropped.length === 1 ? "" : "s"} con esos equipos (y la hoja extra de firmas, si la tenían).</p>` : ""}
        <h2>Partidos</h2>
        ${pending}
        ${warn}
        <form action="/api/generate" method="post" enctype="multipart/form-data">
          <input type="hidden" name="schedule" value="${escapeAttribute(fields.schedule)}" />
          <input type="hidden" name="source" value="${escapeAttribute(fields.source)}" />
          <input type="hidden" name="sort" value="${escapeAttribute(fields.sort)}" />
          <input type="hidden" name="index" value="${escapeAttribute(fields.index)}" />
          <input type="hidden" name="blanks" value="${escapeAttribute(fields.blanks)}" />
          <input type="hidden" name="date" value="${escapeAttribute(fields.date)}" />
          <div class="actions">
            <button class="btn primary" type="submit">Armar planillas</button>
            <a class="btn" href="/">Volver a editar</a>
          </div>
        </form>
        <p class="hint">Si subiste un PDF propio y no el masivo precargado, volvé a la pantalla principal y tocá <strong>Armar planillas</strong> ahí para mandarlo de nuevo.</p>
      </div>
    `,
  });
}

function shell({ title, body }: { title: string; body: string }) {
  return `<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHtml(title)} — Planillero</title>
    <style>
      :root { color-scheme: light; }
      * { box-sizing: border-box; }
      body { margin: 0; font-family: Outfit, ui-sans-serif, system-ui, sans-serif; background: #f4efe2; color: #243328; }
      header { background: #2f4a38; color: #f7f3ea; padding: 1.5rem 1.25rem; }
      header p { margin: 0; letter-spacing: 0.28em; text-transform: uppercase; font-size: 0.7rem; opacity: 0.8; }
      header h1 { font-family: Fraunces, Georgia, serif; margin: 0.35rem 0 0; font-size: 2rem; }
      main { max-width: 44rem; margin: 0 auto; padding: 1.5rem 1.25rem 3rem; }
      .card { background: #fffcf6; border: 1px solid #e4dccb; border-radius: 1rem; padding: 1.25rem 1.35rem; }
      .kicker { text-transform: uppercase; letter-spacing: 0.16em; font-size: 0.7rem; color: #3d6a4c; margin: 0 0 0.4rem; }
      h1 { font-family: Fraunces, Georgia, serif; font-size: 2rem; margin: 0 0 0.5rem; }
      h2 { font-size: 1rem; margin: 1.25rem 0 0.4rem; }
      p { line-height: 1.5; }
      .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; margin: 1rem 0; }
      .stats div { background: #eef3e6; border-radius: 0.7rem; padding: 0.7rem 0.8rem; }
      .stats span { display: block; font-size: 0.75rem; color: #5c6b5f; }
      .stats strong { font-family: Fraunces, Georgia, serif; font-size: 1.4rem; }
      .chips { display: flex; flex-wrap: wrap; gap: 0.4rem; padding: 0; margin: 0.4rem 0 0; list-style: none; }
      .chips li { background: #f8e4e0; color: #7a2e24; border-radius: 999px; padding: 0.25rem 0.7rem; font-size: 0.85rem; }
      .actions { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 1.25rem; }
      .btn { display: inline-flex; align-items: center; justify-content: center; min-height: 2.6rem; padding: 0.45rem 0.95rem; border-radius: 0.7rem; border: 1px solid #d7d0c2; background: #fff; color: inherit; text-decoration: none; font: inherit; cursor: pointer; }
      .btn.primary { background: #2f4a38; color: #f7f3ea; border-color: transparent; }
      .hint { color: #5c6b5f; font-size: 0.85rem; }
      @media (max-width: 640px) { .stats { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <header>
      <p>La Chacra Fútbol</p>
      <h1>Generador de Planillas LCH</h1>
    </header>
    <main>${body}</main>
  </body>
</html>`;
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value: string) {
  return escapeHtml(value);
}
