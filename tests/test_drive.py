"""Testes do módulo drive — usa mocks do googleapiclient."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from calculadora_crefaz.drive import (
    _e_bacen_pasta_cliente,
    _e_calculo_existente,
    _e_contrato,
    _nome_combina,
    _norm,
    localizar_contrato,
    localizar_pasta_cliente,
)
from calculadora_crefaz.exceptions import (
    ContratoAmbiguo,
    ContratoNaoEncontrado,
    PastaAmbigua,
    PastaNaoEncontrada,
)


# ─── Normalização ───────────────────────────────────────────────────────────


def test_norm_remove_acentos():
    assert _norm("MARLÍ SUELÍ") == "marli sueli"


def test_norm_colapsa_espacos():
    assert _norm("  Marli   Sueli  ") == "marli sueli"


def test_nome_combina_com_e_sem_acento():
    assert _nome_combina(
        "Marli Sueli Berger Dambrosio",
        "MARLÍ SUELÍ BERGER DAMBRÓSIO",
    )


def test_nome_combina_diferente():
    assert not _nome_combina("Marli Sueli", "Adriano Luis")


# ─── _e_contrato ────────────────────────────────────────────────────────────


class TestEContrato:
    def test_padrao_numerado(self):
        assert _e_contrato("09 Contrato Crefaz.pdf")

    def test_sem_numero(self):
        assert _e_contrato("Contrato Crefaz.pdf")

    def test_com_sufixo(self):
        assert _e_contrato("09 Contrato Crefaz Adriano.pdf")

    def test_case_insensitive(self):
        assert _e_contrato("09 CONTRATO CREFAZ.pdf")

    def test_procuracao_nao_e_contrato(self):
        assert not _e_contrato("01 Procuração.pdf")

    def test_cnh_nao_e_contrato(self):
        assert not _e_contrato("02 CNH.pdf")

    def test_calculo_nao_e_contrato(self):
        assert not _e_contrato("10 Cálculo Marli.xlsx")

    def test_log_nao_e_contrato(self):
        assert not _e_contrato("12 Log.txt")

    def test_contrato_honorarios_excluido(self):
        assert not _e_contrato("Contrato Honorários.pdf")

    def test_kit_procuracao_excluido(self):
        assert not _e_contrato("Kit Procuração.pdf")

    def test_copia_excluida(self):
        assert not _e_contrato("Cópia de 09 Contrato Crefaz.pdf")

    def test_outro_pdf_qualquer(self):
        assert not _e_contrato("documento qualquer.pdf")


# ─── _e_bacen_pasta_cliente / _e_calculo_existente ──────────────────────────


def test_e_bacen_pasta_cliente_padrao():
    assert _e_bacen_pasta_cliente("11 Series Temporais.pdf")
    assert _e_bacen_pasta_cliente("11 Séries Temporais.pdf")
    assert _e_bacen_pasta_cliente("11 series temporais (1).pdf")


def test_e_bacen_pasta_cliente_copia_ignorada():
    assert not _e_bacen_pasta_cliente("Cópia de 11 Series Temporais.pdf")


def test_e_calculo_existente():
    assert _e_calculo_existente("10 Cálculo MARLI SUELI.xlsx")
    assert _e_calculo_existente("10 Calculo MARLI.xlsx")
    assert not _e_calculo_existente("10 contrato.xlsx")
    assert not _e_calculo_existente("calculo qualquer.xlsx")


# ─── localizar_pasta_cliente — via mock do service ──────────────────────────


def _mock_service_drive(estrutura: dict):
    """Constrói um mock do service do Drive a partir de um dict simulado.

    estrutura:
        {
            <parent_id>: [{name, id, mimeType}, ...],
            ...
        }
    """
    service = MagicMock()

    def fake_list(q=None, **kwargs):
        # Extrair parent_id do query string: "'<id>' in parents..."
        import re

        m = re.search(r"'([^']+)' in parents", q)
        parent = m.group(1) if m else None
        items = estrutura.get(parent, [])

        # Aplicar filtro de mimeType se houver
        m2 = re.search(r"mimeType = '([^']+)'", q)
        if m2:
            items = [i for i in items if i.get("mimeType") == m2.group(1)]

        execute_result = {"files": items, "nextPageToken": None}
        execute_mock = MagicMock()
        execute_mock.execute.return_value = execute_result
        return execute_mock

    service.files().list = fake_list
    return service


def test_localizar_pasta_no_nivel_1():
    service = _mock_service_drive(
        {
            "1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN": [
                {
                    "id": "abc",
                    "name": "MARIA DA SILVA",
                    "mimeType": "application/vnd.google-apps.folder",
                }
            ]
        }
    )
    pasta = localizar_pasta_cliente(service, "Maria da Silva")
    assert pasta.id == "abc"
    assert pasta.path == "EMPRESTIMO DE ENERGIA/MARIA DA SILVA"


def test_localizar_pasta_no_nivel_2_estado():
    service = _mock_service_drive(
        {
            "1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN": [
                {
                    "id": "rs-id",
                    "name": "10. RIO GRANDE DO SUL",
                    "mimeType": "application/vnd.google-apps.folder",
                }
            ],
            "rs-id": [
                {
                    "id": "marli-id",
                    "name": "MARLÍ SUELÍ BERGER DAMBRÓSIO",
                    "mimeType": "application/vnd.google-apps.folder",
                }
            ],
        }
    )
    pasta = localizar_pasta_cliente(service, "Marli Sueli Berger Dambrosio")
    assert pasta.id == "marli-id"
    assert "RIO GRANDE DO SUL" in pasta.path


def test_pasta_nao_encontrada_traz_sugestoes():
    service = _mock_service_drive(
        {
            "1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN": [
                {
                    "id": "rs-id",
                    "name": "10. RIO GRANDE DO SUL",
                    "mimeType": "application/vnd.google-apps.folder",
                },
                {
                    "id": "outra",
                    "name": "MARLI SUELI BERGER",
                    "mimeType": "application/vnd.google-apps.folder",
                },
            ],
            "rs-id": [],
        }
    )
    with pytest.raises(PastaNaoEncontrada) as exc:
        localizar_pasta_cliente(service, "Marli Berger Dambrosio")
    assert exc.value.sugestoes  # tem ao menos uma sugestão


def test_pasta_ambigua_raiz_e_estado():
    service = _mock_service_drive(
        {
            "1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN": [
                {
                    "id": "raiz-id",
                    "name": "JOAO DA SILVA",
                    "mimeType": "application/vnd.google-apps.folder",
                },
                {
                    "id": "rs-id",
                    "name": "10. RIO GRANDE DO SUL",
                    "mimeType": "application/vnd.google-apps.folder",
                },
            ],
            "rs-id": [
                {
                    "id": "estado-id",
                    "name": "JOAO DA SILVA",
                    "mimeType": "application/vnd.google-apps.folder",
                },
            ],
        }
    )
    with pytest.raises(PastaAmbigua) as exc:
        localizar_pasta_cliente(service, "Joao da Silva")
    assert len(exc.value.paths) == 2


# ─── localizar_contrato ─────────────────────────────────────────────────────


def test_localizar_contrato_unico():
    service = _mock_service_drive(
        {
            "pasta-x": [
                {
                    "id": "doc-1",
                    "name": "01 Procuração.pdf",
                    "mimeType": "application/pdf",
                },
                {
                    "id": "doc-2",
                    "name": "09 Contrato Crefaz.pdf",
                    "mimeType": "application/pdf",
                },
                {
                    "id": "doc-3",
                    "name": "Contrato Honorários.pdf",
                    "mimeType": "application/pdf",
                },
            ]
        }
    )
    contrato = localizar_contrato(service, "pasta-x")
    assert contrato.id == "doc-2"


def test_localizar_contrato_ambiguo():
    service = _mock_service_drive(
        {
            "pasta-x": [
                {
                    "id": "doc-a",
                    "name": "09 Contrato Crefaz.pdf",
                    "mimeType": "application/pdf",
                },
                {
                    "id": "doc-b",
                    "name": "Contrato Crefaz antigo.pdf",
                    "mimeType": "application/pdf",
                },
            ]
        }
    )
    with pytest.raises(ContratoAmbiguo) as exc:
        localizar_contrato(service, "pasta-x")
    assert len(exc.value.candidatos) == 2


def test_localizar_contrato_ambiguo_resolvido_com_forcar_nome():
    service = _mock_service_drive(
        {
            "pasta-x": [
                {
                    "id": "doc-a",
                    "name": "09 Contrato Crefaz.pdf",
                    "mimeType": "application/pdf",
                },
                {
                    "id": "doc-b",
                    "name": "Contrato Crefaz antigo.pdf",
                    "mimeType": "application/pdf",
                },
            ]
        }
    )
    contrato = localizar_contrato(service, "pasta-x", forcar_nome="09 Contrato Crefaz.pdf")
    assert contrato.id == "doc-a"


def test_localizar_contrato_ausente():
    service = _mock_service_drive(
        {
            "pasta-x": [
                {
                    "id": "doc-1",
                    "name": "01 Procuração.pdf",
                    "mimeType": "application/pdf",
                },
            ]
        }
    )
    with pytest.raises(ContratoNaoEncontrado):
        localizar_contrato(service, "pasta-x")
