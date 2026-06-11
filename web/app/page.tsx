"use client";

import { useEffect, useRef, useState } from "react";
import ProgressLog, { LogLine } from "@/components/ProgressLog";
import {
  fetchMe,
  fetchVersion,
  fullEventsUrl,
  loginUrl,
  logout,
  Me,
  RunResult,
  startRun,
} from "@/lib/api";

const ERROS_QUERY: Record<string, string> = {
  dominio_nao_autorizado:
    "Esse e-mail não tem permissão. Use uma conta @roseportaladvocacia.com.br.",
  consent_negado: "Login cancelado.",
  state_invalido: "Sessão de login expirou. Tente entrar de novo.",
  falha_oauth: "Falha ao autenticar com o Google. Tente novamente.",
};

export default function Home() {
  const [me, setMe] = useState<Me | null | undefined>(undefined); // undefined = carregando
  const [nome, setNome] = useState("");
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [result, setResult] = useState<RunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dedup, setDedup] = useState<{ nome_arquivo: string; modified_time: string } | null>(
    null
  );
  const [banner, setBanner] = useState<string | null>(null);
  const [ver, setVer] = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const finishedRef = useRef(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const err = params.get("error");
    if (err) setBanner(ERROS_QUERY[err] ?? "Não foi possível entrar.");
    window.history.replaceState({}, "", window.location.pathname);
    fetchMe().then(setMe);
    fetchVersion().then(setVer);
    return () => esRef.current?.close();
  }, []);

  function addLine(line: LogLine) {
    setLines((prev) => [...prev, line]);
  }

  function abrirStream(eventsPath: string) {
    finishedRef.current = false;
    const es = new EventSource(fullEventsUrl(eventsPath), { withCredentials: true });
    esRef.current = es;

    es.onmessage = (e) => {
      let ev: any;
      try {
        ev = JSON.parse(e.data);
      } catch {
        return;
      }
      if (ev.type === "status") {
        addLine({ level: ev.level === "aviso" ? "aviso" : "info", message: ev.message });
      } else if (ev.type === "done") {
        finishedRef.current = true;
        addLine({ level: "ok", message: "Pronto." });
        setResult(ev.result as RunResult);
        setRunning(false);
        es.close();
      } else if (ev.type === "error") {
        finishedRef.current = true;
        addLine({ level: "erro", message: ev.error });
        setError(ev.error);
        setRunning(false);
        es.close();
      }
    };

    es.onerror = () => {
      if (finishedRef.current) return;
      finishedRef.current = true;
      addLine({ level: "erro", message: "Conexão com o servidor interrompida." });
      setError("Conexão com o servidor interrompida. Tente de novo.");
      setRunning(false);
      es.close();
    };
  }

  async function calcular(forcar: boolean) {
    if (nome.trim().split(/\s+/).length < 2) {
      setError("Digite o nome completo da cliente (mínimo 2 palavras).");
      return;
    }
    setError(null);
    setResult(null);
    setDedup(null);
    setLines([]);
    setRunning(true);

    const res = await startRun(nome.trim(), forcar);
    switch (res.kind) {
      case "started":
        abrirStream(res.data.events_url);
        break;
      case "needs_confirmation":
        setRunning(false);
        setDedup({ nome_arquivo: res.nome_arquivo, modified_time: res.modified_time });
        break;
      case "not_authenticated":
        setRunning(false);
        setMe(null);
        setError("Sua sessão expirou. Entre novamente com o Google.");
        break;
      case "error": {
        setRunning(false);
        let msg = res.message;
        if (res.sugestoes?.length) msg += ` Você quis dizer: ${res.sugestoes.join(", ")}?`;
        if (res.paths?.length) msg += ` (${res.paths.join(" | ")})`;
        setError(msg);
        break;
      }
    }
  }

  async function sair() {
    await logout();
    setMe(null);
    setLines([]);
    setResult(null);
    setNome("");
  }

  // ── Render ──
  if (me === undefined) {
    return (
      <main>
        <p className="sub">Carregando…</p>
      </main>
    );
  }

  return (
    <main>
      <div className="topbar">
        <span>
          Rose Portal Advocacia
          {ver && <small style={{ opacity: 0.6, marginLeft: 8 }}>v{ver}</small>}
        </span>
        {me && (
          <span>
            {me.email}{" "}
            <button className="secondary" onClick={sair} style={{ padding: "4px 10px" }}>
              Sair
            </button>
          </span>
        )}
      </div>

      <h1>Calculadora Crefaz</h1>
      <p className="sub">
        Gera o cálculo revisional e salva tudo na pasta da cliente no Drive.
      </p>

      {banner && <div className="banner erro">{banner}</div>}

      {!me ? (
        <div className="card">
          <p>Entre com sua conta Google autorizada para começar.</p>
          <a href={loginUrl()}>
            <button>Entrar com Google</button>
          </a>
        </div>
      ) : (
        <>
          <div className="card">
            <label htmlFor="nome">Nome completo da cliente</label>
            <div className="row">
              <input
                id="nome"
                type="text"
                value={nome}
                placeholder="Ex.: Maria das Dores Silva"
                disabled={running}
                onChange={(e) => setNome(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !running) calcular(false);
                }}
              />
              <button onClick={() => calcular(false)} disabled={running}>
                {running ? "Calculando…" : "Calcular"}
              </button>
            </div>
          </div>

          {dedup && (
            <div className="banner erro">
              Já existe um cálculo nessa pasta: <strong>{dedup.nome_arquivo}</strong>{" "}
              (modificado em {dedup.modified_time}). Sobrescrever?
              <div className="row" style={{ marginTop: 10 }}>
                <button onClick={() => calcular(true)}>Sobrescrever</button>
                <button className="secondary" onClick={() => setDedup(null)}>
                  Cancelar
                </button>
              </div>
            </div>
          )}

          {error && !dedup && <div className="banner erro">{error}</div>}

          <ProgressLog lines={lines} />

          {result && (
            <div className="banner ok" style={{ marginTop: 18 }}>
              <div>
                ✓ Cálculo gerado em <strong>{result.pasta_drive_path}</strong>.
              </div>
              <a className="link" href={result.pasta_drive_url} target="_blank" rel="noreferrer">
                Abrir pasta no Drive →
              </a>
              <ul className="arquivos">
                {result.arquivos_gerados.map((a, i) => (
                  <li key={i}>
                    {a.nome} <em>({a.status})</em>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </main>
  );
}
