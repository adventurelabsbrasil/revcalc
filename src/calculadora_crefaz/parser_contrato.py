"""Extrai dados do Item II do contrato Crefaz em PDF."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import (
    MARCADOR_ITEM_II_FIM,
    MARCADOR_ITEM_II_INICIO,
    REGEX_CEDULA,
    REGEX_ITEM_II,
    REGEX_NOME_EMITENTE,
    TOLERANCIA_VALIDACAO_REAIS,
)
from .exceptions import ContratoParseError, ValidacaoContratoWarning


@dataclass
class DadosContrato:
    """Dados extraídos do contrato Crefaz."""

    # Cabeçalho
    numero_cedula: str
    nome_emitente: str

    # Item II — datas
    data_emissao: date
    primeiro_vencimento: date
    ultimo_vencimento: date

    # Item II — valores monetários (em reais, float)
    valor_nominal: float
    valor_emprestimo: float
    valor_total_contratado: float
    valor_prestacao: float
    tributos_iof: float
    tarifas: float

    # Item II — parâmetros
    prazo: int
    taxa_mensal: float  # decimal: 0.1877 para 18.77%
    taxa_anual: float

    # Texto bruto do Item II (para debug/log)
    item_ii_raw: str = ""


def _parse_valor_brl(s: str) -> float:
    """Converte '3.500,00' → 3500.00; '104,99' → 104.99."""
    s = s.strip().replace(".", "").replace(",", ".")
    return float(s)


def _parse_pct(s: str) -> float:
    """Converte '18,77' → 0.1877."""
    return float(s.replace(",", ".")) / 100.0


def _parse_data(s: str) -> date:
    return datetime.strptime(s.strip(), "%d/%m/%Y").date()


def _extrair_texto_pdf(pdf_path: Path | bytes) -> str:
    """Extrai texto completo do PDF via pdfplumber.

    Aceita Path ou bytes (para casos onde o PDF veio direto do Drive).
    """
    import pdfplumber

    if isinstance(pdf_path, (bytes, bytearray)):
        import io

        fh = io.BytesIO(pdf_path)
        with pdfplumber.open(fh) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def extrair_item_ii(texto_completo: str) -> str:
    """Recorta o bloco Item II do texto completo."""
    inicio = texto_completo.find(MARCADOR_ITEM_II_INICIO)
    if inicio == -1:
        raise ContratoParseError(
            "item_ii", f"Marcador '{MARCADOR_ITEM_II_INICIO}' não encontrado no PDF."
        )
    fim = texto_completo.find(MARCADOR_ITEM_II_FIM, inicio)
    if fim == -1:
        # Fallback: pegar até o final do texto
        return texto_completo[inicio:]
    return texto_completo[inicio:fim]


def _match_obrigatorio(regex, texto: str, campo: str) -> str:
    m = regex.search(texto)
    if not m:
        raise ContratoParseError(campo, f"Regex {regex.pattern!r} não encontrou match.")
    return m.group(1)


def parsear_contrato(pdf: Path | bytes) -> DadosContrato:
    """Pipeline completo: PDF → DadosContrato.

    Lança ContratoParseError se qualquer campo obrigatório faltar.
    Emite ValidacaoContratoWarning se Nominal + IOF + Tarifas ≠ Valor do Empréstimo.
    """
    texto = _extrair_texto_pdf(pdf)

    # Cabeçalho
    numero_cedula = _match_obrigatorio(REGEX_CEDULA, texto, "numero_cedula")

    # Nome do emitente: aceitar quebras de linha entre "Nome:" e "CPF"
    m_nome = REGEX_NOME_EMITENTE.search(texto)
    if not m_nome:
        raise ContratoParseError("nome_emitente", "Padrão 'Nome: ... CPF' não encontrado.")
    nome_emitente = " ".join(m_nome.group(1).split())  # colapsa whitespace/quebras

    # Item II
    item_ii = extrair_item_ii(texto)

    def grab(campo: str) -> str:
        return _match_obrigatorio(REGEX_ITEM_II[campo], item_ii, campo)

    dados = DadosContrato(
        numero_cedula=numero_cedula,
        nome_emitente=nome_emitente,
        data_emissao=_parse_data(grab("data_emissao")),
        primeiro_vencimento=_parse_data(grab("primeiro_vencimento")),
        ultimo_vencimento=_parse_data(grab("ultimo_vencimento")),
        valor_nominal=_parse_valor_brl(grab("valor_nominal")),
        valor_emprestimo=_parse_valor_brl(grab("valor_emprestimo")),
        valor_total_contratado=_parse_valor_brl(grab("valor_total_contratado")),
        valor_prestacao=_parse_valor_brl(grab("valor_prestacao")),
        tributos_iof=_parse_valor_brl(grab("tributos_iof")),
        tarifas=_parse_valor_brl(grab("tarifas")),
        prazo=int(grab("prazo")),
        taxa_mensal=_parse_pct(grab("taxa_mensal")),
        taxa_anual=_parse_pct(grab("taxa_anual")),
        item_ii_raw=item_ii,
    )

    # Validação: Nominal + IOF + Tarifas ≈ Valor do Empréstimo
    soma = dados.valor_nominal + dados.tributos_iof + dados.tarifas
    delta = abs(soma - dados.valor_emprestimo)
    if delta > TOLERANCIA_VALIDACAO_REAIS:
        warnings.warn(
            f"Divergência na soma do contrato: "
            f"Nominal ({dados.valor_nominal:.2f}) + IOF ({dados.tributos_iof:.2f}) + "
            f"Tarifas ({dados.tarifas:.2f}) = {soma:.2f}, "
            f"mas Valor do Empréstimo = {dados.valor_emprestimo:.2f} "
            f"(delta R$ {delta:.2f}).",
            ValidacaoContratoWarning,
            stacklevel=2,
        )

    return dados
