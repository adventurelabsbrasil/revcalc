"""FastAPI: embrulha o pipeline desktop num serviço web com OAuth + SSE.

Rotas:
  GET  /healthz                      — liveness + se o LibreOffice está disponível
  GET  /api/auth/login               — redireciona pro consent do Google
  GET  /api/auth/callback            — troca code, valida domínio, seta cookie de sessão
  POST /api/auth/logout              — limpa cookie + apaga token
  GET  /api/me                       — { email } do usuário logado (401 se não)
  GET  /api/feedback/config          — { enabled } p/ o front saber se mostra a caixa
  POST /api/feedback                 — registra feedback (feat/bug/erro_sistema/duvida)
  POST /api/run                      — inicia run; pré-check de dedup → 409
  GET  /api/run/{id}/events?t=token  — SSE com o progresso ao vivo

O motor de cálculo (calculadora_crefaz) roda inalterado dentro do container.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from calculadora_crefaz import __version__ as ENGINE_VERSION, drive
from calculadora_crefaz.exceptions import (
    AuthError,
    CalculadoraError,
    PastaAmbigua,
    PastaNaoEncontrada,
)

from . import auth_web, feedback, token_store
from .sessions import FIM, manager
from .settings import get_settings

logger = logging.getLogger(__name__)

STATE_COOKIE = "revcalc_oauth_state"
VERIFIER_COOKIE = "revcalc_oauth_verifier"  # PKCE code_verifier (assinado), par do STATE_COOKIE
SSE_PING_TIMEOUT = 15  # segundos entre pings p/ manter a conexão SSE viva atrás de proxy


# ─── Cookies de sessão ──────────────────────────────────────────────────────

def _set_session_cookie(resp: Response, email: str) -> None:
    s = get_settings()
    resp.set_cookie(
        key=s.cookie_name,
        value=auth_web.assinar_sessao(email),
        max_age=auth_web.SESSION_MAX_AGE,
        httponly=True,
        secure=s.cookie_secure,
        samesite=s.cookie_samesite,
        domain=s.cookie_domain,
        path="/",
    )


def _clear_session_cookie(resp: Response) -> None:
    s = get_settings()
    resp.delete_cookie(key=s.cookie_name, domain=s.cookie_domain, path="/")


def _email_da_sessao(request: Request) -> Optional[str]:
    s = get_settings()
    token = request.cookies.get(s.cookie_name)
    if not token:
        return None
    return auth_web.ler_sessao(token)


# ─── App factory ────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Calculadora Crefaz — API", version=ENGINE_VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[s.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health ──
    @app.get("/healthz")
    async def healthz() -> dict:
        libreoffice = bool(shutil.which("soffice") or shutil.which("libreoffice"))
        return {"status": "ok", "libreoffice": libreoffice, "version": ENGINE_VERSION}

    # ── OAuth ──
    @app.get("/api/auth/login")
    async def login() -> Response:
        auth_url, state, code_verifier = auth_web.authorization_url()
        resp = RedirectResponse(auth_url, status_code=302)
        cookie_kw = dict(
            max_age=auth_web.STATE_MAX_AGE,
            httponly=True,
            secure=s.cookie_secure,
            samesite=s.cookie_samesite,
            domain=s.cookie_domain,
            path="/",
        )
        resp.set_cookie(key=STATE_COOKIE, value=auth_web.assinar_state(state), **cookie_kw)
        resp.set_cookie(
            key=VERIFIER_COOKIE, value=auth_web.assinar_verifier(code_verifier), **cookie_kw
        )
        return resp

    @app.get("/api/auth/callback")
    async def callback(request: Request) -> Response:
        params = request.query_params
        if params.get("error"):
            return RedirectResponse(f"{s.frontend_origin}/?error=consent_negado", 302)

        code = params.get("code")
        state_recebido = params.get("state")
        state_cookie = request.cookies.get(STATE_COOKIE)
        state_esperado = auth_web.ler_state(state_cookie) if state_cookie else None
        verifier_cookie = request.cookies.get(VERIFIER_COOKIE)
        code_verifier = auth_web.ler_verifier(verifier_cookie) if verifier_cookie else None

        if not code or not state_recebido or state_recebido != state_esperado:
            return RedirectResponse(f"{s.frontend_origin}/?error=state_invalido", 302)

        try:
            email, creds = auth_web.trocar_code(
                code, state=state_recebido, code_verifier=code_verifier
            )
        except AuthError as e:
            logger.warning("Login bloqueado: %s", e)
            return RedirectResponse(f"{s.frontend_origin}/?error=dominio_nao_autorizado", 302)
        except Exception as e:  # noqa: BLE001
            logger.exception("Falha na troca do code")
            return RedirectResponse(f"{s.frontend_origin}/?error=falha_oauth", 302)

        token_store.save(email, creds)
        resp = RedirectResponse(f"{s.frontend_origin}/?logado=1", 302)
        _set_session_cookie(resp, email)
        resp.delete_cookie(key=STATE_COOKIE, domain=s.cookie_domain, path="/")
        resp.delete_cookie(key=VERIFIER_COOKIE, domain=s.cookie_domain, path="/")
        return resp

    @app.post("/api/auth/logout")
    async def logout(request: Request) -> Response:
        email = _email_da_sessao(request)
        if email:
            token_store.delete(email)
        resp = Response(status_code=204)
        _clear_session_cookie(resp)
        return resp

    @app.get("/api/me")
    async def me(request: Request) -> Response:
        email = _email_da_sessao(request)
        if not email:
            return JSONResponse({"error": "nao_autenticado"}, status_code=401)
        return JSONResponse({"email": email})

    # ── Feedback ──
    @app.get("/api/feedback/config")
    async def feedback_config() -> Response:
        return JSONResponse({"enabled": feedback.enabled()})

    @app.post("/api/feedback")
    async def feedback_submit(request: Request) -> Response:
        email = _email_da_sessao(request)
        if not email:
            return JSONResponse({"error": "nao_autenticado"}, status_code=401)

        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = {}

        try:
            criado = await feedback.registrar(
                tipo=body.get("tipo"),
                mensagem=body.get("mensagem"),
                email=email,
                origem=body.get("origem", "manual"),
                contexto=body.get("contexto"),
            )
        except feedback.FeedbackIndisponivel as e:
            return JSONResponse({"error": str(e)}, status_code=503)
        except feedback.FeedbackError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        except Exception:  # noqa: BLE001
            logger.exception("Falha inesperada no feedback")
            return JSONResponse(
                {"error": "Não foi possível registrar o feedback agora."}, status_code=500
            )

        return JSONResponse({"ok": True, "id": criado.get("id")}, status_code=201)

    # ── Run ──
    @app.post("/api/run")
    async def run(request: Request) -> Response:
        email = _email_da_sessao(request)
        if not email:
            return JSONResponse({"error": "nao_autenticado"}, status_code=401)

        body = await request.json()
        nome = (body.get("nome") or "").strip()
        forcar = bool(body.get("forcar", False))

        if len(nome.split()) < 2:
            return JSONResponse(
                {"error": "Digite o nome completo (mínimo 2 palavras)."}, status_code=400
            )

        sessao = token_store.carregar_sessao(email)
        if not sessao:
            # Token expirado/revogado → precisa relogar.
            resp = JSONResponse({"error": "sessao_expirada"}, status_code=401)
            _clear_session_cookie(resp)
            return resp

        # Pré-check (localizar pasta + dedup) numa thread — chamadas Drive bloqueantes.
        try:
            pre = await asyncio.to_thread(_precheck, sessao, nome, forcar)
        except PastaNaoEncontrada as e:
            return JSONResponse(
                {"error": str(e), "sugestoes": e.sugestoes}, status_code=404
            )
        except PastaAmbigua as e:
            return JSONResponse({"error": str(e), "paths": e.paths}, status_code=409)
        except CalculadoraError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

        if pre is not None:
            # Cálculo já existe e usuário não forçou → pede confirmação.
            return JSONResponse(
                {
                    "needs_confirmation": True,
                    "nome_arquivo": pre["nome_arquivo"],
                    "modified_time": pre["modified_time"],
                },
                status_code=409,
            )

        run_obj = manager.criar(email)
        manager.iniciar(run_obj, sessao, nome, forcar_sobrescrita=forcar)
        stream_token = auth_web.assinar_stream_token(run_obj.id, email)
        return JSONResponse(
            {
                "run_id": run_obj.id,
                "events_url": f"/api/run/{run_obj.id}/events?t={stream_token}",
            }
        )

    @app.get("/api/run/{run_id}/events")
    async def run_events(run_id: str, t: str = "") -> Response:
        payload = auth_web.ler_stream_token(t)
        if not payload or payload.get("run_id") != run_id:
            return JSONResponse({"error": "stream_token_invalido"}, status_code=403)

        run_obj = manager.obter(run_id)
        if not run_obj or run_obj.email != payload.get("email"):
            return JSONResponse({"error": "run_inexistente"}, status_code=404)

        async def gen():
            try:
                while True:
                    try:
                        ev = await asyncio.wait_for(
                            run_obj.queue.get(), timeout=SSE_PING_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"  # comentário SSE = keep-alive
                        continue
                    if ev is FIM:
                        break
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            finally:
                manager.remover(run_id)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # desliga buffering do nginx/proxy
            },
        )

    return app


def _precheck(sessao, nome: str, forcar: bool) -> Optional[dict]:
    """Localiza a pasta e checa dedup. Retorna dict se há cálculo a confirmar, senão None.

    Levanta PastaNaoEncontrada/PastaAmbigua/CalculadoraError (mapeadas no endpoint).
    """
    service = sessao.drive_service()
    pasta = drive.localizar_pasta_cliente(service, nome)
    if forcar:
        return None
    existente = drive.buscar_calculo_existente(service, pasta.id)
    if existente:
        return {
            "nome_arquivo": existente.name,
            "modified_time": existente.modified_time or "data desconhecida",
        }
    return None


# Instância p/ uvicorn: `uvicorn server.app:app`
app = create_app()
