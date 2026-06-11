"""Lógica de cálculo: parcelas pagas + decisão de aba do template."""

from __future__ import annotations

from datetime import date

from .config import PRAZO_MAXIMO, PRAZO_MINIMO, aba_para_prazo
from .exceptions import PrazoForaDoTemplate


def meses_entre(d_atual: date, d_origem: date) -> int:
    """Conta meses cheios completados entre d_origem e d_atual.

    Spec do projeto:
        meses_entre(d_atual, d_origem) =
            (d_atual.year - d_origem.year) * 12
            + (d_atual.month - d_origem.month)
            + (1 if d_atual.day >= d_origem.day else 0)

    A última parcela paga é contada se já passou o dia do mês de origem
    no mês corrente.
    """
    return (
        (d_atual.year - d_origem.year) * 12
        + (d_atual.month - d_origem.month)
        + (1 if d_atual.day >= d_origem.day else 0)
    )


def parcelas_pagas(
    primeiro_vencimento: date,
    prazo: int,
    hoje: date | None = None,
) -> int:
    """Quantas parcelas já venceram entre o 1º vencimento e hoje.

    Bounded: 0 ≤ resultado ≤ prazo.
    """
    if hoje is None:
        hoje = date.today()
    return max(0, min(prazo, meses_entre(hoje, primeiro_vencimento)))


def decidir_aba(prazo: int) -> str:
    """Escolhe a aba do template a partir do prazo.

    v0.6.0: Crefaz só opera contratos de 1 a 24 parcelas → uma única aba CÁLCULO.
    Lança PrazoForaDoTemplate se o prazo cair fora de [PRAZO_MINIMO, PRAZO_MAXIMO].
    """
    if prazo < PRAZO_MINIMO or prazo > PRAZO_MAXIMO:
        raise PrazoForaDoTemplate(prazo)
    return aba_para_prazo(prazo)
