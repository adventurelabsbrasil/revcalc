"""Orquestra os 12 passos do pipeline.

Função principal `executar(...)` é genérica em "como confirmar dedup" e em
"para onde enviar mensagens de status" — recebe callbacks pra UI/CLI plugarem
seu próprio comportamento.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional
from unidecode import unidecode

from . import calculadora, drive, parser_bacen, parser_contrato
from .auth import SessaoAutenticada
from .capturas import (
    CapturasError,
    capturar_pagina_pdf,
    gerar_capturas,
    gerar_capturas_regionais,
    nome_pdf,
)
from .config import (
    CAPTURAS_PDF,
    NOME_BACEN_PASTA_CLIENTE,
    NOME_LOG,
    NOME_XLSX_SAIDA,
    REGIOES_CALCULO,
)
from .exceptions import (
    BloqueioDedup,
    EntradaInvalida,
)
from .log_writer import ArquivoGerado, DadosLog, combinar_log_anterior, gerar_log
from .planilha import DadosPlanilha, gerar_xlsx

logger = logging.getLogger(__name__)


# ─── Tipos auxiliares ───────────────────────────────────────────────────────


# Callback de status: o pipeline chama isso a cada passo concluído com mensagem
# UI usa pra atualizar o painel de log; CLI usa pra `print`
StatusCallback = Callable[[str], None]

# Callback de confirmação de dedup. Recebe a data de modificação do XLSX existente,
# devolve True se usuário confirma sobrescrever.
ConfirmDedupCallback = Callable[[str], bool]


@dataclass
class ResultadoPipeline:
    """O que o pipeline devolve no final."""

    pasta_drive_path: str
    pasta_drive_url: str
    xlsx_file_id: str
    log_file_id: str
    bacen_file_id: Optional[str]  # None se BACEN já estava na pasta
    arquivos_gerados: list[ArquivoGerado] = field(default_factory=list)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _validar_nome(nome: str) -> str:
    nome = nome.strip()
    if len(nome.split()) < 2:
        raise EntradaInvalida(
            "Digite o nome completo (mínimo 2 palavras)."
        )
    return nome


def _nome_xlsx_saida(nome_emitente: str) -> str:
    """3500.0 → MARLI SUELI BERGER DAMBROSIO (uppercase ASCII)."""
    return NOME_XLSX_SAIDA.format(nome=unidecode(nome_emitente).upper())


def _noop(_: str) -> None:
    pass


# ─── Pipeline ───────────────────────────────────────────────────────────────


def executar(
    nome_cliente: str,
    sessao: SessaoAutenticada,
    *,
    forcar_contrato_nome: Optional[str] = None,
    forcar_sobrescrita: bool = False,
    status: StatusCallback = _noop,
    aviso: StatusCallback = _noop,
    confirmar_dedup: ConfirmDedupCallback = lambda _: False,
    hoje: Optional[date] = None,
) -> ResultadoPipeline:
    """Executa o pipeline completo: nome → XLSX no Drive + log.

    Cada passo emite uma mensagem de status via `status(...)`.
    Se o PDF BACEN da pasta da cliente não existir e o sistema copiar do
    repositório central, também chama `aviso(...)` (ex.: UI em destaque).
    """
    nome_cliente = _validar_nome(nome_cliente)
    hoje = hoje or date.today()
    service = sessao.drive_service()

    # 3. Localizar pasta do cliente
    status("Buscando pasta da cliente no Drive...")
    pasta = drive.localizar_pasta_cliente(service, nome_cliente)
    status(f"Pasta encontrada: {pasta.path}")

    # 4. Dedup
    calculo_existente = drive.buscar_calculo_existente(service, pasta.id)
    if calculo_existente and not forcar_sobrescrita:
        status(
            f"Cálculo já existe ({calculo_existente.name}, "
            f"modificado em {calculo_existente.modified_time})"
        )
        if not confirmar_dedup(calculo_existente.modified_time or "data desconhecida"):
            raise BloqueioDedup(
                f"Cálculo '{calculo_existente.name}' já existe e usuário não confirmou sobrescrita."
            )
        status("Sobrescrita confirmada.")

    # 5. Localizar contrato
    status("Localizando contrato Crefaz...")
    contrato_arquivo = drive.localizar_contrato(
        service, pasta.id, forcar_nome=forcar_contrato_nome
    )
    status(f"Contrato encontrado: {contrato_arquivo.name}")

    # 6. Baixar e parsear contrato
    status("Baixando e parseando contrato...")
    pdf_bytes = drive.baixar_pdf(service, contrato_arquivo.id)
    dados_contrato = parser_contrato.parsear_contrato(pdf_bytes)
    status(
        f"Contrato lido: cédula {dados_contrato.numero_cedula}, "
        f"prazo {dados_contrato.prazo}, taxa {dados_contrato.taxa_mensal*100:.2f}%"
    )

    # 7. Calcular parcelas pagas
    parcelas = calculadora.parcelas_pagas(
        primeiro_vencimento=dados_contrato.primeiro_vencimento,
        prazo=dados_contrato.prazo,
        hoje=hoje,
    )
    aba = calculadora.decidir_aba(dados_contrato.prazo)
    status(f"Parcelas pagas até hoje: {parcelas} | aba: {aba}")

    # 8. Localizar BACEN — primeiro na pasta da cliente
    # Referência: mês/ano da data de emissão (Item II), não do 1º vencimento.
    bacen_mes = dados_contrato.data_emissao.month
    bacen_ano = dados_contrato.data_emissao.year

    bacen_na_pasta = drive.localizar_bacen_na_pasta(service, pasta.id)
    if bacen_na_pasta:
        status(f"BACEN já na pasta da cliente: {bacen_na_pasta.name}")
        bacen_pdf_bytes = drive.baixar_pdf(service, bacen_na_pasta.id)
        bacen_origem = "pasta_cliente"
        bacen_file_id_subido: Optional[str] = None
    else:
        status(f"Buscando BACEN {bacen_mes:02d}/{bacen_ano} no repositório central...")
        bacen_repo = drive.localizar_bacen_no_repositorio(service, bacen_mes, bacen_ano)
        bacen_pdf_bytes = drive.baixar_pdf(service, bacen_repo.id)
        bacen_origem = "serie_do_bacen"
        # Subir cópia para a pasta da cliente
        status("Copiando BACEN para a pasta da cliente...")
        bacen_file_id_subido, _ = drive.subir_ou_sobrescrever(
            service,
            pasta.id,
            NOME_BACEN_PASTA_CLIENTE,
            bacen_pdf_bytes,
            "application/pdf",
        )
        aviso(
            f"ATENÇÃO: «{NOME_BACEN_PASTA_CLIENTE}» não estava na pasta da cliente. "
            "O sistema baixou o PDF da série BACEN (repositório central) e gravou "
            "o arquivo nesta pasta automaticamente."
        )

    # 9. Extrair taxa BACEN
    taxa_bacen = parser_bacen.extrair_taxa_mes(
        parser_bacen._extrair_texto_pdf(bacen_pdf_bytes), bacen_mes, bacen_ano
    )
    status(f"Taxa BACEN para {bacen_mes:02d}/{bacen_ano}: {taxa_bacen*100:.2f}%")

    # 10-11. Gerar XLSX
    status("Gerando planilha preenchida...")
    dados_planilha = DadosPlanilha(
        contrato=dados_contrato,
        taxa_bacen=taxa_bacen,
        parcelas_pagas=parcelas,
        data_calculo=hoje,
    )
    xlsx_bytes = gerar_xlsx(dados_planilha)

    # 12. Upload XLSX
    nome_xlsx = _nome_xlsx_saida(dados_contrato.nome_emitente)
    status(f"Subindo {nome_xlsx} para o Drive...")
    xlsx_id, xlsx_sobrescrito = drive.subir_ou_sobrescrever(
        service,
        pasta.id,
        nome_xlsx,
        xlsx_bytes,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # 12b. Capturas (PDF + PNG por página) — v0.6.0
    arquivos_capturas: list[ArquivoGerado] = []
    try:
        status("Gerando capturas (PDF + PNG)...")
        cap = gerar_capturas(xlsx_bytes, nome_aba=aba)

        # PDF unificado
        pdf_nome = nome_pdf(aba)
        status(f"Subindo {pdf_nome}...")
        _, pdf_sobrescrito = drive.subir_ou_sobrescrever(
            service, pasta.id, pdf_nome, cap.pdf_bytes, "application/pdf"
        )
        arquivos_capturas.append(
            ArquivoGerado(pdf_nome, "sobrescrito" if pdf_sobrescrito else "novo")
        )

        # PNGs por página
        for png in cap.pngs:
            _, png_sobrescrito = drive.subir_ou_sobrescrever(
                service, pasta.id, png.nome_arquivo, png.bytes_, "image/png"
            )
            arquivos_capturas.append(
                ArquivoGerado(png.nome_arquivo, "sobrescrito" if png_sobrescrito else "novo")
            )
        status(f"Capturas gerais: {cap.num_paginas} PNG + 1 PDF.")

        # 12c. Capturas regionais (6 blocos da aba CÁLCULO)
        status("Gerando capturas regionais (6 blocos)...")
        regionais = gerar_capturas_regionais(
            xlsx_bytes,
            REGIOES_CALCULO,
            nome_aba=aba,
            on_status=status,
        )
        for png in regionais:
            _, png_sobrescrito = drive.subir_ou_sobrescrever(
                service, pasta.id, png.nome_arquivo, png.bytes_, "image/png"
            )
            arquivos_capturas.append(
                ArquivoGerado(png.nome_arquivo, "sobrescrito" if png_sobrescrito else "novo")
            )
        status(f"Capturas regionais: {len(regionais)} PNGs.")

        # 12d. Capturas de PDFs (Item II do contrato + Séries BACEN)
        for label, conf in CAPTURAS_PDF.items():
            tipo = conf["tipo"]
            regex = conf["marcador_regex"]
            regex_fim = conf.get("marcador_fim_regex")
            altura_fallback_ratio = conf.get("altura_fallback_ratio", 0.50)
            nome_png = f"13 Print {label}.png"
            if tipo == "contrato":
                pdf_src = pdf_bytes  # bytes do contrato Crefaz já baixado
            elif tipo == "bacen":
                pdf_src = bacen_pdf_bytes
            else:
                aviso(f"Tipo de captura PDF desconhecido: {tipo!r} — ignorando {label}.")
                continue
            try:
                png = capturar_pagina_pdf(
                    pdf_src,
                    regex,
                    nome_png,
                    marcador_fim_regex=regex_fim,
                    altura_fallback_ratio=altura_fallback_ratio,
                )
            except CapturasError as e:
                aviso(f"Captura PDF {label} falhou: {e}")
                continue
            if png is None:
                aviso(
                    f"Captura {label}: marcador {regex!r} não encontrado no PDF — ignorada."
                )
                continue
            _, sobrescrito = drive.subir_ou_sobrescrever(
                service, pasta.id, png.nome_arquivo, png.bytes_, "image/png"
            )
            arquivos_capturas.append(
                ArquivoGerado(png.nome_arquivo, "sobrescrito" if sobrescrito else "novo")
            )
        status(f"Capturas concluídas: {len(arquivos_capturas)} arquivos.")
    except CapturasError as e:
        # Não bloqueia o cálculo — só avisa.
        aviso(
            f"Capturas não geradas: {e}. "
            "Cliente continua com XLSX e log normalmente. "
            "Instale LibreOffice no Mac da equipe pra ativar capturas automáticas."
        )

    # 13. Log
    arquivos = [
        ArquivoGerado(nome_xlsx, "sobrescrito" if xlsx_sobrescrito else "novo"),
    ]
    if bacen_origem == "serie_do_bacen":
        arquivos.append(ArquivoGerado(NOME_BACEN_PASTA_CLIENTE, "novo"))
    else:
        arquivos.append(ArquivoGerado(bacen_na_pasta.name, "mantido"))
    arquivos.extend(arquivos_capturas)
    log_existente = drive.buscar_arquivo_por_nome(service, pasta.id, NOME_LOG)
    log_anterior_txt: str | None = None
    if log_existente:
        log_anterior_txt = drive.baixar_pdf(service, log_existente.id).decode(
            "utf-8", errors="replace"
        )

    arquivos.append(
        ArquivoGerado(NOME_LOG, "append" if log_anterior_txt else "novo")
    )

    novo_bloco_log = gerar_log(
        DadosLog(
            dados_planilha=dados_planilha,
            usuario_email=sessao.email,
            pasta_drive_path=pasta.path,
            contrato_arquivo=contrato_arquivo.name,
            bacen_origem=bacen_origem,
            bacen_mes=bacen_mes,
            bacen_ano=bacen_ano,
            aba_template=aba,
            arquivos_gerados=arquivos,
        )
    )

    log_txt = combinar_log_anterior(log_anterior_txt, novo_bloco_log)

    log_id, _ = drive.subir_ou_sobrescrever(
        service,
        pasta.id,
        NOME_LOG,
        log_txt.encode("utf-8"),
        "text/plain",
    )

    status("Pronto.")
    return ResultadoPipeline(
        pasta_drive_path=pasta.path,
        pasta_drive_url=drive.url_pasta(pasta.id),
        xlsx_file_id=xlsx_id,
        log_file_id=log_id,
        bacen_file_id=bacen_file_id_subido,
        arquivos_gerados=arquivos,
    )
