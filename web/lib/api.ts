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

export interface RunResult {
  pasta_drive_path: string;
  pasta_drive_url: string;
  xlsx_file_id: string;
  arquivos_gerados: ArquivoGerado[];
}

export type StartResponse =
  | { kind: "started"; data: RunStart }
  | { kind: "needs_confirmation"; nome_arquivo: string; modified_time: string }
  | { kind: "not_authenticated" }
  | { kind: "error"; message: string; sugestoes?: string[]; paths?: string[] };

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

export async function startRun(nome: string, forcar: boolean): Promise<StartResponse> {
  const r = await fetch(`${API_BASE}/api/run`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, forcar }),
  });
  const body = await r.json().catch(() => ({}));

  if (r.ok) return { kind: "started", data: body as RunStart };
  if (r.status === 401) return { kind: "not_authenticated" };
  if (r.status === 409 && body?.needs_confirmation) {
    return {
      kind: "needs_confirmation",
      nome_arquivo: body.nome_arquivo,
      modified_time: body.modified_time,
    };
  }
  return {
    kind: "error",
    message: body?.error ?? `Erro ${r.status}.`,
    sugestoes: body?.sugestoes,
    paths: body?.paths,
  };
}

export function fullEventsUrl(eventsPath: string): string {
  return `${API_BASE}${eventsPath}`;
}
