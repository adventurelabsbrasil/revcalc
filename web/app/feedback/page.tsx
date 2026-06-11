"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchFeedbackConfig,
  fetchMe,
  fetchVersion,
  FeedbackTipo,
  loginUrl,
  Me,
  sendFeedback,
} from "@/lib/api";

const TIPOS: { value: FeedbackTipo; label: string; hint: string }[] = [
  { value: "feat", label: "💡 Melhoria — ideia ou pedido", hint: "Algo que você gostaria que o sistema fizesse." },
  { value: "bug", label: "🐞 Falha — algo errado", hint: "Algo calculou ou salvou errado, ou não funcionou como esperado." },
  { value: "erro_sistema", label: "⚠️ Log de erro — o sistema travou", hint: "O app deu erro / parou no meio." },
  { value: "duvida", label: "❓ Dúvida — não entendi algo", hint: "Uma pergunta sobre como usar." },
];

export default function FeedbackPage() {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [ver, setVer] = useState<string | null>(null);
  const [enabled, setEnabled] = useState<boolean | null>(null);

  const [tipo, setTipo] = useState<FeedbackTipo>("feat");
  const [mensagem, setMensagem] = useState("");
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe().then(setMe);
    fetchVersion().then(setVer);
    fetchFeedbackConfig().then((c) => setEnabled(c.enabled));
  }, []);

  async function enviar() {
    if (!mensagem.trim()) {
      setError("Escreva uma mensagem antes de enviar.");
      return;
    }
    setError(null);
    setSending(true);
    const res = await sendFeedback({ tipo, mensagem: mensagem.trim(), origem: "manual" });
    setSending(false);
    switch (res.kind) {
      case "ok":
        setDone(true);
        setMensagem("");
        break;
      case "not_authenticated":
        setMe(null);
        setError("Sua sessão expirou. Entre novamente com o Google.");
        break;
      case "disabled":
        setError("A caixa de feedback está temporariamente indisponível.");
        break;
      case "error":
        setError(res.message);
        break;
    }
  }

  const tipoAtual = TIPOS.find((t) => t.value === tipo);

  return (
    <main>
      <div className="topbar">
        <span>
          Rose Portal Advocacia
          {ver && <small style={{ opacity: 0.6, marginLeft: 8 }}>v{ver}</small>}
        </span>
        <Link className="link" href="/">
          ← Voltar à calculadora
        </Link>
      </div>

      <h1>Enviar feedback</h1>
      <p className="sub">
        Conte pra gente o que melhorar, o que falhou ou tire uma dúvida. Vai direto pra equipe da
        Adventure Labs.
      </p>

      {me === null ? (
        <div className="card">
          <p>Entre com sua conta Google autorizada para enviar feedback.</p>
          <a href={loginUrl()}>
            <button>Entrar com Google</button>
          </a>
        </div>
      ) : enabled === false ? (
        <div className="banner erro">A caixa de feedback está indisponível no momento.</div>
      ) : done ? (
        <div className="banner ok">
          ✓ Recebemos seu feedback. Obrigado!{" "}
          <button
            className="secondary"
            style={{ marginLeft: 8, padding: "4px 10px" }}
            onClick={() => setDone(false)}
          >
            Enviar outro
          </button>
        </div>
      ) : (
        <div className="card">
          <label htmlFor="tipo">Tipo</label>
          <select
            id="tipo"
            value={tipo}
            disabled={sending}
            onChange={(e) => setTipo(e.target.value as FeedbackTipo)}
          >
            {TIPOS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          {tipoAtual && <p className="sub" style={{ margin: "6px 0 16px" }}>{tipoAtual.hint}</p>}

          <label htmlFor="msg">Mensagem</label>
          <textarea
            id="msg"
            value={mensagem}
            disabled={sending}
            placeholder="Descreva com o máximo de detalhes que puder…"
            rows={6}
            onChange={(e) => setMensagem(e.target.value)}
          />

          {error && <div className="banner erro" style={{ marginTop: 14 }}>{error}</div>}

          <div className="row" style={{ marginTop: 14 }}>
            <button onClick={enviar} disabled={sending}>
              {sending ? "Enviando…" : "Enviar feedback"}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
