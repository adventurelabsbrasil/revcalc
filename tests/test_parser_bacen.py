"""Testes do parser BACEN."""

from __future__ import annotations

from pathlib import Path

import pytest

from calculadora_crefaz.exceptions import BacenParseError
from calculadora_crefaz.parser_bacen import _parse_taxa, extrair_taxa_mes, parsear_bacen

FIXTURES = Path(__file__).parent / "fixtures"


# ─── Helpers ────────────────────────────────────────────────────────────────


def test_parse_taxa_decimal():
    assert _parse_taxa("5,58") == pytest.approx(0.0558)


def test_parse_taxa_pequena():
    assert _parse_taxa("0,99") == pytest.approx(0.0099)


def test_parse_taxa_grande():
    assert _parse_taxa("12,34") == pytest.approx(0.1234)


# ─── extrair_taxa_mes ───────────────────────────────────────────────────────


# Texto sintético baseado no formato real do PDF BACEN
TEXTO_BACEN_FEV_2026 = """\
Sistema Gerenciador de Séries Temporais - SGS - Banco Central do Brasil
Código 25464 - Taxa média de juros das operações de crédito - PJ

Período        Taxa anual    Taxa mensal
jan/2026       95,12         5,73
fev/2026       80,15         6,47
mar/2026       82,33         5,12
"""


def test_extrair_fev_2026():
    assert extrair_taxa_mes(TEXTO_BACEN_FEV_2026, 2, 2026) == pytest.approx(0.0647)


def test_extrair_jan_2026():
    assert extrair_taxa_mes(TEXTO_BACEN_FEV_2026, 1, 2026) == pytest.approx(0.0573)


def test_extrair_mes_ausente_lanca_erro():
    with pytest.raises(BacenParseError) as exc:
        extrair_taxa_mes(TEXTO_BACEN_FEV_2026, 12, 2026)
    assert exc.value.mes == 12
    assert exc.value.ano == 2026


def test_extrair_ano_errado_lanca_erro():
    with pytest.raises(BacenParseError):
        extrair_taxa_mes(TEXTO_BACEN_FEV_2026, 2, 2025)


def test_case_insensitive_mes():
    texto = "FEV/2026   80,15   6,47\n"
    assert extrair_taxa_mes(texto, 2, 2026) == pytest.approx(0.0647)


def test_pega_mensal_nao_anual():
    """Confirma que retornamos o segundo número (mensal), não o primeiro (anual)."""
    texto = "fev/2026   80,15   6,47\n"
    taxa = extrair_taxa_mes(texto, 2, 2026)
    assert taxa == pytest.approx(0.0647)
    assert taxa != pytest.approx(0.8015)


def test_todos_os_meses():
    """Garante que todas as abreviações em pt-BR são reconhecidas."""
    texto_todos = """\
jan/2025   10,00   1,00
fev/2025   10,00   2,00
mar/2025   10,00   3,00
abr/2025   10,00   4,00
mai/2025   10,00   5,00
jun/2025   10,00   6,00
jul/2025   10,00   7,00
ago/2025   10,00   8,00
set/2025   10,00   9,00
out/2025   10,00   10,00
nov/2025   10,00   11,00
dez/2025   10,00   12,00
"""
    for mes_idx in range(1, 13):
        taxa = extrair_taxa_mes(texto_todos, mes_idx, 2025)
        assert taxa == pytest.approx(mes_idx / 100.0), f"Falhou para mês {mes_idx}"


# ─── E2E com PDFs reais ─────────────────────────────────────────────────────


@pytest.mark.skipif(
    not (FIXTURES / "02-2026.pdf").exists(),
    reason="Fixture BACEN 02-2026 não disponível",
)
def test_e2e_bacen_fev_2026():
    taxa = parsear_bacen(FIXTURES / "02-2026.pdf", 2, 2026)
    # valor de referência do spec: 6,47% → 0.0647
    assert taxa == pytest.approx(0.0647, abs=1e-4)


@pytest.mark.skipif(
    not (FIXTURES / "10-2025.pdf").exists(),
    reason="Fixture BACEN 10-2025 não disponível",
)
def test_e2e_bacen_out_2025():
    taxa = parsear_bacen(FIXTURES / "10-2025.pdf", 10, 2025)
    # valor exato pode variar — apenas validar que retorna decimal entre 0 e 1
    assert 0 < taxa < 1
