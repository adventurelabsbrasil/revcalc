"""Integração com a planilha de controle (POP-006) — modo planilha-driven.

A equipe da Rose mantém uma planilha Google de controle onde cada linha é um
contrato fechado. A coluna **Ação** (H) é um dropdown; o valor
``CONTRATO RECEBIDO`` marca os contratos prontos para cálculo. Este módulo:

  1. lê as linhas cuja Ação == ``CONTRATO RECEBIDO`` (a serem calculadas);
  2. após um cálculo bem-sucedido, escreve Ação == ``-CALCULO OK`` naquela linha.

Só toca a célula H da linha processada — nunca outras colunas nem as tabelas
dinâmicas à direita. Em falha, a linha fica **como estava** (o chamador não
chama :func:`marcar_calculo_ok`), preservando o estado para reprocessar depois.

Leitura/escrita usam a Sheets API (scope ``drive`` já cobre; a API precisa estar
habilitada no projeto GCP do OAuth).
"""

from __future__ import annotations

from dataclasses import dataclass

from googleapiclient.discovery import Resource

# ─── Convenção de colunas da planilha de controle (POP-006) ─────────────────
# Layout (col A é uma coluna-espaçador vazia):
#   A(0) vazia · B(1) UF · C(2) ADVBOX · D(3) CÁLCULO · E(4) Cliente ·
#   F(5) Atendente · G(6) Situação · H(7) Ação · I(8) Pasta DRIVE · J(9) Anotações
COL_NOME = 4          # E — nome do cliente (chave pra achar a pasta no Drive)
COL_ACAO = 7          # H — dropdown de Ação
COL_PASTA = 8         # I — dica de pasta no Drive
COL_NOTA = 9          # J — anotações (às vezes nº da cédula)

COL_ACAO_A1 = "H"     # letra da coluna Ação (pra range A1 do write-back)

# Valores do dropdown da coluna Ação (H) — EXATOS (validação de dados rejeita
# qualquer string fora da lista; "-CALCULO OK" tem traço e é sem acento).
ACAO_GATILHO = "CONTRATO RECEBIDO"   # → processar
ACAO_OK = "-CALCULO OK"              # → marcar após sucesso


@dataclass
class LinhaControle:
    """Uma linha da planilha de controle relevante para o cálculo."""

    row: int            # número da linha na planilha (1-based, como no A1)
    nome_cliente: str   # coluna E
    acao: str           # coluna H (valor atual)
    pasta_hint: str     # coluna I
    nota: str           # coluna J


def _cel(linha: list[str], idx: int) -> str:
    """Célula por índice, tolerante a linhas curtas (Sheets omite trailing vazias)."""
    return linha[idx].strip() if idx < len(linha) else ""


def ler_linhas(sheets: Resource, spreadsheet_id: str, tab: str) -> list[LinhaControle]:
    """Lê todas as linhas da aba como :class:`LinhaControle` (preserva o nº da linha)."""
    safe = tab.replace("'", "''")
    resp = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{safe}'!A1:J")
        .execute()
    )
    valores = resp.get("values", [])
    linhas: list[LinhaControle] = []
    for i, r in enumerate(valores):
        linhas.append(
            LinhaControle(
                row=i + 1,
                nome_cliente=_cel(r, COL_NOME),
                acao=_cel(r, COL_ACAO),
                pasta_hint=_cel(r, COL_PASTA),
                nota=_cel(r, COL_NOTA),
            )
        )
    return linhas


def linhas_para_calcular(linhas: list[LinhaControle]) -> list[LinhaControle]:
    """Filtra as linhas com Ação == ``CONTRATO RECEBIDO`` e nome de cliente presente."""
    return [
        ln
        for ln in linhas
        if ln.acao.upper() == ACAO_GATILHO and ln.nome_cliente
    ]


def marcar_calculo_ok(sheets: Resource, spreadsheet_id: str, tab: str, row: int) -> None:
    """Escreve ``-CALCULO OK`` na coluna Ação (H) da linha `row`.

    Idempotente do ponto de vista de resultado (reescrever o mesmo valor é inócuo).
    ``USER_ENTERED`` mantém a validação de dados do dropdown ativa.
    """
    safe = tab.replace("'", "''")
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{safe}'!{COL_ACAO_A1}{row}",
        valueInputOption="USER_ENTERED",
        body={"values": [[ACAO_OK]]},
    ).execute()


def ler_acao(sheets: Resource, spreadsheet_id: str, tab: str, row: int) -> str:
    """Relê o valor atual da coluna Ação (H) de uma linha — para verificação pós-escrita."""
    safe = tab.replace("'", "''")
    resp = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{safe}'!{COL_ACAO_A1}{row}")
        .execute()
    )
    vals = resp.get("values", [])
    return vals[0][0].strip() if vals and vals[0] else ""
