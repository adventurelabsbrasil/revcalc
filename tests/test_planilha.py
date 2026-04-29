"""Testes do preenchimento da planilha — usam o template real do projeto."""

from __future__ import annotations

from datetime import date
from io import BytesIO

import pytest
from openpyxl import load_workbook

from calculadora_crefaz.config import TEMPLATE_PATH
from calculadora_crefaz.parser_contrato import DadosContrato
from calculadora_crefaz.planilha import DadosPlanilha, gerar_xlsx


def _contrato_marli() -> DadosContrato:
    return DadosContrato(
        numero_cedula="4095068",
        nome_emitente="Marli Sueli Berger Dambrosio",
        data_emissao=date(2025, 12, 29),
        primeiro_vencimento=date(2026, 2, 2),
        ultimo_vencimento=date(2027, 7, 2),
        valor_nominal=3500.00,
        valor_emprestimo=3604.99,
        valor_total_contratado=10539.54,
        valor_prestacao=585.53,
        tributos_iof=104.99,
        tarifas=0.00,
        prazo=18,
        taxa_mensal=0.1449,
        taxa_anual=3.9373,
    )


def _contrato_adriano() -> DadosContrato:
    return DadosContrato(
        numero_cedula="3867296",
        nome_emitente="Adriano Luis Calistro Lourenco",
        data_emissao=date(2025, 9, 22),
        primeiro_vencimento=date(2025, 10, 27),
        ultimo_vencimento=date(2026, 9, 27),
        valor_nominal=1000.00,
        valor_emprestimo=1025.10,
        valor_total_contratado=2721.48,
        valor_prestacao=226.79,
        tributos_iof=25.10,
        tarifas=0.00,
        prazo=12,
        taxa_mensal=0.1877,
        taxa_anual=6.9289,
    )


def _carrega_xlsx(blob: bytes):
    return load_workbook(BytesIO(blob))


class TestGerarXlsx:
    def test_marli_18_parcelas_aba_24x(self):
        dados = DadosPlanilha(
            contrato=_contrato_marli(),
            taxa_bacen=0.0647,
            parcelas_pagas=3,
            data_calculo=date(2026, 4, 28),
        )
        blob = gerar_xlsx(dados)
        wb = _carrega_xlsx(blob)

        # Apenas 1 aba sobrevive
        assert wb.sheetnames == ["PRICE 24X"]
        ws = wb.active

        assert ws["C1"].value == (
            "CÁLCULOS DA OPERAÇÃO Nº 4095068 - "
            "CLIENTE: MARLI SUELI BERGER DAMBROSIO x BANCO CREFAZ"
        )
        # data_pactuacao em D3 — datetime
        assert ws["D3"].value.date() == date(2025, 12, 29)
        assert ws["I7"].value == 3500.00
        assert ws["I9"].value == 0.00  # tarifas
        assert ws["I13"].value == 104.99  # IOF
        assert ws["I15"].value == 18
        assert ws["I16"].value == 585.53
        assert ws["I17"].value == pytest.approx(0.1449)
        assert ws["AP15"].value == pytest.approx(0.0647)
        assert ws["BL8"].value == 3

        assert ws["D5"].value.date() == date(2026, 2, 2)
        assert ws["D5"].number_format == "dd/mm/yyyy"
        assert isinstance(ws["D132"].value, str) and ws["D132"].value.startswith("=IF(")

        # Page setup (v0.5.1 print-ready)
        assert ws.page_setup.orientation == "landscape"
        assert ws.page_setup.fitToWidth in (1, True)

    def test_adriano_12_parcelas_aba_24x(self):
        dados = DadosPlanilha(
            contrato=_contrato_adriano(),
            taxa_bacen=0.0573,  # exemplo
            parcelas_pagas=6,
            data_calculo=date(2026, 4, 28),
        )
        blob = gerar_xlsx(dados)
        wb = _carrega_xlsx(blob)

        assert wb.sheetnames == ["PRICE 24X"]
        ws = wb.active
        assert ws["C1"].value == (
            "CÁLCULOS DA OPERAÇÃO Nº 3867296 - "
            "CLIENTE: ADRIANO LUIS CALISTRO LOURENCO x BANCO CREFAZ"
        )
        assert ws["I7"].value == 1000.00
        assert ws["I13"].value == 25.10
        assert ws["I15"].value == 12
        assert ws["I16"].value == 226.79
        assert ws["I17"].value == pytest.approx(0.1877)
        assert ws["BL8"].value == 6

        assert ws["D5"].value.date() == date(2025, 10, 27)
        assert ws["D5"].number_format == "dd/mm/yyyy"

    def test_prazo_30_aba_36x_offset_aplicado(self):
        contrato = _contrato_marli()
        contrato.prazo = 30
        dados = DadosPlanilha(
            contrato=contrato,
            taxa_bacen=0.0647,
            parcelas_pagas=5,
            data_calculo=date(2026, 4, 28),
        )
        blob = gerar_xlsx(dados)
        wb = _carrega_xlsx(blob)

        assert wb.sheetnames == ["PRICE 36x"]
        ws = wb.active
        # Offset +1: titulo em C2, valor em I8, qtd parcelas em I16, taxa BACEN em AP16
        assert "MARLI" in ws["C2"].value
        assert ws["I8"].value == 3500.00
        assert ws["I16"].value == 30
        assert ws["I17"].value == 585.53  # valor da prestação
        assert ws["I18"].value == pytest.approx(0.1449)  # taxa pactuada
        assert ws["AP16"].value == pytest.approx(0.0647)  # BACEN com offset
        assert ws["BL9"].value == 5  # parcelas pagas com offset

        assert ws["D6"].value.date() == date(2026, 2, 2)
        assert ws["D6"].number_format == "dd/mm/yyyy"
        assert isinstance(ws["D133"].value, str) and ws["D133"].value.startswith("=IF(")
        assert ws.page_setup.fitToWidth in (1, True)

    def test_prazo_48_forca_landscape(self):
        contrato = _contrato_marli()
        contrato.prazo = 48
        dados = DadosPlanilha(
            contrato=contrato,
            taxa_bacen=0.0647,
            parcelas_pagas=10,
            data_calculo=date(2026, 4, 28),
        )
        blob = gerar_xlsx(dados)
        wb = _carrega_xlsx(blob)

        assert wb.sheetnames == ["PRICE 48x"]
        ws = wb.active
        assert ws.page_setup.orientation == "landscape"
        assert ws.page_setup.fitToWidth in (1, True)

    def test_prazo_60_aba_60x(self):
        contrato = _contrato_marli()
        contrato.prazo = 60
        dados = DadosPlanilha(
            contrato=contrato,
            taxa_bacen=0.0647,
            parcelas_pagas=15,
            data_calculo=date(2026, 4, 28),
        )
        blob = gerar_xlsx(dados)
        wb = _carrega_xlsx(blob)

        assert wb.sheetnames == ["PRICE 60x"]
        ws = wb.active
        assert ws["I16"].value == 60
        assert ws["BL9"].value == 15
        assert ws["D6"].number_format == "dd/mm/yyyy"
        assert ws.page_setup.fitToWidth in (1, True)

    def test_formulas_preservadas(self):
        """Garante que fórmulas críticas do template não são sobrescritas."""
        dados = DadosPlanilha(
            contrato=_contrato_marli(),
            taxa_bacen=0.0647,
            parcelas_pagas=3,
            data_calculo=date(2026, 4, 28),
        )
        blob = gerar_xlsx(dados)
        wb = _carrega_xlsx(blob)
        ws = wb.active

        # PRICE 24X — fórmulas-chave que NÃO devem ter sido tocadas
        assert ws["I14"].value == "=SUM(I7:Y13)"  # total
        assert ws["I18"].value == "=I15*I16"  # valor final
        assert ws["AP14"].value == "=SUM(AP7:AZ13)"
        assert ws["AP17"].value == "=I15*AP16"
        assert ws["BL10"].value == "=BL8*BL9"
