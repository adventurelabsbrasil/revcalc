"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  fetchAssistenteConfig,
  fetchMe,
  fetchVersion,
  loginUrl,
  Me,
  perguntarAssistente,
} from "@/lib/api";

interface Mensagem {
  autor: "usuario" | "agente";
  texto: string;
}

const EXEMPLOS = [
  "Onde está a pasta da cliente Maria Silva?",
  "Quais documentos tem no caso revisional de veículo do João?",
];

// O agente responde em markdown simples; aqui só o **negrito** vira <strong>
// (quebras de linha e listas já saem legíveis com white-space: pre-wrap).
function Texto({ texto }: { texto: string }) {
  return (
    <>
      {texto.split(/\*\*(.+?)\*\*/g).map((parte, i) =>
        i % 2 ? <strong key={i}>{parte}</strong> : <Fragment key={i}>{parte}</Fragment>,
      )}
    </>
  );
}

export default function AssistentePage() {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [ver, setVer] = useState<string | null>(null);
  const [enabled, setEnabled] = useState<boolean | null>(null);

  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [respondendo, setRespondendo] = useState(false);
  // Última mensagem do agente no turno em curso: notas de progresso até o "fim",
  // quando a mais recente vira a resposta.
  const [rascunho, setRascunho] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const conversaRef = useRef<string | null>(null);
  const fimRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchMe().then(setMe);
    fetchVersion().then(setVer);
    fetchAssistenteConfig().then((c) => setEnabled(c.enabled));
  }, []);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ block: "end" });
  }, [mensagens]);

  async function enviar(texto: string) {
    texto = texto.trim();
    if (!texto || respondendo) return;
    setError(null);
    setPergunta("");
    setMensagens((prev) => [...prev, { autor: "usuario", texto }]);
    setRespondendo(true);

    let ultima: string | null = null;
    const res = await perguntarAssistente(texto, conversaRef.current, (ev) => {
      switch (ev.tipo) {
        case "conversa":
          conversaRef.current = ev.token;
          break;
        case "texto":
          ultima = ev.texto;
          setRascunho(ev.texto);
          break;
        case "fim": {
          // Copia antes: o updater do setState roda depois, quando `ultima` já foi zerada.
          const resposta = ultima;
          if (resposta) setMensagens((prev) => [...prev, { autor: "agente", texto: resposta }]);
          ultima = null;
          break;
        }
        case "erro":
          setError(ev.mensagem);
          if (ev.reiniciar) conversaRef.current = null;
          ultima = null;
          break;
      }
    });
    setRascunho(null);
    setRespondendo(false);

    if (res.kind === "not_authenticated") {
      setMe(null);
      setError("Sua sessão expirou. Entre novamente com o Google.");
    } else if (res.kind === "error") {
      setError(res.message);
    }
  }

  function novaConversa() {
    conversaRef.current = null;
    setMensagens([]);
    setError(null);
  }

  return (
    <main>
      <div className="topbar">
        <span>
          Operação de Revisão de Contratos
          {ver && <small style={{ opacity: 0.6, marginLeft: 8 }}>v{ver}</small>}
        </span>
        <Link className="link" href="/">
          ← Voltar à calculadora
        </Link>
      </div>

      <h1>Assistente</h1>
      <p className="sub">
        Pergunte sobre as pastas e documentos de clientes no Drive. O assistente só consulta — não
        altera nada.
      </p>

      {me === null ? (
        <div className="card">
          <p>Entre com sua conta Google autorizada para usar o assistente.</p>
          <a href={loginUrl()}>
            <button>Entrar com Google</button>
          </a>
        </div>
      ) : enabled === false ? (
        <div className="banner erro">O assistente está indisponível no momento.</div>
      ) : (
        <>
          {mensagens.length > 0 && (
            <div className="chat">
              {mensagens.map((m, i) => (
                <div key={i} className={`msg ${m.autor}`}>
                  <Texto texto={m.texto} />
                </div>
              ))}
              {respondendo && (
                <div className="msg agente pensando">
                  Procurando no Drive…
                  {rascunho && <><br /><Texto texto={rascunho} /></>}
                </div>
              )}
              <div ref={fimRef} />
            </div>
          )}

          {error && <div className="banner erro">{error}</div>}

          <div className="card">
            <label htmlFor="pergunta">Sua pergunta</label>
            <textarea
              id="pergunta"
              value={pergunta}
              disabled={respondendo}
              placeholder={EXEMPLOS[0]}
              rows={3}
              onChange={(e) => setPergunta(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  enviar(pergunta);
                }
              }}
            />
            <div className="row" style={{ marginTop: 14 }}>
              <button onClick={() => enviar(pergunta)} disabled={respondendo || !pergunta.trim()}>
                {respondendo ? "Respondendo…" : "Perguntar"}
              </button>
              {mensagens.length > 0 && (
                <button className="secondary" onClick={novaConversa} disabled={respondendo}>
                  Nova conversa
                </button>
              )}
            </div>
            {mensagens.length === 0 && (
              <p className="sub" style={{ margin: "14px 0 0" }}>
                Exemplos:{" "}
                {EXEMPLOS.map((ex, i) => (
                  <Fragment key={ex}>
                    {i > 0 && " · "}
                    <a className="link" href="#" onClick={(e) => { e.preventDefault(); enviar(ex); }}>
                      {ex}
                    </a>
                  </Fragment>
                ))}
              </p>
            )}
          </div>
        </>
      )}
    </main>
  );
}
