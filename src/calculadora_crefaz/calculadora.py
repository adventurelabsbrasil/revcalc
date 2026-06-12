"""Lógica de cálculo: parcelas pagas + decisão de aba do template."""

from __future__ import annotations

from datetime import date

from .config import (
    PRAZO_MAXIMO,
    PRAZO_MAXIMO_QUITADO,
    PRAZO_MINIMO,
    aba_para_prazo,
    aba_para_prazo_quitado,
)
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


def is_quitado(parcelas_pagas: int, prazo: int) -> bool:
    """Contrato quitado = todas as parcelas já venceram (0 a vencer).

    v0.9.0: detecção automática pelos dados. `parcelas_pagas` é limitado a `prazo`
    em :func:`parcelas_pagas`, então `>= prazo` ⇔ "parcelas a vencer == 0".
    """
    return parcelas_pagas >= prazo


def decidir_aba(prazo: int, quitado: bool = False) -> str:
    """Escolhe a aba do template a partir do prazo (e do status quitado).

    - ATIVO (v0.6.0): Crefaz opera 1–24 parcelas → aba única CÁLCULO.
    - QUITADO (v0.9.0): contratos históricos até 60 → abas PRICE 24X/36x/48x/60x.

    Lança PrazoForaDoTemplate se o prazo cair fora da faixa do fluxo escolhido.
    """
    if quitado:
        if prazo < PRAZO_MINIMO or prazo > PRAZO_MAXIMO_QUITADO:
            raise PrazoForaDoTemplate(prazo)
        return aba_para_prazo_quitado(prazo)
    if prazo < PRAZO_MINIMO or prazo > PRAZO_MAXIMO:
        raise PrazoForaDoTemplate(prazo)
    return aba_para_prazo(prazo)
