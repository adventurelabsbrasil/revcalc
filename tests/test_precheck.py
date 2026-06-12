"""Pré-check de dedup (v0.9.5): varre pasta raiz + subpastas diretas.

Confirma que `_precheck` lista TODAS as pastas que serão sobrescritas (têm
contrato Crefaz E cálculo prévio), e ignora subpastas sem contrato — fechando o
gap em que subpastas eram sobrescritas sem aviso (bug do VLADIMIR).
"""

from __future__ import annotations

import pytest

from calculadora_crefaz.drive import ArquivoDrive, PastaCliente
from calculadora_crefaz.exceptions import ContratoNaoEncontrado
from server import app as app_module


class _FakeSessao:
    def drive_service(self):
        return object()


def _calc(name: str) -> ArquivoDrive:
    return ArquivoDrive(id=f"id-{name}", name=name, mime_type="xlsx", modified_time="2026-06-10")


def _patch_drive(monkeypatch, *, raiz, subpastas, calc_por_id, com_contrato_ids):
    monkeypatch.setattr(app_module.drive, "localizar_pasta_cliente", lambda s, n: raiz)
    monkeypatch.setattr(app_module.drive, "listar_subpastas", lambda s, p: subpastas)
    monkeypatch.setattr(
        app_module.drive, "buscar_calculo_existente", lambda s, pid: calc_por_id.get(pid)
    )

    def _loc_contrato(service, pid, forcar_nome=None):
        if pid in com_contrato_ids:
            return ArquivoDrive(id="c", name="01 Contrato Crefaz.pdf", mime_type="pdf")
        raise ContratoNaoEncontrado("sem contrato")

    monkeypatch.setattr(app_module.drive, "localizar_contrato", _loc_contrato)


def test_varre_raiz_e_subpastas_lista_apenas_com_contrato(monkeypatch):
    raiz = PastaCliente("R", "VLADIMIR ALMEIDA LOPES", "EMP/UF/VLADIMIR ALMEIDA LOPES")
    sub1 = PastaCliente("S1", "Quitado 01", "EMP/UF/VLADIMIR ALMEIDA LOPES/Quitado 01")
    docs = PastaCliente("S2", "Documentos", "EMP/UF/VLADIMIR ALMEIDA LOPES/Documentos")

    _patch_drive(
        monkeypatch,
        raiz=raiz,
        subpastas=[sub1, docs],
        calc_por_id={
            "R": _calc("Calculo.xlsx"),
            "S1": _calc("Calculo quitado.xlsx"),
            "S2": _calc("Calculo.xlsx"),  # tem cálculo, mas...
        },
        com_contrato_ids={"R", "S1"},  # ...Documentos NÃO tem contrato → ignorada
    )

    existentes = app_module._precheck(_FakeSessao(), "VLADIMIR ALMEIDA", forcar=False)

    pastas = {e["pasta"] for e in existentes}
    assert pastas == {"VLADIMIR ALMEIDA LOPES", "Quitado 01"}  # Documentos fora
    raiz_item = next(e for e in existentes if e["is_raiz"])
    assert raiz_item["nome_arquivo"] == "Calculo.xlsx"
    sub_item = next(e for e in existentes if not e["is_raiz"])
    assert sub_item["pasta"] == "Quitado 01"
    assert sub_item["nome_arquivo"] == "Calculo quitado.xlsx"


def test_forcar_pula_o_check(monkeypatch):
    raiz = PastaCliente("R", "FULANO", "EMP/FULANO")
    _patch_drive(
        monkeypatch,
        raiz=raiz,
        subpastas=[],
        calc_por_id={"R": _calc("Calculo.xlsx")},
        com_contrato_ids={"R"},
    )
    assert app_module._precheck(_FakeSessao(), "FULANO DE TAL", forcar=True) == []


def test_sem_calculo_previo_retorna_vazio(monkeypatch):
    raiz = PastaCliente("R", "FULANO", "EMP/FULANO")
    _patch_drive(
        monkeypatch,
        raiz=raiz,
        subpastas=[PastaCliente("S1", "Quitado 01", "EMP/FULANO/Quitado 01")],
        calc_por_id={},  # nenhuma pasta tem cálculo
        com_contrato_ids={"R", "S1"},
    )
    assert app_module._precheck(_FakeSessao(), "FULANO DE TAL", forcar=False) == []


def test_subpasta_com_calculo_sem_contrato_nao_conta(monkeypatch):
    raiz = PastaCliente("R", "FULANO", "EMP/FULANO")
    sub1 = PastaCliente("S1", "Antigo", "EMP/FULANO/Antigo")
    _patch_drive(
        monkeypatch,
        raiz=raiz,
        subpastas=[sub1],
        calc_por_id={"S1": _calc("Calculo quitado.xlsx")},
        com_contrato_ids=set(),  # nenhuma tem contrato
    )
    assert app_module._precheck(_FakeSessao(), "FULANO DE TAL", forcar=False) == []
