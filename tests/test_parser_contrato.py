"""Testes do parser de contrato Crefaz.

Os testes sintéticos validam regex sem depender de PDFs reais.
Testes E2E com PDFs reais ficam em fixtures/ (gitignored) e são opcionais.
"""

from __future__ import annotations

import warnings
from datetime import date
from pathlib import Path

import pytest

from calculadora_crefaz.exceptions import ContratoParseError, ValidacaoContratoWarning
from calculadora_crefaz.parser_contrato import (
    _parse_data,
    _parse_pct,
    _parse_valor_brl,
    extrair_item_ii,
    parsear_contrato,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ─── Helpers ────────────────────────────────────────────────────────────────


class TestHelpers:
    def test_parse_valor_brl_milhar(self):
        assert _parse_valor_brl("3.500,00") == 3500.00

    def test_parse_valor_brl_simples(self):
        assert _parse_valor_brl("104,99") == 104.99

    def test_parse_valor_brl_zero(self):
        assert _parse_valor_brl("0,00") == 0.00

    def test_parse_valor_brl_milhao(self):
        assert _parse_valor_brl("1.234.567,89") == 1234567.89

    def test_parse_pct_decimal(self):
        assert _parse_pct("18,77") == pytest.approx(0.1877)

    def test_parse_pct_inteiro(self):
        assert _parse_pct("14") == pytest.approx(0.14)

    def test_parse_data(self):
        assert _parse_data("29/12/2025") == date(2025, 12, 29)


# ─── Recorte do Item II ─────────────────────────────────────────────────────


class TestExtrairItemII:
    def test_recorte_basico(self):
        texto = (
            "I.EMITENTE\nNome: Joao\n"
            "II.EMPRÉSTIMO CONCEDIDO:\n"
            "Prazo: 18\n"
            "III.CUSTO EFETIVO TOTAL\nblabla"
        )
        out = extrair_item_ii(texto)
        assert "Prazo: 18" in out
        assert "blabla" not in out

    def test_sem_marcador_inicial(self):
        with pytest.raises(ContratoParseError) as exc:
            extrair_item_ii("texto sem marcador")
        assert exc.value.campo == "item_ii"

    def test_sem_marcador_final_pega_ate_fim(self):
        texto = "II.EMPRÉSTIMO CONCEDIDO:\nPrazo: 18\nfim"
        out = extrair_item_ii(texto)
        assert "Prazo: 18" in out
        assert "fim" in out


# ─── Parser completo com texto sintético ────────────────────────────────────


CONTRATO_SINTETICO_MARLI = """\
CÉDULA DE CRÉDITO BANCÁRIO N.º 4095068

I.EMITENTE
Nome: Marli Sueli Berger Dambrosio CPF/MF: 123.456.789-00

II.EMPRÉSTIMO CONCEDIDO:
Data de Emissão: 29/12/2025
Prazo: 18
1º Vencimento: 02/02/2026
Último Vencimento: 02/07/2027
Valor Nominal: R$ 3.500,00
Valor do Empréstimo: R$ 3.604,99
Valor Total Contratado: R$ 10.539,54
Valor da Prestação: R$ 585,53
Taxa de Juros Mensal: 14,49%
Taxa de Juros Anual: 393,73%
Tributos/IOF: R$ 104,99
Tarifas: R$ 0,00

III.CUSTO EFETIVO TOTAL
"""


CONTRATO_SINTETICO_ADRIANO = """\
CÉDULA DE CRÉDITO BANCÁRIO N.º 3867296

I.EMITENTE
Nome: Adriano Luis Calistro Lourenco CPF/MF: 987.654.321-00

II.EMPRÉSTIMO CONCEDIDO:
Data de Emissão: 22/09/2025
Prazo: 12
1º Vencimento: 27/10/2025
Último Vencimento: 27/09/2026
Valor Nominal: R$ 1.000,00
Valor do Empréstimo: R$ 1.025,10
Valor Total Contratado: R$ 2.721,48
Valor da Prestação: R$ 226,79
Taxa de Juros Mensal: 18,77%
Taxa de Juros Anual: 692,89%
Tributos/IOF: R$ 25,10
Tarifas: R$ 0,00

III.CUSTO EFETIVO TOTAL
"""


class TestParsearContratoSintetico:
    """Mocka pdfplumber para retornar texto controlado."""

    def _patch_pdf(self, monkeypatch, texto: str):
        from calculadora_crefaz import parser_contrato

        monkeypatch.setattr(parser_contrato, "_extrair_texto_pdf", lambda _: texto)

    def test_marli_completo(self, monkeypatch):
        self._patch_pdf(monkeypatch, CONTRATO_SINTETICO_MARLI)
        d = parsear_contrato(Path("fake.pdf"))

        assert d.numero_cedula == "4095068"
        assert d.nome_emitente == "Marli Sueli Berger Dambrosio"
        assert d.data_emissao == date(2025, 12, 29)
        assert d.primeiro_vencimento == date(2026, 2, 2)
        assert d.ultimo_vencimento == date(2027, 7, 2)
        assert d.valor_nominal == 3500.00
        assert d.valor_emprestimo == 3604.99
        assert d.valor_prestacao == 585.53
        assert d.prazo == 18
        assert d.taxa_mensal == pytest.approx(0.1449)
        assert d.tributos_iof == 104.99
        assert d.tarifas == 0.00

    def test_adriano_completo(self, monkeypatch):
        self._patch_pdf(monkeypatch, CONTRATO_SINTETICO_ADRIANO)
        d = parsear_contrato(Path("fake.pdf"))

        assert d.numero_cedula == "3867296"
        assert d.nome_emitente == "Adriano Luis Calistro Lourenco"
        assert d.data_emissao == date(2025, 9, 22)
        assert d.primeiro_vencimento == date(2025, 10, 27)
        assert d.valor_nominal == 1000.00
        assert d.taxa_mensal == pytest.approx(0.1877)
        assert d.prazo == 12
        assert d.tributos_iof == 25.10

    def test_validacao_passa_quando_soma_bate(self, monkeypatch):
        self._patch_pdf(monkeypatch, CONTRATO_SINTETICO_ADRIANO)
        # 1000 + 25.10 + 0 = 1025.10 == valor_emprestimo
        with warnings.catch_warnings():
            warnings.simplefilter("error", ValidacaoContratoWarning)
            parsear_contrato(Path("fake.pdf"))  # não deve lançar warning

    def test_validacao_warning_quando_soma_nao_bate(self, monkeypatch):
        contrato_quebrado = CONTRATO_SINTETICO_ADRIANO.replace(
            "Valor do Empréstimo: R$ 1.025,10",
            "Valor do Empréstimo: R$ 9.999,99",
        )
        self._patch_pdf(monkeypatch, contrato_quebrado)
        with pytest.warns(ValidacaoContratoWarning):
            parsear_contrato(Path("fake.pdf"))

    def test_falta_data_emissao_lanca_erro(self, monkeypatch):
        contrato_quebrado = CONTRATO_SINTETICO_ADRIANO.replace(
            "Data de Emissão: 22/09/2025\n", ""
        )
        self._patch_pdf(monkeypatch, contrato_quebrado)
        with pytest.raises(ContratoParseError) as exc:
            parsear_contrato(Path("fake.pdf"))
        assert exc.value.campo == "data_emissao"

    def test_falta_cedula_lanca_erro(self, monkeypatch):
        contrato_quebrado = CONTRATO_SINTETICO_ADRIANO.replace(
            "CÉDULA DE CRÉDITO BANCÁRIO N.º 3867296", "OUTRA COISA"
        )
        self._patch_pdf(monkeypatch, contrato_quebrado)
        with pytest.raises(ContratoParseError) as exc:
            parsear_contrato(Path("fake.pdf"))
        assert exc.value.campo == "numero_cedula"

    def test_taxa_mensal_5a_linha_nao_anual(self, monkeypatch):
        """Confirma que extraímos a Mensal e não a Anual (são parecidas no formato)."""
        self._patch_pdf(monkeypatch, CONTRATO_SINTETICO_MARLI)
        d = parsear_contrato(Path("fake.pdf"))
        # Mensal é 14,49%; Anual é 393,73%
        assert d.taxa_mensal == pytest.approx(0.1449)
        assert d.taxa_anual == pytest.approx(3.9373)
        assert d.taxa_mensal != d.taxa_anual

    def test_taxa_com_marcador_nota_superscript(self, monkeypatch):
        """Contratos novos (2026-08): 'Taxa de Juros¹ Mensal:' com superscript.

        Feedback do cliente (2026-08): o ¹ entre 'Juros' e 'Mensal' quebrava o
        \\s+ antigo e a extração falhava. O separador tolerante deve casar.
        """
        contrato = CONTRATO_SINTETICO_MARLI.replace(
            "Taxa de Juros Mensal: 14,49%", "Taxa de Juros¹ Mensal: 14,49%"
        ).replace(
            "Taxa de Juros Anual: 393,73%", "Taxa de Juros² Anual: 393,73%"
        )
        self._patch_pdf(monkeypatch, contrato)
        d = parsear_contrato(Path("fake.pdf"))
        assert d.taxa_mensal == pytest.approx(0.1449)
        assert d.taxa_anual == pytest.approx(3.9373)

    def test_taxa_com_marcador_nota_digito_nfkc(self, monkeypatch):
        """Variante em que o extrator normaliza o superscript p/ dígito ASCII."""
        contrato = CONTRATO_SINTETICO_MARLI.replace(
            "Taxa de Juros Mensal: 14,49%", "Taxa de Juros1 Mensal: 14,49%"
        ).replace(
            "Taxa de Juros Anual: 393,73%", "Taxa de Juros2 Anual: 393,73%"
        )
        self._patch_pdf(monkeypatch, contrato)
        d = parsear_contrato(Path("fake.pdf"))
        assert d.taxa_mensal == pytest.approx(0.1449)
        assert d.taxa_anual == pytest.approx(3.9373)


# ─── Testes E2E com PDFs reais (skip se ausentes) ───────────────────────────


@pytest.mark.skipif(
    not (FIXTURES / "adriano.pdf").exists(),
    reason="Fixture do Adriano não disponível",
)
def test_e2e_adriano():
    from datetime import date

    pdf = FIXTURES / "adriano.pdf"
    d = parsear_contrato(pdf)
    assert d.numero_cedula == "3867296"
    assert d.prazo == 12
    assert d.taxa_mensal == pytest.approx(0.1877)
    assert d.valor_nominal == 1000.00
    assert d.tributos_iof == 25.10
    assert d.tarifas == 0.00
    assert d.valor_prestacao == 226.79
    assert d.data_emissao == date(2025, 9, 22)
    assert d.primeiro_vencimento == date(2025, 10, 27)


@pytest.mark.skipif(
    not (FIXTURES / "marli.pdf").exists(),
    reason="Fixture da Marli não disponível",
)
def test_e2e_marli():
    from datetime import date

    pdf = FIXTURES / "marli.pdf"
    d = parsear_contrato(pdf)
    assert d.numero_cedula == "4095068"
    assert d.prazo == 18
    assert d.taxa_mensal == pytest.approx(0.1449)
    assert d.valor_nominal == 3500.00
    assert d.tributos_iof == 104.99
    assert d.tarifas == 0.00
    assert d.valor_prestacao == 585.53
    assert d.data_emissao == date(2025, 12, 29)
    assert d.primeiro_vencimento == date(2026, 2, 2)
