"""Nomes de saída v0.9.0 — sem numeração/acento; variante quitado com sufixo."""

from __future__ import annotations

import pytest

from calculadora_crefaz.capturas import nome_pdf
from calculadora_crefaz.config import (
    REGEX_BACEN_PASTA_CLIENTE,
    nome_series_temporais,
    nome_xlsx_saida,
    numero_prefixo,
)


def test_nome_xlsx_ativo():
    assert nome_xlsx_saida(quitado=False) == "Calculo.xlsx"


def test_nome_xlsx_quitado():
    assert nome_xlsx_saida(quitado=True) == "Calculo quitado.xlsx"


# ── Fallback legado: sem sequência, nome sem número (comportamento v0.9.0) ──


def test_nome_pdf_ativo_sem_seq():
    assert nome_pdf(quitado=False) == "Calculo.pdf"


def test_nome_pdf_quitado_sem_seq():
    assert nome_pdf(quitado=True) == "Calculo quitado.pdf"


# ── v0.9.8: sequência consecutiva derivada do prefixo do contrato ──


@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("09 Contrato Crefaz FULANO DE TAL.pdf", 9),
        ("10 Contrato Crefaz.pdf", 10),
        ("07 Contrato Crefaz MARIA.pdf", 7),
        ("Contrato Crefaz.pdf", None),          # sem prefixo → fallback
        ("Contrato Crefaz FULANO.pdf", None),
        ("contrato crefaz.pdf", None),
    ],
)
def test_numero_prefixo(nome, esperado):
    assert numero_prefixo(nome) == esperado


@pytest.mark.parametrize(
    "seq, series, calc_pdf, calc_quit",
    [
        # contrato 09 → séries 10 · cálculo 11
        (9, "10 Series Temporais.pdf", "11 Calculo.pdf", "11 Calculo quitado.pdf"),
        # contrato 10 → séries 11 · cálculo 12
        (10, "11 Series Temporais.pdf", "12 Calculo.pdf", "12 Calculo quitado.pdf"),
        # zero-padding preservado em números baixos
        (7, "08 Series Temporais.pdf", "09 Calculo.pdf", "09 Calculo quitado.pdf"),
    ],
)
def test_sequencia_consecutiva(seq, series, calc_pdf, calc_quit):
    assert nome_series_temporais(seq) == series
    assert nome_pdf(quitado=False, seq_contrato=seq) == calc_pdf
    assert nome_pdf(quitado=True, seq_contrato=seq) == calc_quit


def test_series_fallback_sem_seq():
    # contrato sem número → séries mantém o nome legado fixo
    assert nome_series_temporais(None) == "11 Series Temporais.pdf"


@pytest.mark.parametrize(
    "nome",
    [
        "10 Series Temporais.pdf",   # novo (contrato 09)
        "11 Series Temporais.pdf",   # legado / contrato 10
        "12 Séries Temporais.pdf",   # com acento
        "Series Temporais.pdf",      # sem prefixo
    ],
)
def test_bacen_detecta_qualquer_prefixo(nome):
    # a detecção de "BACEN já na pasta" tem de reconhecer o arquivo em qualquer
    # número de sequência (senão re-baixa e duplica em run subsequente).
    assert REGEX_BACEN_PASTA_CLIENTE.match(nome)
