"""Registry de runs + ponte thread→asyncio para o SSE.

O pipeline é síncrono e bloqueante (faz I/O de rede e roda LibreOffice). Rodamos
cada run num executor (thread), e os callbacks `status`/`aviso` do pipeline
empurram eventos para uma `asyncio.Queue` via `loop.call_soon_threadsafe`. O
endpoint SSE drena essa fila e emite frames até o evento terminal (done/error).

É o análogo web do padrão `queue.Queue` + `_drain_queue_loop` do ui.py desktop.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from calculadora_crefaz.auth_core import SessaoAutenticada
from calculadora_crefaz.pipeline import (
    ClienteResultado,
    ResultadoLote,
    ResultadoPipeline,
    executar_lote,
)

logger = logging.getLogger(__name__)

# Evento sentinela que fecha o gerador SSE.
FIM = {"type": "_end"}


def _resultado_para_dict(res: ResultadoPipeline) -> dict[str, Any]:
    return {
        "pasta_drive_path": res.pasta_drive_path,
        "pasta_drive_url": res.pasta_drive_url,
        "xlsx_file_id": res.xlsx_file_id,
        "arquivos_gerados": [
            {"nome": a.nome, "status": str(a.status)} for a in res.arquivos_gerados
        ],
        "pulados": list(res.pulados),
    }


def _cliente_para_dict(c: ClienteResultado) -> dict[str, Any]:
    d: dict[str, Any] = {"nome": c.nome, "status": c.status}
    if c.resultado is not None:
        d["resultado"] = _resultado_para_dict(c.resultado)
    if c.erro:
        d["erro"] = c.erro
    if c.sugestoes:
        d["sugestoes"] = list(c.sugestoes)
    if c.paths:
        d["paths"] = list(c.paths)
    return d


def _lote_para_dict(res: ResultadoLote) -> dict[str, Any]:
    return {
        "clientes": [_cliente_para_dict(c) for c in res.clientes],
        "resumo": dict(res.resumo),
    }


@dataclass
class Run:
    id: str
    email: str
    queue: "asyncio.Queue[dict]" = field(default_factory=asyncio.Queue)
    future: Optional[asyncio.Future] = None


class RunManager:
    """Mantém runs ativos em memória (single-firm; sem persistência entre restarts)."""

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}

    def criar(self, email: str) -> Run:
        run = Run(id=uuid.uuid4().hex, email=email)
        self._runs[run.id] = run
        return run

    def obter(self, run_id: str) -> Optional[Run]:
        return self._runs.get(run_id)

    def remover(self, run_id: str) -> None:
        self._runs.pop(run_id, None)

    def iniciar(
        self,
        run: Run,
        sessao: SessaoAutenticada,
        nomes: list[str],
    ) -> None:
        """Agenda o lote de clientes numa thread; eventos fluem para run.queue.

        v0.9.8: um run processa N clientes em sequência (executar_lote). Erros
        por-cliente viram status no relatório; só falha inesperada global emite
        `error`. O `done` carrega o relatório por-cliente (_lote_para_dict)."""
        loop = asyncio.get_running_loop()

        def emit(tipo: str, **kw: Any) -> None:
            loop.call_soon_threadsafe(run.queue.put_nowait, {"type": tipo, **kw})

        def status_cb(msg: str) -> None:
            emit("status", level="info", message=msg)

        def aviso_cb(msg: str) -> None:
            emit("status", level="aviso", message=msg)

        def trabalho() -> None:
            try:
                res = executar_lote(
                    nomes,
                    sessao,
                    status=status_cb,
                    aviso=aviso_cb,
                )
                emit("done", result=_lote_para_dict(res))
            except Exception as e:  # noqa: BLE001 — erro inesperado vira evento, não crash
                logger.exception("Run %s falhou inesperadamente", run.id)
                emit("error", error=f"Erro inesperado: {e}", kind="Exception")
            finally:
                loop.call_soon_threadsafe(run.queue.put_nowait, FIM)

        run.future = loop.run_in_executor(None, trabalho)


# Instância única do processo.
manager = RunManager()
