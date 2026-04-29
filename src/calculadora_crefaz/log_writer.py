"""Gera o arquivo `12 Log.txt` que vai junto na pasta da cliente."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from . import __version__
from .config import NOME_BACEN_PASTA_CLIENTE, nome_arquivo_bacen
from .planilha import DadosPlanilha

OrigemBacen = Literal["pasta_cliente", "serie_do_bacen"]
ArquivoStatus = Literal["novo", "sobrescrito", "mantido", "append"]


@dataclass
class ArquivoGerado:
    nome: str
    status: ArquivoStatus


@dataclass
class DadosLog:
    """Tudo o que entra no log.txt — uma sessão de processamento."""

    dados_planilha: DadosPlanilha
    usuario_email: str
    pasta_drive_path: str  # ex: "EMPRESTIMO DE ENERGIA/10. RIO GRANDE DO SUL/MARLI..."
    contrato_arquivo: str  # ex: "09 Contrato Crefaz.pdf"
    bacen_origem: OrigemBacen
    bacen_mes: int
    bacen_ano: int
    aba_template: str
    arquivos_gerados: list[ArquivoGerado]
    status: str = "SUCESSO"
    timestamp: datetime | None = None  # default: now()

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


def _fmt_real(v: float) -> str:
    """3500.0 → '3.500,00'"""
    s = f"{v:,.2f}"
    # Inverter: vírgula decimal, ponto milhar (formato pt-BR)
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _fmt_pct(v: float) -> str:
    """0.1449 → '14,49%'"""
    return f"{v * 100:.2f}".replace(".", ",") + "%"


def _bacen_origem_humana(origem: OrigemBacen) -> str:
    if origem == "pasta_cliente":
        return "pasta_cliente (já estava em 11 Series Temporais.pdf)"
    return "serie_do_bacen (copiado para 11 Series Temporais.pdf)"


LOG_SEPARATOR = "\n\n" + ("=" * 60) + "\n\n"


def _prefixo_aviso_bacen_incluido_pelo_sistema(dados: DadosLog) -> str:
    """Bloco em destaque no log quando o BACEN veio do repositório (não estava na pasta)."""
    if dados.bacen_origem != "serie_do_bacen":
        return ""
    pdf_serie = nome_arquivo_bacen(dados.bacen_mes, dados.bacen_ano)
    return f"""\
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
ATENÇÃO — PDF BACEN NÃO ESTAVA NA PASTA DA CLIENTE
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Antes deste cálculo não havia «{NOME_BACEN_PASTA_CLIENTE}» na pasta.
O sistema obteve o arquivo «{pdf_serie}» da pasta «Série do Bacen» no Drive
e gravou «{NOME_BACEN_PASTA_CLIENTE}» nesta pasta automaticamente.

Recomendação: nas próximas vezes, inclua manualmente o PDF na pasta da
cliente (fonte oficial BACEN/SGS), para manter o processo explícito.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

"""


def combinar_log_anterior(conteudo_anterior: str | None, novo_bloco: str) -> str:
    """Concatena histórico existente com novo bloco (append no Drive)."""
    if conteudo_anterior is None or not conteudo_anterior.strip():
        return novo_bloco
    return conteudo_anterior.rstrip() + LOG_SEPARATOR + novo_bloco


def gerar_log(dados: DadosLog) -> str:
    contrato = dados.dados_planilha.contrato
    pl = dados.dados_planilha

    excesso_pct = (contrato.taxa_mensal / pl.taxa_bacen - 1.0) * 100 if pl.taxa_bacen else 0.0

    arquivos_lines = [
        f"- {a.nome} ({a.status})" for a in dados.arquivos_gerados
    ]

    prefixo_aviso = _prefixo_aviso_bacen_incluido_pelo_sistema(dados)
    # Com aviso: uma quebra após "Por:" e o bloco; sem aviso: linha em branco como antes.
    apos_por = f"\n{prefixo_aviso}" if prefixo_aviso else "\n\n"

    txt = f"""\
Calculadora de Ação Crefaz — MVP v{__version__}
=========================================

Processado em: {dados.timestamp.strftime("%Y-%m-%d %H:%M:%S")} BRT
Por: {dados.usuario_email}{apos_por}CLIENTE
-------
Nome: {contrato.nome_emitente}
Pasta no Drive: {dados.pasta_drive_path}

CONTRATO LIDO
-------------
Arquivo: {dados.contrato_arquivo}
Número da cédula: {contrato.numero_cedula}

Item II extraído:
- Data de Emissão: {contrato.data_emissao.strftime("%d/%m/%Y")}
- Prazo: {contrato.prazo} parcelas
- 1º Vencimento: {contrato.primeiro_vencimento.strftime("%d/%m/%Y")}
- Último Vencimento: {contrato.ultimo_vencimento.strftime("%d/%m/%Y")}
- Valor Nominal: R$ {_fmt_real(contrato.valor_nominal)}
- Valor da Prestação: R$ {_fmt_real(contrato.valor_prestacao)}
- Taxa de Juros Mensal: {_fmt_pct(contrato.taxa_mensal)}
- Tributos/IOF: R$ {_fmt_real(contrato.tributos_iof)}
- Tarifas: R$ {_fmt_real(contrato.tarifas)}

CÁLCULO
-------
Parcelas pagas até hoje: {pl.parcelas_pagas}
Aba do template: {dados.aba_template}

BACEN
-----
Origem: {_bacen_origem_humana(dados.bacen_origem)}
Mês de referência (data de emissão): {dados.bacen_mes:02d}/{dados.bacen_ano}
Taxa 25464: {_fmt_pct(pl.taxa_bacen)}

DIVERGÊNCIA
-----------
Taxa pactuada: {_fmt_pct(contrato.taxa_mensal)}
Taxa BACEN: {_fmt_pct(pl.taxa_bacen)}
Excesso: {excesso_pct:+.0f}% (taxa pactuada / taxa BACEN - 1)

ARQUIVOS GERADOS NESTA EXECUÇÃO
-------------------------------
{chr(10).join(arquivos_lines)}

CAPTURAS
--------
Geradas automaticamente na pasta da cliente:
  - 13 Print {dados.aba_template}.pdf      (PDF unificado, paisagem A4)
  - 13 Print {dados.aba_template}*.png     (1 PNG por página, 150 DPI)
Se ausentes em ARQUIVOS GERADOS acima, LibreOffice não estava
disponível quando o cálculo rodou — XLSX e log seguem válidos.

STATUS: {dados.status}
"""
    return txt
