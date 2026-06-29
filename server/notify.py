"""Notifica o Founder via WhatsApp (Evolution API) sobre eventos do RevCalc.

Best-effort, fire-and-forget: nunca lança nem bloqueia o fluxo chamador. Reusa o
padrão canônico Adventure (`founder-notify`): POST {EVOLUTION_API_URL}/message/
sendText/{instance} com header `apikey`, body {number, text}. O destino aceita
número individual OU JID de grupo (`...@g.us`) — então o mesmo código serve pro
grupo "Comando Estelar". No-op gracioso se as env vars não estiverem configuradas.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

NOTIFY_TIMEOUT = 8.0
MAX_RESUMO = 300

_EMOJI_TIPO = {"feat": "💡", "bug": "🐛", "erro_sistema": "🚨", "duvida": "❓"}
_LABEL_TIPO = {
    "feat": "Melhoria",
    "bug": "Falha",
    "erro_sistema": "Erro de sistema",
    "duvida": "Dúvida",
}


def _normalizar_destino(d: str) -> str:
    """JID (grupo/contato) passa intacto; número solto vira só dígitos (DDI+DDD+nº)."""
    d = (d or "").strip()
    if "@" in d:
        return d
    return "".join(ch for ch in d if ch.isdigit())


def montar_texto_feedback(
    *,
    projeto: str,
    cliente: str,
    tipo: str,
    origem: str,
    email: str | None,
    mensagem: str | None,
    app_version: str,
) -> str:
    """Mensagem curta pro Founder: projeto/cliente + tipo + quem + problema resumido."""
    emoji = _EMOJI_TIPO.get(tipo, "🔔")
    label = _LABEL_TIPO.get(tipo, tipo)
    resumo = (mensagem or "").replace("\r", "").strip()
    if len(resumo) > MAX_RESUMO:
        resumo = resumo[:MAX_RESUMO].rstrip() + "…"
    if not resumo:
        resumo = "(sem mensagem)"
    auto = " (auto)" if origem == "auto" else ""
    de = (email or "").strip() or "anônimo"
    return (
        f"🔔 *Feedback · {projeto} — {cliente}*\n"
        f"{emoji} {label}{auto} · v{app_version}\n"
        f"De: {de}\n\n"
        f"{resumo}"
    )


async def enviar_whatsapp(
    *,
    api_url: str | None,
    api_key: str | None,
    instance: str,
    destinos,
    text: str,
) -> int:
    """Envia `text` via Evolution pra cada destino. Retorna nº de envios OK. Nunca lança."""
    destinos = tuple(destinos or ())
    if not (api_url and api_key and destinos):
        return 0
    text = f"[Comando Estelar]\n{text}"  # assinatura prévia em toda notificação do sistema
    endpoint = f"{api_url}/message/sendText/{instance}"
    headers = {"Content-Type": "application/json", "apikey": api_key}
    enviados = 0
    try:
        async with httpx.AsyncClient(timeout=NOTIFY_TIMEOUT) as client:
            for destino in destinos:
                number = _normalizar_destino(destino)
                if not number:
                    continue
                try:
                    r = await client.post(
                        endpoint, headers=headers, json={"number": number, "text": text}
                    )
                    if r.status_code in (200, 201):
                        enviados += 1
                    else:
                        logger.warning(
                            "Evolution sendText %s: HTTP %s %s",
                            number, r.status_code, r.text[:200],
                        )
                except Exception as e:  # noqa: BLE001 — best-effort por destino
                    logger.warning("Evolution sendText %s falhou: %s", number, e)
    except Exception as e:  # noqa: BLE001 — nunca derruba o fluxo do feedback
        logger.warning("Notify WhatsApp falhou: %s", e)
    return enviados
