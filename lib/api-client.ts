export const LOCAL_API = "http://127.0.0.1:43147";

export function describeNetworkError(caught: unknown): string {
  if (typeof DOMException !== "undefined" && caught instanceof DOMException && caught.name === "AbortError") {
    return "Tardó demasiado. Dejá la ventana abierta y volvé a tocar Armar planillas.";
  }
  const message = caught instanceof Error ? caught.message : String(caught ?? "");
  if (isNetworkFailure(caught)) {
    return (
      "No pude hablar con el generador. Dejá abierta la ventana negra del programa y recargá esta página. " +
      `Si estás en una vista previa, abrí ${LOCAL_API} en el navegador.`
    );
  }
  return message || "Algo salió mal.";
}

export function isNetworkFailure(caught: unknown): boolean {
  const message = caught instanceof Error ? caught.message : String(caught ?? "");
  if (caught instanceof TypeError) return true;
  return /failed to fetch|networkerror|load failed/i.test(message);
}

export async function postProcess(
  path: "/api/analyze" | "/api/generate",
  payload: Record<string, string>,
  file: File | null,
): Promise<Record<string, unknown>> {
  const bases = apiBases();
  let last: unknown = null;
  for (const base of bases) {
    try {
      return await postOnce(`${base}${path}`, payload, file);
    } catch (error) {
      last = error;
      if (!isNetworkFailure(error)) throw error;
    }
  }
  throw new Error(describeNetworkError(last));
}

function apiBases(): string[] {
  const bases = [""];
  if (typeof window === "undefined") return bases;
  const origin = window.location.origin.replace(/\/$/, "");
  if (origin !== LOCAL_API) bases.push(LOCAL_API);
  return bases;
}

async function postOnce(
  url: string,
  payload: Record<string, string>,
  file: File | null,
): Promise<Record<string, unknown>> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 180_000);
  try {
    const headers: Record<string, string> = { Accept: "application/json" };
    let body: BodyInit;
    if (file) {
      const form = new FormData();
      for (const [key, value] of Object.entries(payload)) form.set(key, value);
      form.set("pdf", file);
      body = form;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(payload);
    }
    const response = await fetch(url, {
      method: "POST",
      body,
      headers,
      signal: controller.signal,
      cache: "no-store",
    });
    const data = (await response.json().catch(() => null)) as { error?: string } | null;
    if (!data) throw new TypeError("Failed to fetch");
    if (!response.ok) throw new Error(data.error || "No pude completar el pedido.");
    return data;
  } finally {
    window.clearTimeout(timer);
  }
}
