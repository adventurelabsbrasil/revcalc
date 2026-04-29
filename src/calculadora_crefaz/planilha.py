"""Preenche o template Calculo.xlsx com os dados do cálculo."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.workbook import Workbook

from .calculadora import decidir_aba
from .config import (
    CELULAS_DADOS,
    NOME_ABA_DADOS,
    TEMPLATE_PATH,
    celulas_para_aba,
)
from .parser_contrato import DadosContrato

logger = logging.getLogger(__name__)


@dataclass
class DadosPlanilha:
    """Dados que vão escritos no XLSX final."""

    contrato: DadosContrato
    taxa_bacen: float  # decimal, ex: 0.0647 para 6,47%
    parcelas_pagas: int
    data_calculo: date  # data_atual usada no cálculo


def _titulo_operacao(contrato: DadosContrato) -> str:
    return (
        f"CÁLCULOS DA OPERAÇÃO Nº {contrato.numero_cedula} - "
        f"CLIENTE: {contrato.nome_emitente.upper()} x BANCO CREFAZ"
    )


def _remover_abas_nao_usadas(
    wb: Workbook,
    aba_visual: str,
    *,
    manter: tuple[str, ...] = (),
) -> None:
    """Remove abas que não são a visual-alvo nem as extras (ex.: NOME_ABA_DADOS)."""
    for nome in list(wb.sheetnames):
        if nome == aba_visual or nome in manter:
            continue
        del wb[nome]


def _forcar_landscape(ws, aba: str) -> None:
    """Defesa em profundidade: força paisagem caso template seja modificado e perca a config.

    Em v0.6.0 o template `Calculo.xlsx` tem aba CÁLCULO única já em landscape A4
    com fitToWidth=1 e fitToHeight=1. Mantém função como backstop de runtime.
    """
    if ws.page_setup.orientation != "landscape":
        logger.warning(
            "Aba %s está em %s no template — forçando landscape.",
            aba,
            ws.page_setup.orientation,
        )
        ws.page_setup.orientation = "landscape"


def _set_date_cell(ws, coord: str, d: date) -> None:
    """Escreve data como datetime e força formato BR no XLSX."""
    cell = ws[coord]
    cell.value = datetime.combine(d, datetime.min.time())
    cell.number_format = "dd/mm/yyyy"


def _preencher_aba(ws, aba: str, dados: DadosPlanilha) -> None:
    celulas = celulas_para_aba(aba)
    contrato = dados.contrato

    # Título
    ws[celulas["titulo"]] = _titulo_operacao(contrato)

    # Datas (dd/mm/yyyy defensivo — não confiar só no template)
    _set_date_cell(ws, celulas["data_pactuacao"], contrato.data_emissao)
    _set_date_cell(ws, celulas["primeiro_vencimento"], contrato.primeiro_vencimento)

    # Valores monetários (R$)
    ws[celulas["valor_principal"]] = contrato.valor_nominal
    ws[celulas["tac"]] = contrato.tarifas
    ws[celulas["iof"]] = contrato.tributos_iof
    ws[celulas["qtd_parcelas"]] = contrato.prazo
    ws[celulas["valor_prestacao"]] = contrato.valor_prestacao

    # Taxas em decimal (formato % do template multiplica por 100 ao exibir)
    ws[celulas["taxa_pactuada"]] = contrato.taxa_mensal
    ws[celulas["taxa_bacen"]] = dados.taxa_bacen

    # Parcelas pagas (inteiro)
    ws[celulas["parcelas_pagas"]] = dados.parcelas_pagas


def _preencher_aba_dados(ws, dados: DadosPlanilha) -> None:
    """Escreve apenas na aba DADOS — a aba PRICE deve usar fórmulas =DADOS!..."""
    c = CELULAS_DADOS
    contrato = dados.contrato
    ws[c["titulo"]] = _titulo_operacao(contrato)
    _set_date_cell(ws, c["data_emissao"], contrato.data_emissao)
    _set_date_cell(ws, c["primeiro_vencimento"], contrato.primeiro_vencimento)
    _set_date_cell(ws, c["ultimo_vencimento"], contrato.ultimo_vencimento)
    ws[c["valor_principal"]] = contrato.valor_nominal
    ws[c["tac"]] = contrato.tarifas
    ws[c["iof"]] = contrato.tributos_iof
    ws[c["qtd_parcelas"]] = contrato.prazo
    ws[c["valor_prestacao"]] = contrato.valor_prestacao
    ws[c["taxa_pactuada"]] = contrato.taxa_mensal
    ws[c["taxa_bacen"]] = dados.taxa_bacen
    ws[c["parcelas_pagas"]] = dados.parcelas_pagas
    _set_date_cell(ws, c["data_calculo"], dados.data_calculo)


def gerar_xlsx(dados: DadosPlanilha, template_path: Path | None = None) -> bytes:
    """Gera o XLSX preenchido em memória, retornando os bytes.

    - Carrega o template
    - Decide a aba apropriada via `decidir_aba(prazo)`
    - Remove abas não usadas (mantém `DADOS` se existir — modelo dados + visual)
    - Preenche: modo legacy (direto na PRICE) ou modo DADOS (só aba DADOS; PRICE com fórmulas)
    - Força landscape na aba visual se necessário
    - Retorna bytes prontos para upload
    """
    template_path = template_path or TEMPLATE_PATH
    wb = load_workbook(template_path)

    aba = decidir_aba(dados.contrato.prazo)
    if aba not in wb.sheetnames:
        raise ValueError(
            f"Aba '{aba}' não encontrada no template. "
            f"Abas disponíveis: {wb.sheetnames}"
        )

    usa_dados = NOME_ABA_DADOS in wb.sheetnames
    manter = (NOME_ABA_DADOS,) if usa_dados else ()
    _remover_abas_nao_usadas(wb, aba, manter=manter)
    ws = wb[aba]

    if usa_dados:
        _preencher_aba_dados(wb[NOME_ABA_DADOS], dados)
        logger.info(
            "Template com aba %s — valores só na fonte; PRICE deve referenciar fórmulas.",
            NOME_ABA_DADOS,
        )
    else:
        _preencher_aba(ws, aba, dados)

    _forcar_landscape(ws, aba)

    # Força recálculo na abertura — sem isso, openpyxl salva o XLSX sem
    # calcChain.xml e a primeira renderização (LibreOffice headless ou
    # Sheets/Excel cliente) pode mostrar células de fórmula vazias até o
    # usuário tocar/recalcular manualmente.
    wb.calculation.fullCalcOnLoad = True

    out = BytesIO()
    wb.save(out)
    return out.getvalue()
