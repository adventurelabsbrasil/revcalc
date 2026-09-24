from datetime import date

from calculadora_crefaz.parser_contrato import DadosContrato
from calculadora_crefaz.pipeline import competencia_bacen


def _contrato() -> DadosContrato:
    return DadosContrato(
        numero_cedula="123",
        nome_emitente="Cliente Teste",
        data_emissao=date(2026, 6, 15),
        primeiro_vencimento=date(2026, 7, 15),
        ultimo_vencimento=date(2027, 6, 15),
        valor_nominal=1000.0,
        valor_emprestimo=1000.0,
        valor_total_contratado=1000.0,
        valor_prestacao=100.0,
        tributos_iof=0.0,
        tarifas=0.0,
        prazo=12,
        taxa_mensal=0.1,
        taxa_anual=2.0,
    )


def test_competencia_bacen_usa_data_de_emissao_e_nao_primeiro_vencimento():
    assert competencia_bacen(_contrato()) == (6, 2026)
