"""Testes do log_writer."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from calculadora_crefaz.log_writer import (
    ArquivoGerado,
    DadosLog,
    _fmt_pct,
    _fmt_real,
    combinar_log_anterior,
    gerar_log,
)
from calculadora_crefaz.parser_contrato import DadosContrato
from calculadora_crefaz.planilha import DadosPlanilha


def test_fmt_real_milhar():
    assert _fmt_real(3500.00) == "3.500,00"


def test_fmt_real_simples():
    assert _fmt_real(104.99) == "104,99"


def test_fmt_real_zero():
    assert _fmt_real(0.00) == "0,00"


def test_fmt_real_milhao():
    assert _fmt_real(1234567.89) == "1.234.567,89"


def test_fmt_pct_taxa_decimal():
    assert _fmt_pct(0.1449) == "14,49%"


def test_fmt_pct_bacen_pequena():
    assert _fmt_pct(0.0647) == "6,47%"


def _dados_log_marli() -> DadosLog:
    contrato = DadosContrato(
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
    pl = DadosPlanilha(
        contrato=contrato,
        taxa_bacen=0.0647,
        parcelas_pagas=3,
        data_calculo=date(2026, 4, 28),
    )
    return DadosLog(
        dados_planilha=pl,
        usuario_email="bruna@roseportaladvocacia.com.br",
        pasta_drive_path="EMPRESTIMO DE ENERGIA/10. RIO GRANDE DO SUL/MARLI...",
        contrato_arquivo="09 Contrato Crefaz.pdf",
        bacen_origem="pasta_cliente",
        bacen_mes=2,
        bacen_ano=2026,
        aba_template="PRICE 24X",
        arquivos_gerados=[
            ArquivoGerado("10 Cálculo MARLI SUELI BERGER DAMBROSIO.xlsx", "novo"),
            ArquivoGerado("11 Series Temporais.pdf", "mantido"),
            ArquivoGerado("12 Log.txt", "append"),
        ],
        timestamp=datetime(2026, 4, 28, 14, 32, 11),
    )


def test_log_marli_contem_campos_chave():
    txt = gerar_log(_dados_log_marli())
    assert "v0.5.1" in txt
    assert "2026-04-28 14:32:11 BRT" in txt
    assert "bruna@roseportaladvocacia.com.br" in txt
    assert "Marli Sueli Berger Dambrosio" in txt
    assert "Número da cédula: 4095068" in txt
    assert "Prazo: 18 parcelas" in txt
    assert "29/12/2025" in txt
    assert "02/02/2026" in txt
    assert "R$ 3.500,00" in txt
    assert "R$ 104,99" in txt
    assert "14,49%" in txt
    assert "6,47%" in txt
    assert "Parcelas pagas até hoje: 3" in txt
    assert "PRICE 24X" in txt
    assert "pasta_cliente" in txt
    assert "STATUS: SUCESSO" in txt
    # Lista de arquivos gerados
    assert "10 Cálculo MARLI SUELI BERGER DAMBROSIO.xlsx (novo)" in txt
    assert "11 Series Temporais.pdf (mantido)" in txt
    assert "12 Log.txt (append)" in txt


def test_log_excesso_calculado_corretamente():
    txt = gerar_log(_dados_log_marli())
    # Excesso: 14,49 / 6,47 - 1 = 1.2395 → +124%
    assert "+124%" in txt


def test_log_origem_serie_do_bacen():
    log = _dados_log_marli()
    log.bacen_origem = "serie_do_bacen"
    txt = gerar_log(log)
    assert "serie_do_bacen" in txt
    assert "copiado" in txt


def test_log_status_customizado():
    log = _dados_log_marli()
    log.status = "BLOQUEIO_DEDUP"
    txt = gerar_log(log)
    assert "STATUS: BLOQUEIO_DEDUP" in txt


def test_combinar_log_anterior_somente_novo():
    assert combinar_log_anterior(None, "bloco") == "bloco"
    assert combinar_log_anterior("", "bloco") == "bloco"
    assert combinar_log_anterior("   \n", "bloco") == "bloco"


def test_combinar_log_anterior_append_separador():
    out = combinar_log_anterior("histórico", "novo")
    assert out.startswith("histórico")
    assert "novo" in out
    assert out.count("=") >= 60
    assert "histórico" in out and "novo" in out
