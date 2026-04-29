"""Extrai a taxa mensal do campo 25464 (BACEN) para o mês/ano alvo do PDF."""

from __future__ import annotations

from pathlib import Path

from .config import MESES_PT, REGEX_LINHA_BACEN
from .exceptions import BacenParseError


def _extrair_texto_pdf(pdf: Path | bytes) -> str:
    import pdfplumber

    if isinstance(pdf, (bytes, bytearray)):
        import io

        fh = io.BytesIO(pdf)
        with pdfplumber.open(fh) as p:
            return "\n".join(pg.extract_text() or "" for pg in p.pages)
    with pdfplumber.open(pdf) as p:
        return "\n".join(pg.extract_text() or "" for pg in p.pages)


def _parse_taxa(s: str) -> float:
    """Converte '5,58' → 0.0558 (taxa mensal em decimal)."""
    return float(s.replace(",", ".")) / 100.0


def extrair_taxa_mes(texto: str, mes: int, ano: int) -> float:
    """Procura a linha do mês/ano alvo e devolve a taxa mensal em decimal.

    Linhas do PDF BACEN têm o formato:
        {mes_pt}/{ano}    {valor_anual}    {valor_mensal}

    Retornamos sempre o valor mensal (grupo 4 do regex).
    """
    for m in REGEX_LINHA_BACEN.finditer(texto):
        mes_pt, ano_str, _anual, mensal = m.groups()
        mes_num = MESES_PT[mes_pt.lower()]
        if mes_num == mes and int(ano_str) == ano:
            return _parse_taxa(mensal)
    raise BacenParseError(
        mes,
        ano,
        f"Nenhuma linha casou {mes:02d}/{ano} no texto extraído.",
    )


def parsear_bacen(pdf: Path | bytes, mes: int, ano: int) -> float:
    """Pipeline completo: PDF → taxa mensal decimal para o mês/ano alvo."""
    texto = _extrair_texto_pdf(pdf)
    return extrair_taxa_mes(texto, mes, ano)
