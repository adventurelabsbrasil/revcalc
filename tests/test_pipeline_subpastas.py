"""Orquestração v0.9.4: processa pasta raiz + subpastas diretas com contrato."""

from __future__ import annotations

import pytest

from calculadora_crefaz import pipeline
from calculadora_crefaz.drive import PastaCliente
from calculadora_crefaz.exceptions import ContratoNaoEncontrado
from calculadora_crefaz.log_writer import ArquivoGerado
from calculadora_crefaz.pipeline import ResultadoPipeline


class _FakeSessao:
    email = "test@adventurelabs.com.br"

    def drive_service(self):
        return object()


def _resultado(path: str, arquivos: list[ArquivoGerado]) -> ResultadoPipeline:
    return ResultadoPipeline(
        pasta_drive_path=path,
        pasta_drive_url="url",
        xlsx_file_id="x",
        log_file_id="",
        bacen_file_id=None,
        arquivos_gerados=arquivos,
        files_added=len(arquivos),
    )


def test_processa_raiz_e_subpastas_pula_sem_contrato(monkeypatch):
    raiz = PastaCliente("R", "VLADIMIR ALMEIDA LOPES", "EMP/UF/VLADIMIR ALMEIDA LOPES")
    sub1 = PastaCliente("S1", "Quitado 01", "EMP/UF/VLADIMIR ALMEIDA LOPES/Quitado 01")
    sub2 = PastaCliente("S2", "Documentos", "EMP/UF/VLADIMIR ALMEIDA LOPES/Documentos")

    monkeypatch.setattr(pipeline.drive, "localizar_pasta_cliente", lambda s, n: raiz)
    monkeypatch.setattr(pipeline.drive, "listar_subpastas", lambda s, p: [sub1, sub2])
    monkeypatch.setattr(pipeline.drive, "url_pasta", lambda i: f"url/{i}")

    def fake_proc(service, sessao, pasta, **kw):
        if pasta is sub2:  # subpasta de documentos, sem contrato → pulada
            raise ContratoNaoEncontrado("no contract")
        return _resultado(pasta.path, [ArquivoGerado("Calculo.xlsx", "novo")])

    monkeypatch.setattr(pipeline, "_processar_pasta", fake_proc)

    msgs: list[str] = []
    res = pipeline.executar("VLADIMIR ALMEIDA", _FakeSessao(), status=msgs.append)

    nomes = [a.nome for a in res.arquivos_gerados]
    assert "Calculo.xlsx" in nomes                  # raiz: sem prefixo
    assert "Quitado 01/Calculo.xlsx" in nomes       # subpasta: prefixo «<subpasta>/»
    assert res.files_added == 2                      # raiz + sub1 (sub2 pulada)
    assert res.pasta_drive_path == raiz.path         # aponta pra raiz (abrir pasta)
    assert any("skipped" in m and "Documentos" in m for m in msgs)


def test_erro_se_nenhuma_pasta_tem_contrato(monkeypatch):
    raiz = PastaCliente("R", "FULANO DE TAL", "EMP/UF/FULANO DE TAL")
    monkeypatch.setattr(pipeline.drive, "localizar_pasta_cliente", lambda s, n: raiz)
    monkeypatch.setattr(pipeline.drive, "listar_subpastas", lambda s, p: [])

    def fake_proc(*a, **k):
        raise ContratoNaoEncontrado("no contract")

    monkeypatch.setattr(pipeline, "_processar_pasta", fake_proc)

    with pytest.raises(ContratoNaoEncontrado):
        pipeline.executar("FULANO DE TAL", _FakeSessao(), status=lambda _: None)
