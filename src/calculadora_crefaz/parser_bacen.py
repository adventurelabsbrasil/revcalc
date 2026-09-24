"""Extrai a taxa mensal BACEN para o mês/ano alvo do PDF."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import (
    CODIGO_BACEN_ANUAL_ANTIGO,
    CODIGO_BACEN_ANUAL_NOV_2025,
    CODIGO_BACEN_MENSAL_ANTIGO,
    CODIGO_BACEN_MENSAL_NOV_2025,
    DATA_MUDANCA_SERIES_BACEN,
    MESES_PT,
    REGEX_LINHA_BACEN,
)
from .exceptions import BacenParseError


@dataclass(frozen=True)
class DadosTaxaBacen:
    taxa_mensal: float
    codigo_anual: int
    codigo_mensal: int


def codigos_esperados(mes: int, ano: int) -> tuple[int, int]:
    """Retorna ``(anual, mensal)`` conforme a competência da série."""
    if date(ano, mes, 1) >= DATA_MUDANCA_SERIES_BACEN:
        return CODIGO_BACEN_ANUAL_NOV_2025, CODIGO_BACEN_MENSAL_NOV_2025
    return CODIGO_BACEN_ANUAL_ANTIGO, CODIGO_BACEN_MENSAL_ANTIGO


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


def _extrair_codigos(texto: str) -> tuple[int, int]:
    """Extrai os códigos das colunas anual e mensal do cabeçalho SGS."""
    compacto = " ".join(texto.split())
    padroes = (
        r"(?:Data\s+)?mês/AAAA\s+(\d+)\s+%\s*a\.a\.\s+(\d+)\s+%\s*a\.m\.",
        r"(?:Data\s+)?mes/AAAA\s+(\d+)\s+%\s*a\.a\.\s+(\d+)\s+%\s*a\.m\.",
        # O PDF exportado pelo SGS também pode omitir as unidades no cabeçalho:
        # ``Data 20742 25464`` (ou ``Data 29974 29977``).
        r"Data\s+(\d+)\s+(\d+)",
    )
    for padrao in padroes:
        match = re.search(padrao, compacto, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    raise ValueError("Cabeçalho SGS sem códigos anuais/mensais reconhecíveis.")


def extrair_dados_mes(texto: str, mes: int, ano: int) -> DadosTaxaBacen:
    """Valida as séries SGS, procura a competência e devolve a taxa mensal."""
    esperado_anual, esperado_mensal = codigos_esperados(mes, ano)
    try:
        codigo_anual, codigo_mensal = _extrair_codigos(texto)
    except ValueError as exc:
        raise BacenParseError(mes, ano, str(exc)) from exc
    if (codigo_anual, codigo_mensal) != (esperado_anual, esperado_mensal):
        raise BacenParseError(
            mes,
            ano,
            f"Séries encontradas {codigo_anual}/{codigo_mensal}; "
            f"esperadas {esperado_anual}/{esperado_mensal} para esta competência.",
        )

    for m in REGEX_LINHA_BACEN.finditer(texto):
        mes_pt, ano_str, _anual, mensal = m.groups()
        mes_num = MESES_PT[mes_pt.lower()]
        if mes_num == mes and int(ano_str) == ano:
            return DadosTaxaBacen(
                taxa_mensal=_parse_taxa(mensal),
                codigo_anual=codigo_anual,
                codigo_mensal=codigo_mensal,
            )
    raise BacenParseError(
        mes,
        ano,
        f"Nenhuma linha casou {mes:02d}/{ano} no texto extraído.",
    )


def extrair_taxa_mes(texto: str, mes: int, ano: int) -> float:
    """Compatibilidade pública: devolve apenas a taxa mensal em decimal."""
    return extrair_dados_mes(texto, mes, ano).taxa_mensal


def parsear_bacen(pdf: Path | bytes, mes: int, ano: int) -> float:
    """Pipeline completo: PDF → taxa mensal decimal para o mês/ano alvo."""
    texto = _extrair_texto_pdf(pdf)
    return extrair_taxa_mes(texto, mes, ano)
