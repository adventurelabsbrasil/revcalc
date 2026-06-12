"""Nomes de saída v0.9.0 — sem numeração/acento; variante quitado com sufixo."""

from __future__ import annotations

from calculadora_crefaz.capturas import nome_pdf
from calculadora_crefaz.config import nome_xlsx_saida


def test_nome_xlsx_ativo():
    assert nome_xlsx_saida(quitado=False) == "Calculo.xlsx"


def test_nome_xlsx_quitado():
    assert nome_xlsx_saida(quitado=True) == "Calculo quitado.xlsx"


def test_nome_pdf_ativo():
    assert nome_pdf(quitado=False) == "Calculo.pdf"


def test_nome_pdf_quitado():
    assert nome_pdf(quitado=True) == "Calculo quitado.pdf"
