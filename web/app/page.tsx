"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Novidades from "@/components/Novidades";
import ProgressLog, { LogLine } from "@/components/ProgressLog";
import {
  fetchMe,
  fetchVersion,
  fullEventsUrl,
  LoteResult,
  loginUrl,
  logout,
  Me,
  sendFeedback,
  startRun,
} from "@/lib/api";

const ERROS_QUERY: Record<string, string> = {
  dominio_nao_autorizado:
    "Esse e-mail não tem permissão. Use uma conta @roseportaladvocacia.com.br.",
  consent_negado: "Login cancelado.",
  state_invalido: "Sessão de login expirou. Tente entrar de novo.",
  falha_oauth: "Falha ao autenticar com o Google. Tente novamente.",
};

// Rótulo/emoji por status de cliente no relatório do lote (v0.9.8).
const STATUS_INFO: Record<string, { emoji: string; label: string }> = {
  ok: { emoji: "✅", label: "calculado" },
  nada_novo: { emoji: "⏭️", label: "já tinha cálculo (pulado)" },
  nao_encontrado: { emoji: "🔎", label: "cliente não encontrado" },
  ambiguo: { emoji: "🔎", label: "nome ambíguo (vários locais)" },
  erro: { emoji: "⚠️", label: "erro" },
};

export default function Home() {
  const [me, setMe] = useState<Me | null | undefined>(undefined); // undefined = carregando
  const [nomeInput, setNomeInput] = useState(""); // campo de digitação
  const [nomes, setNomes] = useState<string[]>([]); // fila de clientes do lote
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [result, setResult] = useState<LoteResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [ver, setVer] = useState<string | null>(null);
  // Auto-reporte de erro do sistema: 'idle' | 'sending' | 'sent' | 'failed'
  const [report, setReport] = useState<"idle" | "sending" | "sent" | "failed">("idle");

  const esRef = useRef<EventSource | null>(null);
  const finishedRef = useRef(false);
  const linesRef = useRef<LogLine[]>([]);

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
    setLines((prev) => {
      const next = [...prev, line];
      linesRef.current = next;
      return next;
    });
  }

  async function reportarErro(mensagemErro: string) {
    setReport("sending");
    const logTxt = linesRef.current
      .map((l) => `[${l.level}] ${l.message}`)
      .join("\n")
      .slice(-4000);
    const res = await sendFeedback({
      tipo: "erro_sistema",
      origem: "auto",
      mensagem: `Erro detectado pelo sistema: ${mensagemErro}`,
      contexto: { erro: mensagemErro, log: logTxt },
    });
    setReport(res.kind === "ok" ? "sent" : "failed");
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
        setResult(ev.result as LoteResult);
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

  // Adiciona um nome à fila do lote (valida ≥2 palavras, sem duplicar).
  function adicionarNome(): boolean {
    const n = nomeInput.trim().replace(/\s+/g, " ");
    if (n.split(" ").length < 2) {
      setError("Digite o nome completo da cliente (mínimo 2 palavras).");
      return false;
    }
    setError(null);
    if (!nomes.some((x) => x.toLowerCase() === n.toLowerCase())) {
      setNomes((prev) => [...prev, n]);
    }
    setNomeInput("");
    return true;
  }

  function removerNome(i: number) {
    setNomes((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function calcular() {
    // Inclui o que estiver digitado no campo (mesmo sem ter clicado "Adicionar").
    const digitado = nomeInput.trim().replace(/\s+/g, " ");
    const fila = [...nomes];
    if (digitado && digitado.split(" ").length >= 2 &&
        !fila.some((x) => x.toLowerCase() === digitado.toLowerCase())) {
      fila.push(digitado);
    }
    if (fila.length === 0) {
      setError("Adicione ao menos um nome completo de cliente (mínimo 2 palavras).");
      return;
    }
    setNomes(fila);
    setNomeInput("");
    setError(null);
    setResult(null);
    setLines([]);
    linesRef.current = [];
    setReport("idle");
    setRunning(true);

    const res = await startRun(fila);
    switch (res.kind) {
      case "started":
        abrirStream(res.data.events_url);
        break;
      case "not_authenticated":
        setRunning(false);
        setMe(null);
        setError("Sua sessão expirou. Entre novamente com o Google.");
        break;
      case "error":
        setRunning(false);
        setError(res.message);
        break;
    }
  }

  async function sair() {
    await logout();
    setMe(null);
    setLines([]);
    setResult(null);
    setNomes([]);
    setNomeInput("");
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
        <span style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Novidades />
          <Link className="link" href="/feedback">
            Feedback
          </Link>
          {me && (
            <>
              {me.email}{" "}
              <button className="secondary" onClick={sair} style={{ padding: "4px 10px" }}>
                Sair
              </button>
            </>
          )}
        </span>
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
                value={nomeInput}
                placeholder="Ex.: Maria das Dores Silva"
                disabled={running}
                onChange={(e) => setNomeInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !running) adicionarNome();
                }}
              />
              <button
                className="secondary"
                onClick={adicionarNome}
                disabled={running}
              >
                Adicionar
              </button>
            </div>

            {nomes.length > 0 && (
              <div className="chips" style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                {nomes.map((n, i) => (
                  <span
                    key={i}
                    className="chip"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "4px 10px",
                      borderRadius: 999,
                      background: "rgba(127,127,127,0.15)",
                      fontSize: "0.9rem",
                    }}
                  >
                    {n}
                    {!running && (
                      <button
                        aria-label={`Remover ${n}`}
                        onClick={() => removerNome(i)}
                        style={{
                          border: "none",
                          background: "transparent",
                          cursor: "pointer",
                          padding: 0,
                          fontSize: "1rem",
                          lineHeight: 1,
                        }}
                      >
                        ×
                      </button>
                    )}
                  </span>
                ))}
              </div>
            )}

            <div className="row" style={{ marginTop: 12 }}>
              <button onClick={calcular} disabled={running}>
                {running
                  ? "Calculando…"
                  : nomes.length > 1
                    ? `Calcular ${nomes.length} clientes`
                    : "Calcular"}
              </button>
            </div>

            <p className="sub" style={{ marginTop: 10, fontSize: "0.82rem" }}>
              Adicione um ou vários nomes (um a um) e processe em lote. Cálculos já
              feitos são <strong>pulados automaticamente</strong> — para refazer um
              contrato, apague o arquivo <code>Calculo.xlsx</code> (ou{" "}
              <code>Calculo quitado.xlsx</code>) da pasta dele no Drive e rode de novo.
            </p>
          </div>

          {error && (
            <div className="banner erro">
              <div>{error}</div>
              <div className="row" style={{ marginTop: 10, alignItems: "center" }}>
                {report === "sent" ? (
                  <span style={{ fontSize: "0.85rem" }}>
                    ✓ Erro reportado pra equipe. Obrigado!
                  </span>
                ) : (
                  <>
                    <button
                      className="secondary"
                      style={{ padding: "6px 12px" }}
                      disabled={report === "sending"}
                      onClick={() => reportarErro(error)}
                    >
                      {report === "sending" ? "Enviando…" : "📨 Reportar este erro pra equipe"}
                    </button>
                    {report === "failed" && (
                      <span style={{ fontSize: "0.8rem", opacity: 0.8 }}>
                        Não consegui enviar agora — você pode usar a página de{" "}
                        <Link className="link" href="/feedback">
                          Feedback
                        </Link>
                        .
                      </span>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          <ProgressLog lines={lines} />

          {result && (
            <div className="banner ok" style={{ marginTop: 18 }}>
              <div style={{ marginBottom: 8 }}>
                <strong>Lote concluído.</strong> {result.resumo.ok} calculado(s) ·{" "}
                {result.resumo.nada_novo} já feito(s) ·{" "}
                {result.resumo.pulados_total} contrato(s) pulado(s) ·{" "}
                {result.resumo.nao_encontrados} não encontrado(s) ·{" "}
                {result.resumo.erros} erro(s).
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {result.clientes.map((c, i) => (
                  <li
                    key={i}
                    style={{
                      padding: "10px 0",
                      borderTop: i ? "1px solid rgba(127,127,127,0.2)" : "none",
                    }}
                  >
                    <div>
                      {STATUS_INFO[c.status]?.emoji ?? "•"} <strong>{c.nome}</strong>{" "}
                      <em style={{ opacity: 0.8 }}>
                        — {STATUS_INFO[c.status]?.label ?? c.status}
                      </em>
                    </div>
                    {c.resultado?.pasta_drive_url && (
                      <a
                        className="link"
                        href={c.resultado.pasta_drive_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Abrir pasta no Drive →
                      </a>
                    )}
                    {c.resultado && c.resultado.arquivos_gerados.length > 0 && (
                      <ul className="arquivos">
                        {c.resultado.arquivos_gerados.map((a, j) => (
                          <li key={j}>
                            {a.nome} <em>({a.status})</em>
                          </li>
                        ))}
                      </ul>
                    )}
                    {c.resultado && c.resultado.pulados.length > 0 && (
                      <div style={{ fontSize: "0.85rem", opacity: 0.85 }}>
                        Pulados (já tinham cálculo):{" "}
                        {c.resultado.pulados.map((p) => p.pasta).join(", ")}
                      </div>
                    )}
                    {c.status === "nao_encontrado" && c.sugestoes && c.sugestoes.length > 0 && (
                      <div style={{ fontSize: "0.85rem" }}>
                        Você quis dizer: {c.sugestoes.join(", ")}?
                      </div>
                    )}
                    {c.status === "ambiguo" && c.paths && c.paths.length > 0 && (
                      <div style={{ fontSize: "0.85rem" }}>
                        Vários locais: {c.paths.join(" | ")}
                      </div>
                    )}
                    {c.status === "erro" && c.erro && (
                      <div style={{ fontSize: "0.85rem" }}>{c.erro}</div>
                    )}
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
