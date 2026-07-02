"""v0.9.8: (1) pular contrato já calculado (não refazer) e (2) lote de clientes.

Cobre a regra pedida pela cliente — cálculo existente é PULADO (não abortado nem
refeito) — e o novo `executar_lote` que processa vários clientes numa tanda, com
erro por-cliente isolado (um nome ruim não derruba os demais).
"""

from __future__ import annotations

import pytest

from calculadora_crefaz import pipeline
from calculadora_crefaz.drive import PastaCliente
from calculadora_crefaz.exceptions import (
    CalculoJaExiste,
    ContratoNaoEncontrado,
    PastaAmbigua,
    PastaNaoEncontrada,
)
from calculadora_crefaz.log_writer import ArquivoGerado
from calculadora_crefaz.pipeline import ResultadoPipeline
from server.run_input import extrair_nomes


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


# ── (1) Regra de pular ────────────────────────────────────────────────────────


def test_pula_pasta_com_calculo_e_processa_as_demais(monkeypatch):
    """Pasta com cálculo é pulada; as outras processam; o run NÃO aborta."""
    raiz = PastaCliente("R", "FULANO DE TAL", "EMP/UF/FULANO DE TAL")
    sub1 = PastaCliente("S1", "Quitado 01", "EMP/UF/FULANO DE TAL/Quitado 01")

    monkeypatch.setattr(pipeline.drive, "localizar_pasta_cliente", lambda s, n: raiz)
    monkeypatch.setattr(pipeline.drive, "listar_subpastas", lambda s, p: [sub1])
    monkeypatch.setattr(pipeline.drive, "url_pasta", lambda i: f"url/{i}")

    def fake_proc(service, sessao, pasta, **kw):
        if pasta is sub1:  # já tem cálculo → pulada
            raise CalculoJaExiste(pasta.nome_real, "Calculo quitado.xlsx")
        return _resultado(pasta.path, [ArquivoGerado("Calculo.xlsx", "novo")])

    monkeypatch.setattr(pipeline, "_processar_pasta", fake_proc)

    res = pipeline.executar("FULANO DE TAL", _FakeSessao(), status=lambda _: None)

    assert [a.nome for a in res.arquivos_gerados] == ["Calculo.xlsx"]  # só a raiz
    assert res.pulados == [{"pasta": "Quitado 01", "arquivo": "Calculo quitado.xlsx"}]


def test_tudo_ja_calculado_nao_e_erro(monkeypatch):
    """Todos os contratos já feitos → resultado 'nada novo' com pulados, sem raise."""
    raiz = PastaCliente("R", "FULANO DE TAL", "EMP/UF/FULANO DE TAL")
    sub1 = PastaCliente("S1", "Quitado 01", "EMP/UF/FULANO DE TAL/Quitado 01")

    monkeypatch.setattr(pipeline.drive, "localizar_pasta_cliente", lambda s, n: raiz)
    monkeypatch.setattr(pipeline.drive, "listar_subpastas", lambda s, p: [sub1])
    monkeypatch.setattr(pipeline.drive, "url_pasta", lambda i: f"url/{i}")

    def fake_proc(service, sessao, pasta, **kw):
        raise CalculoJaExiste(pasta.nome_real, "Calculo.xlsx")

    monkeypatch.setattr(pipeline, "_processar_pasta", fake_proc)

    res = pipeline.executar("FULANO DE TAL", _FakeSessao(), status=lambda _: None)

    assert res.arquivos_gerados == []
    assert {p["pasta"] for p in res.pulados} == {"FULANO DE TAL", "Quitado 01"}
    assert res.pasta_drive_url  # aponta pra pasta raiz (abrir no Drive)


def test_sem_contrato_em_lugar_nenhum_ainda_levanta(monkeypatch):
    """Nenhum contrato E nenhum pulado → continua ContratoNaoEncontrado."""
    raiz = PastaCliente("R", "FULANO DE TAL", "EMP/UF/FULANO DE TAL")
    monkeypatch.setattr(pipeline.drive, "localizar_pasta_cliente", lambda s, n: raiz)
    monkeypatch.setattr(pipeline.drive, "listar_subpastas", lambda s, p: [])
    monkeypatch.setattr(pipeline, "_processar_pasta",
                        lambda *a, **k: (_ for _ in ()).throw(ContratoNaoEncontrado("x")))

    with pytest.raises(ContratoNaoEncontrado):
        pipeline.executar("FULANO DE TAL", _FakeSessao(), status=lambda _: None)


# ── (2) Lote de clientes ──────────────────────────────────────────────────────


def test_executar_lote_isola_erro_por_cliente(monkeypatch):
    """Sucesso, nada-novo, não-encontrado e erro num mesmo lote — nada interrompe."""

    def fake_executar(nome, sessao, **kw):
        if nome == "ANA OK":
            return _resultado("EMP/ANA OK", [ArquivoGerado("Calculo.xlsx", "novo")])
        if nome == "BRUNO FEITO":
            r = _resultado("EMP/BRUNO FEITO", [])
            r.pulados = [{"pasta": "BRUNO FEITO", "arquivo": "Calculo.xlsx"}]
            return r
        if nome == "CARLOS SUMIU":
            raise PastaNaoEncontrada("CARLOS SUMIU", sugestoes=["CARLOS SILVA"])
        if nome == "DORA DUPLA":
            raise PastaAmbigua("DORA DUPLA", paths=["EMP/A/DORA", "EMP/B/DORA"])
        raise ContratoNaoEncontrado("sem contrato")

    monkeypatch.setattr(pipeline, "executar", fake_executar)

    nomes = ["ANA OK", "BRUNO FEITO", "CARLOS SUMIU", "DORA DUPLA", "ERRO QUALQUER"]
    lote = pipeline.executar_lote(nomes, _FakeSessao(), status=lambda _: None)

    por_nome = {c.nome: c for c in lote.clientes}
    assert por_nome["ANA OK"].status == "ok"
    assert por_nome["BRUNO FEITO"].status == "nada_novo"
    assert por_nome["CARLOS SUMIU"].status == "nao_encontrado"
    assert por_nome["CARLOS SUMIU"].sugestoes == ["CARLOS SILVA"]
    assert por_nome["DORA DUPLA"].status == "ambiguo"
    assert por_nome["ERRO QUALQUER"].status == "erro"

    assert lote.resumo["total"] == 5
    assert lote.resumo["ok"] == 1
    assert lote.resumo["nada_novo"] == 1
    assert lote.resumo["nao_encontrados"] == 2  # não-encontrado + ambíguo
    assert lote.resumo["erros"] == 1
    assert lote.resumo["pulados_total"] == 1


# ── (3) Endpoint: normalização de nomes ──────────────────────────────────────


def test_extrair_nomes_lista_filtra_invalidos():
    body = {"nomes": ["Maria das Dores", "  ", "Solteiro", "  João  Silva  ", 42]}
    assert extrair_nomes(body) == ["Maria das Dores", "João Silva"]


def test_extrair_nomes_compat_single():
    assert extrair_nomes({"nome": "Ana Paula Souza"}) == ["Ana Paula Souza"]
    assert extrair_nomes({"nome": "Solteiro"}) == []


def test_extrair_nomes_vazio_ou_formato_invalido():
    assert extrair_nomes({}) == []
    assert extrair_nomes({"nomes": "Maria Dores"}) == []  # string, não lista
