"""Recorte vertical da imag.01 (`_escolher_y_fim`).

Modela os DOIS layouts reais do contrato Crefaz (ativo × quitado) como `line_rows`
e garante que a âncora inclusiva ("C.E.T. TAXA ANUAL") fecha o bloco EMPRÉSTIMO
CONCEDIDO corretamente nos dois — fechando o bug em que o contrato ativo varava
para a seção "III. CUSTO EFETIVO TOTAL" (v0.9.6).
"""

from __future__ import annotations

import re

from calculadora_crefaz.capturas import _escolher_y_fim
from calculadora_crefaz.config import CAPTURA_IMG01_CONTRATO as C

INCL = re.compile(C["marcador_fim_inclusivo_regex"], re.IGNORECASE)
EXCL = re.compile(C["marcador_fim_regex"], re.IGNORECASE)


def _linha(top: float, texto: str):
    # (bucket, texto, tops, bottoms) — altura de linha ~10pt.
    return (top, texto, [top], [top + 10.0])


# Layout ATIVO: EMPRÉSTIMO (326) → C.E.T. ANUAL (434) → III.CUSTO EFETIVO TOTAL
# (468). "DA LIBERAÇÃO" só aparece ACIMA (174), como texto corrido.
ATIVO = [
    _linha(174, "quantia correspondente ao Valor da Liberação do Crédito..."),
    _linha(326, "II.EMPRÉSTIMO CONCEDIDO:"),
    _linha(434, "C.E.T. TAXA MENSAL: 13,07% C.E.T. TAXA ANUAL: 336,68%"),
    _linha(468, "III.CUSTO EFETIVO TOTAL"),
]

# Layout QUITADO: EMPRÉSTIMO (316) → "C.E.T (CUSTO EFETIVO TOTAL)" cabeçalho de
# coluna DENTRO do bloco (380) → C.E.T. ANUAL (392) → IV.DA LIBERAÇÃO (418).
QUITADO = [
    _linha(316, "III.EMPRÉSTIMO CONCEDIDO:"),
    _linha(380, "C.E.T (CUSTO EFETIVO TOTAL)¹ Informações dos valores componentes"),
    _linha(392, "C.E.T. MENSAL: 12,65% C.E.T. TAXA ANUAL: 317,44%"),
    _linha(418, "IV.DA LIBERAÇÃO DO CRÉDITO:"),
]


def test_ativo_inclui_cet_anual_e_nao_vara_para_custo_efetivo_total():
    y_fim = _escolher_y_fim(ATIVO, y_inicio=316.0, fim_incl_pattern=INCL, fim_pattern=EXCL)
    assert 444.0 < y_fim < 468.0  # abaixo do C.E.T. ANUAL (444), acima do III (468)


def test_quitado_para_no_cet_anual_e_nao_corta_no_custo_efetivo_total_do_meio():
    # A âncora C.E.T. ANUAL (392) vence o "CUSTO EFETIVO TOTAL" de coluna (380)
    # e não vara para o IV.DA LIBERAÇÃO (418).
    y_fim = _escolher_y_fim(QUITADO, y_inicio=306.0, fim_incl_pattern=INCL, fim_pattern=EXCL)
    assert 402.0 < y_fim < 418.0


def test_ancora_acima_do_inicio_e_ignorada():
    # Se a única linha "DA LIBERAÇÃO" estiver acima do início (ativo), o fallback
    # exclusivo não acha nada abaixo → None (cai no fallback de altura no caller).
    so_acima = [_linha(174, "...DA LIBERAÇÃO DO CRÉDITO..."), _linha(326, "II.EMPRÉSTIMO CONCEDIDO:")]
    y_fim = _escolher_y_fim(so_acima, y_inicio=316.0, fim_incl_pattern=None, fim_pattern=EXCL)
    assert y_fim is None


def test_fallback_exclusivo_corta_acima_da_secao_seguinte():
    # Sem âncora inclusiva, usa o marcador exclusivo (corta ACIMA dele).
    y_fim = _escolher_y_fim(QUITADO, y_inicio=306.0, fim_incl_pattern=None, fim_pattern=EXCL)
    assert 392.0 < y_fim < 418.0  # acima do IV.DA LIBERAÇÃO (418)
