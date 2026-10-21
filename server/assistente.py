"""Assistente administrativo (Claude Managed Agent) — spike do chat.

Fala com um agente hospedado na Anthropic (que consulta pastas do Drive) via
Managed Agents: cria a sessão, abre o stream SSE, envia a mensagem do usuário e
devolve o texto do agente conforme chega.

`conversar()` é o núcleo reaproveitável (a futura aba de chat embrulha esse
gerador numa rota SSE do FastAPI). O `__main__` é um CLI pra testar na mão:

    python -m server.assistente "quais pastas de clientes existem no Drive?"
    python -m server.assistente            # modo interativo (várias perguntas, mesma sessão)

Ambiente: ANTHROPIC_API_KEY (Infisical, nunca no código) + ASSISTENTE_AGENT_ID,
ASSISTENTE_ENVIRONMENT_ID e ASSISTENTE_VAULT_ID.
"""

from __future__ import annotations

import os
import sys
from typing import Callable, Iterator, Optional

import anthropic

# IDs do agente/ambiente/vault (org do cliente) vêm só do ambiente: o repo é público.
# O vault guarda a credencial OAuth do MCP do Drive — sem ele a sessão sobe sem Drive.
CONFIG = ("ASSISTENTE_AGENT_ID", "ASSISTENTE_ENVIRONMENT_ID", "ASSISTENTE_VAULT_ID")


def habilitado() -> bool:
    tem_chave = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    return tem_chave and all(os.environ.get(n) for n in CONFIG)


class AssistenteErro(RuntimeError):
    """Falha do lado do agente (session.error não-recuperável, sessão encerrada)."""


def criar_cliente() -> anthropic.Anthropic:
    # Só p/ chave de org sem workspace fixo; chave escopada a um workspace dispensa.
    workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    headers = {"anthropic-workspace-id": workspace} if workspace else None
    return anthropic.Anthropic(default_headers=headers)


def criar_sessao(client: anthropic.Anthropic, titulo: str = "RevCalc — assistente") -> str:
    session = client.beta.sessions.create(
        agent=os.environ["ASSISTENTE_AGENT_ID"],
        environment_id=os.environ["ASSISTENTE_ENVIRONMENT_ID"],
        vault_ids=[os.environ["ASSISTENTE_VAULT_ID"]],
        title=titulo,
    )
    return session.id


def _negar(_event) -> bool:
    return False


def conversar(
    client: anthropic.Anthropic,
    session_id: str,
    texto: str,
    aprovar: Callable[[object], bool] = _negar,
) -> Iterator[str]:
    """Envia `texto` e gera cada mensagem do agente até ele ficar ocioso.

    A última mensagem do turno é a resposta; as anteriores são notas de progresso.

    `aprovar(event)` decide chamadas de ferramenta que pausam pedindo confirmação
    (evaluated_permission == "ask"); o padrão nega, que é o seguro sem humano olhando.
    Levanta AssistenteErro em erro terminal do agente.
    """
    # Stream primeiro, depois envia: o stream só entrega eventos posteriores à abertura.
    with client.beta.sessions.events.stream(session_id=session_id) as stream:
        client.beta.sessions.events.send(
            session_id=session_id,
            events=[{"type": "user.message", "content": [{"type": "text", "text": texto}]}],
        )
        for event in stream:
            if event.type == "agent.message":
                # Uma mensagem inteira por evento: entre ferramentas o agente solta notas
                # de progresso; quem consome decide mostrar só a última como resposta.
                texto_msg = "".join(b.text for b in event.content if b.type == "text")
                if texto_msg:
                    yield texto_msg
            elif event.type in ("agent.tool_use", "agent.mcp_tool_use") and event.evaluated_permission == "ask":
                permitido = aprovar(event)
                confirmacao = {
                    "type": "user.tool_confirmation",
                    "tool_use_id": event.id,  # é o sevt_..., não um toolu_...
                    "result": "allow" if permitido else "deny",
                }
                if not permitido:
                    confirmacao["deny_message"] = "Negado pelo usuário do RevCalc."
                client.beta.sessions.events.send(session_id=session_id, events=[confirmacao])
            elif event.type == "session.error":
                # "retrying" = o servidor tenta de novo sozinho; os demais encerram o turno.
                if event.error.retry_status.type != "retrying":
                    raise AssistenteErro(f"{event.error.type}: {getattr(event.error, 'message', '')}".rstrip(": "))
            elif event.type == "session.status_idle":
                # requires_action = esperando a confirmação acima; qualquer outro motivo encerra o turno.
                if event.stop_reason.type == "requires_action":
                    continue
                if event.stop_reason.type == "retries_exhausted":
                    raise AssistenteErro("o agente esgotou as tentativas neste turno")
                if event.stop_reason.type == "budget_reached":
                    raise AssistenteErro("a sessão atingiu o teto de gasto")
                return
            elif event.type == "session.status_terminated":
                raise AssistenteErro("a sessão foi encerrada")


# ─── CLI ────────────────────────────────────────────────────────────────────

def _aprovar_no_terminal(event) -> bool:
    nome = getattr(event, "name", "ferramenta")
    resp = input(f"\n[o agente quer usar {nome!r} — permitir? s/N] ").strip().lower()
    return resp in ("s", "sim", "y", "yes")


def _perguntar(client: anthropic.Anthropic, session_id: str, texto: str) -> None:
    mensagens: list[str] = []
    for msg in conversar(client, session_id, texto, aprovar=_aprovar_no_terminal):
        if mensagens:
            print(f"  … {mensagens[-1]}", file=sys.stderr, flush=True)
        mensagens.append(msg)
    if mensagens:
        print(mensagens[-1])


def main(argv: Optional[list[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not habilitado():
        print("configure ANTHROPIC_API_KEY e " + ", ".join(CONFIG), file=sys.stderr)
        return 1
    client = criar_cliente()
    session_id: Optional[str] = None
    try:
        session_id = criar_sessao(client)
        print(f"sessão {session_id}", file=sys.stderr)
        if argv:
            _perguntar(client, session_id, " ".join(argv))
            return 0
        while True:
            try:
                texto = input("\nvocê> ").strip()
            except EOFError:
                return 0
            if texto in ("", "sair", "exit"):
                return 0
            _perguntar(client, session_id, texto)
    except KeyboardInterrupt:
        if session_id:
            try:
                client.beta.sessions.events.send(session_id=session_id, events=[{"type": "user.interrupt"}])
            except anthropic.APIError:
                pass
        print("\ninterrompido", file=sys.stderr)
        return 130
    except AssistenteErro as e:
        print(f"\nerro do agente: {e}", file=sys.stderr)
        return 1
    except anthropic.AuthenticationError:
        print("credencial Anthropic inválida ou ausente (ANTHROPIC_API_KEY)", file=sys.stderr)
        return 1
    except anthropic.NotFoundError as e:
        print(f"agente/ambiente/sessão não encontrado: {e.message}", file=sys.stderr)
        return 1
    except anthropic.RateLimitError:
        print("limite de taxa da Anthropic — tente de novo em instantes", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as e:
        print(f"erro da API Anthropic ({e.status_code}): {e.message}", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError:
        print("sem conexão com a API Anthropic", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
