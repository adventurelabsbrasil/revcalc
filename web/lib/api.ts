// Cliente da API do backend (xeon). Todas as chamadas com credentials:include
// para mandar o cookie de sessão (first-party quando front+api compartilham domínio).

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export interface Me {
  email: string;
}

export interface RunStart {
  run_id: string;
  events_url: string;
}

export interface ArquivoGerado {
  nome: string;
  status: string;
}

export interface Pulado {
  pasta: string;
  arquivo: string;
}

export interface RunResult {
  pasta_drive_path: string;
  pasta_drive_url: string;
  xlsx_file_id: string;
  arquivos_gerados: ArquivoGerado[];
  pulados: Pulado[];
}

// Status por cliente no lote (v0.9.8).
export type ClienteStatus = "ok" | "nada_novo" | "nao_encontrado" | "ambiguo" | "erro";

export interface ClienteResultado {
  nome: string;
  status: ClienteStatus;
  resultado?: RunResult;
  erro?: string;
  sugestoes?: string[];
  paths?: string[];
}

export interface ResumoLote {
  total: number;
  ok: number;
  nada_novo: number;
  nao_encontrados: number;
  erros: number;
  pulados_total: number;
}

export interface LoteResult {
  clientes: ClienteResultado[];
  resumo: ResumoLote;
}

export type StartResponse =
  | { kind: "started"; data: RunStart }
  | { kind: "not_authenticated" }
  | { kind: "error"; message: string };

export async function fetchVersion(): Promise<string | null> {
  try {
    const r = await fetch(`${API_BASE}/healthz`);
    if (!r.ok) return null;
    const d = await r.json();
    return (d?.version as string) ?? null;
  } catch {
    return null;
  }
}

export async function fetchMe(): Promise<Me | null> {
  try {
    const r = await fetch(`${API_BASE}/api/me`, { credentials: "include" });
    if (r.status === 200) return (await r.json()) as Me;
    return null;
  } catch {
    return null;
  }
}

export function loginUrl(): string {
  return `${API_BASE}/api/auth/login`;
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    /* ignore */
  }
}

// v0.9.8: processa uma FILA de clientes em lote. Já-calculados são pulados e
// nomes não encontrados viram status no relatório por-cliente (evento `done`).
export async function startRun(nomes: string[]): Promise<StartResponse> {
  const r = await fetch(`${API_BASE}/api/run`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nomes }),
  });
  const body = await r.json().catch(() => ({}));

  if (r.ok) return { kind: "started", data: body as RunStart };
  if (r.status === 401) return { kind: "not_authenticated" };
  return { kind: "error", message: body?.error ?? `Erro ${r.status}.` };
}

export function fullEventsUrl(eventsPath: string): string {
  return `${API_BASE}${eventsPath}`;
}

// ─── Feedback ──────────────────────────────────────────────────────────────

export type FeedbackTipo = "feat" | "bug" | "erro_sistema" | "duvida";

export interface FeedbackPayload {
  tipo: FeedbackTipo;
  mensagem?: string;
  origem?: "manual" | "auto";
  contexto?: Record<string, unknown>;
}

export type FeedbackResult =
  | { kind: "ok"; id?: string }
  | { kind: "not_authenticated" }
  | { kind: "disabled" }
  | { kind: "error"; message: string };

export async function fetchFeedbackConfig(): Promise<{ enabled: boolean }> {
  try {
    const r = await fetch(`${API_BASE}/api/feedback/config`, { credentials: "include" });
    if (!r.ok) return { enabled: false };
    return (await r.json()) as { enabled: boolean };
  } catch {
    return { enabled: false };
  }
}

export async function sendFeedback(payload: FeedbackPayload): Promise<FeedbackResult> {
  // Contexto técnico básico, sempre anexado (não-PII).
  const contexto = {
    url: typeof window !== "undefined" ? window.location.href : "",
    user_agent: typeof navigator !== "undefined" ? navigator.userAgent : "",
    ...(payload.contexto ?? {}),
  };
  try {
    const r = await fetch(`${API_BASE}/api/feedback`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, contexto }),
    });
    const body = await r.json().catch(() => ({}));
    if (r.status === 201 || (r.ok && body?.ok)) return { kind: "ok", id: body?.id };
    if (r.status === 401) return { kind: "not_authenticated" };
    if (r.status === 503) return { kind: "disabled" };
    return { kind: "error", message: body?.error ?? `Erro ${r.status}.` };
  } catch {
    return { kind: "error", message: "Falha de conexão ao enviar o feedback." };
  }
}
