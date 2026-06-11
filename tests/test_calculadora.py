"""Testes da lógica de cálculo (parcelas pagas + decisão de aba)."""

from __future__ import annotations

from datetime import date

import pytest

from calculadora_crefaz.calculadora import decidir_aba, meses_entre, parcelas_pagas
from calculadora_crefaz.exceptions import PrazoForaDoTemplate


# ─── meses_entre ────────────────────────────────────────────────────────────


class TestMesesEntre:
    """A função conta parcelas vencidas: a primeira parcela vence em d_origem
    e cada mês subsequente atinge um novo aniversário do dia de origem.

    Fórmula do spec:
        (year_diff * 12) + month_diff + (1 if d_atual.day >= d_origem.day else 0)
    """

    def test_mesma_data_conta_parcela_do_dia(self):
        # 02/02 → 02/02: a parcela do dia já venceu = 1
        d = date(2026, 2, 2)
        assert meses_entre(d, d) == 1

    def test_mesmo_dia_proximo_mes(self):
        # 02/02 → 02/03: 2 parcelas vencidas (02/02 e 02/03)
        assert meses_entre(date(2026, 3, 2), date(2026, 2, 2)) == 2

    def test_um_dia_antes_proximo_mes(self):
        # 02/02 → 01/03: só a parcela de 02/02 venceu = 1
        assert meses_entre(date(2026, 3, 1), date(2026, 2, 2)) == 1

    def test_um_dia_depois_proximo_mes(self):
        # 02/02 → 03/03: 02/02 e 02/03 já venceram = 2
        assert meses_entre(date(2026, 3, 3), date(2026, 2, 2)) == 2

    def test_um_dia_antes_do_primeiro_vencimento(self):
        # 01/02 com origem 02/02: nada venceu ainda
        assert meses_entre(date(2026, 2, 1), date(2026, 2, 2)) == 0

    def test_atravessando_ano(self):
        # 29/12/2025 → 02/02/2026:
        # year_diff = 1 → +12
        # month_diff = 2 - 12 = -10
        # day: 2 >= 29? não → 0
        # total = 2
        assert meses_entre(date(2026, 2, 2), date(2025, 12, 29)) == 2

    def test_atravessando_ano_dia_alcancado(self):
        # 29/12/2025 → 30/01/2026:
        # 12 + (1-12) + (1 if 30>=29 else 0) = 12 - 11 + 1 = 2
        assert meses_entre(date(2026, 1, 30), date(2025, 12, 29)) == 2

    def test_data_origem_no_futuro_pode_ser_negativo(self):
        # Spec não trata — apenas validamos que não estoura
        result = meses_entre(date(2026, 1, 1), date(2026, 6, 1))
        assert result < 0


# ─── parcelas_pagas ─────────────────────────────────────────────────────────


class TestParcelasPagas:
    def test_antes_do_primeiro_vencimento(self):
        # hoje 01/02/2026, 1º venc 02/02/2026 → 0 parcelas
        assert parcelas_pagas(
            primeiro_vencimento=date(2026, 2, 2),
            prazo=18,
            hoje=date(2026, 2, 1),
        ) == 0

    def test_no_primeiro_vencimento(self):
        assert parcelas_pagas(
            primeiro_vencimento=date(2026, 2, 2),
            prazo=18,
            hoje=date(2026, 2, 2),
        ) == 1

    def test_marli_3_parcelas(self):
        # 1º venc 02/02/2026, hoje 27/04/2026
        # meses_entre = (2026-2026)*12 + (4-2) + (1 if 27>=2 else 0) = 0+2+1 = 3
        assert parcelas_pagas(
            primeiro_vencimento=date(2026, 2, 2),
            prazo=18,
            hoje=date(2026, 4, 27),
        ) == 3

    def test_capped_pelo_prazo(self):
        # contrato vencido há tempo: já passou de 18 parcelas
        assert parcelas_pagas(
            primeiro_vencimento=date(2020, 1, 1),
            prazo=18,
            hoje=date(2026, 4, 27),
        ) == 18

    def test_floor_zero(self):
        # contrato no futuro
        assert parcelas_pagas(
            primeiro_vencimento=date(2030, 1, 1),
            prazo=18,
            hoje=date(2026, 4, 27),
        ) == 0


# ─── decidir_aba ────────────────────────────────────────────────────────────


class TestDecidirAba:
    # v0.6.0: Crefaz só opera contratos de até 24 parcelas → uma única aba "CÁLCULO".
    # As abas multi-prazo (PRICE 36x/48x/60x) foram removidas; prazo > 24 agora lança.
    def test_prazo_1_aba_calculo(self):
        assert decidir_aba(1) == "CÁLCULO"

    def test_prazo_18_aba_calculo(self):
        assert decidir_aba(18) == "CÁLCULO"

    def test_prazo_24_aba_calculo(self):
        assert decidir_aba(24) == "CÁLCULO"

    def test_prazo_25_lanca(self):
        # boundary: 1 acima do PRAZO_MAXIMO (24)
        with pytest.raises(PrazoForaDoTemplate) as exc:
            decidir_aba(25)
        assert exc.value.prazo == 25

    def test_prazo_61_lanca(self):
        with pytest.raises(PrazoForaDoTemplate) as exc:
            decidir_aba(61)
        assert exc.value.prazo == 61

    def test_prazo_zero_lanca(self):
        with pytest.raises(PrazoForaDoTemplate):
            decidir_aba(0)

    def test_prazo_negativo_lanca(self):
        with pytest.raises(PrazoForaDoTemplate):
            decidir_aba(-1)
