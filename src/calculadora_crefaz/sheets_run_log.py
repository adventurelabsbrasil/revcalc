"""Append de uma linha na planilha Google central de runs (equipa / tenant).

Cabeçalho sugerido na **linha 1** da aba (criar manualmente uma vez):

timestamp_brt | user_email | client_name | drive_folder_url | duration_sec |
files_before | files_after | files_added | files_modified | cedula | term_months |
paid_installments | rate_contract_pct | rate_bacen_pct | bacen_ref | bacen_source |
contract_pdf | revcalc_version
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from googleapiclient.discovery import Resource


def append_master_run_row(
    sheets: Resource,
    spreadsheet_id: str,
    tab: str,
    row: list[Any],
) -> None:
    """Insere uma linha no fim da aba (`append` da API Sheets)."""
    safe_tab = tab.replace("'", "''")
    range_a1 = f"'{safe_tab}'!A:Z"
    sheets.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_a1,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def build_master_run_row(
    *,
    user_email: str,
    client_name: str,
    folder_url: str,
    duration_sec: float,
    files_before: int,
    files_after: int,
    files_added: int,
    files_modified: int,
    cedula: str,
    term_months: int,
    paid_installments: int,
    rate_contract_pct: float,
    rate_bacen_pct: float,
    bacen_ref: str,
    bacen_source: str,
    contract_pdf: str,
    revcalc_version: str,
) -> list[Any]:
    ts = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")
    return [
        ts,
        user_email,
        client_name,
        folder_url,
        round(duration_sec, 2),
        files_before,
        files_after,
        files_added,
        files_modified,
        cedula,
        term_months,
        paid_installments,
        round(rate_contract_pct, 4),
        round(rate_bacen_pct, 4),
        bacen_ref,
        bacen_source,
        contract_pdf,
        revcalc_version,
    ]
