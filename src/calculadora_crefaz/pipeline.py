"""Orquestra o pipeline completo (Drive → contrato → BACEN → XLSX → capturas → run log).

Função principal `executar(...)` recebe callbacks de status/aviso para UI ou CLI.
Mensagens de execução em inglês. v0.6.9: log .txt deixou de ser salvo na pasta
da cliente — audit trail vive apenas na planilha central de runs (Sheets).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

from . import __version__, calculadora, drive, parser_bacen, parser_contrato
from .auth_core import SessaoAutenticada
from .capturas import (
    CapturasError,
    capturar_pagina_pdf,
    gerar_capturas,
    nome_pdf,
    recortar_bloco_pmt_pdf,
)
from .config import (
    CAPTURA_IMG01_CONTRATO,
    NOME_IMAG_01,
    NOME_IMAG_02,
    master_run_log_sheet_tab,
    master_run_log_spreadsheet_id,
    master_run_log_url,
    nome_series_temporais,
    nome_xlsx_saida,
    numero_prefixo,
)
from .exceptions import (
    CalculadoraError,
    CalculoJaExiste,
    ContratoNaoEncontrado,
    EntradaInvalida,
    PastaAmbigua,
    PastaNaoEncontrada,
)
from .log_writer import ArquivoGerado
from .sheets_run_log import append_master_run_row, build_master_run_row
from .planilha import DadosPlanilha, gerar_xlsx

logger = logging.getLogger(__name__)


StatusCallback = Callable[[str], None]


@dataclass
class ResultadoPipeline:
    pasta_drive_path: str
    pasta_drive_url: str
    xlsx_file_id: str
    log_file_id: str
    bacen_file_id: Optional[str]
    arquivos_gerados: list[ArquivoGerado] = field(default_factory=list)
    master_run_log_url: Optional[str] = None
    master_run_log_row_appended: bool = False
    executor_email: str = ""
    duration_sec: float = 0.0
    files_before: int = 0
    files_after: int = 0
    files_added: int = 0
    files_modified: int = 0
    # Pastas/contratos que já tinham cálculo e foram PULADOS (não refeitos).
    # Cada item: {"pasta": <nome>, "arquivo": <nome do Calculo existente>}.
    pulados: list[dict] = field(default_factory=list)


# ── Lote de múltiplos clientes ───────────────────────────────────────────────
# Status por cliente: "ok" (calculou algo) · "nada_novo" (tudo já feito, pulou) ·
# "nao_encontrado" · "ambiguo" · "erro".
@dataclass
class ClienteResultado:
    nome: str
    status: str
    resultado: Optional[ResultadoPipeline] = None
    erro: Optional[str] = None
    sugestoes: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)


@dataclass
class ResultadoLote:
    clientes: list[ClienteResultado] = field(default_factory=list)
    resumo: dict = field(default_factory=dict)


def _validar_nome(nome: str) -> str:
    nome = nome.strip()
    if len(nome.split()) < 2:
        raise EntradaInvalida("Digite o nome completo (mínimo 2 palavras).")
    return nome


def _noop(_: str) -> None:
    pass


def _count_arquivos_por_status(arquivos: list[ArquivoGerado]) -> tuple[int, int]:
    added = sum(1 for a in arquivos if a.status == "novo")
    modified = sum(1 for a in arquivos if a.status == "sobrescrito")
    return added, modified


def _segmento_final(path: str) -> str:
    return path.rstrip("/").split("/")[-1]


def _agregar(resultados: list[ResultadoPipeline], pasta_raiz) -> ResultadoPipeline:
    """Consolida os resultados (raiz + subpastas) num único ResultadoPipeline.

    Os arquivos das subpastas levam o prefixo «<subpasta>/» pra ficar claro onde
    cada um foi gravado. URL/path apontam pra pasta raiz (botão "abrir pasta").
    """
    base = resultados[0]
    arquivos: list[ArquivoGerado] = []
    for r in resultados:
        prefixo = "" if r.pasta_drive_path == pasta_raiz.path else f"{_segmento_final(r.pasta_drive_path)}/"
        arquivos.extend(ArquivoGerado(prefixo + a.nome, a.status) for a in r.arquivos_gerados)
    return ResultadoPipeline(
        pasta_drive_path=pasta_raiz.path,
        pasta_drive_url=drive.url_pasta(pasta_raiz.id),
        xlsx_file_id=base.xlsx_file_id,
        log_file_id="",
        bacen_file_id=base.bacen_file_id,
        arquivos_gerados=arquivos,
        master_run_log_url=base.master_run_log_url,
        master_run_log_row_appended=any(r.master_run_log_row_appended for r in resultados),
        executor_email=base.executor_email,
        duration_sec=sum(r.duration_sec for r in resultados),
        files_before=base.files_before,
        files_after=base.files_after,
        files_added=sum(r.files_added for r in resultados),
        files_modified=sum(r.files_modified for r in resultados),
    )


def _resultado_vazio_pulados(pasta_raiz, pulados: list[dict]) -> ResultadoPipeline:
    """Resultado 'nada novo': todos os contratos da cliente já tinham cálculo.

    Não é erro — a cliente pediu que já-calculados sejam pulados. Carrega só a
    lista de `pulados` e o link da pasta raiz (sem arquivos gerados)."""
    return ResultadoPipeline(
        pasta_drive_path=pasta_raiz.path,
        pasta_drive_url=drive.url_pasta(pasta_raiz.id),
        xlsx_file_id="",
        log_file_id="",
        bacen_file_id=None,
        pulados=pulados,
    )


def executar(
    nome_cliente: str,
    sessao: SessaoAutenticada,
    *,
    forcar_contrato_nome: Optional[str] = None,
    status: StatusCallback = _noop,
    aviso: StatusCallback = _noop,
    hoje: Optional[date] = None,
) -> ResultadoPipeline:
    """Orquestra o run: processa a pasta RAIZ + cada SUBPASTA DIRETA com contrato.

    v0.9.4: alguns clientes têm o contrato ativo na raiz e contratos quitados em
    subpastas (ex.: VLADIMIR). Processa cada pasta com contrato Crefaz, gravando a
    saída na respectiva pasta; pastas sem contrato são puladas silenciosamente.

    v0.9.8: contrato que já tem cálculo na pasta é PULADO (não refeito) — a cliente
    apaga o Calculo.xlsx no Drive se quiser recalcular. As pastas puladas voltam em
    `ResultadoPipeline.pulados`; "tudo pulado" não é erro (retorna resultado vazio).
    """
    nome_cliente = _validar_nome(nome_cliente)
    hoje = hoje or date.today()
    service = sessao.drive_service()

    def emit(msg: str) -> None:
        status(msg)

    emit("=== Planned steps ===")
    for step in (
        "Locate client folder on Drive (+ direct subfolders)",
        "For each folder with a Crefaz contract (skip if already calculated): parse, BACEN, XLSX, captures, run log",
    ):
        emit(f"  • {step}")
    emit("")
    emit("=== Execution ===")
    emit(f"Executed by: {sessao.email}")

    emit("Locating client folder...")
    pasta_raiz = drive.localizar_pasta_cliente(service, nome_cliente)
    emit(f"Folder found: {pasta_raiz.path}")
    subpastas = drive.listar_subpastas(service, pasta_raiz)
    pastas = [pasta_raiz, *subpastas]
    if subpastas:
        emit(f"Direct subfolders: {len(subpastas)} — each with a Crefaz contract will be processed too.")

    resultados: list[ResultadoPipeline] = []
    pulados: list[dict] = []
    for pasta in pastas:
        is_raiz = pasta is pasta_raiz
        if not is_raiz:
            emit("")
            emit(f"=== Subfolder: {pasta.nome_real} ===")
        try:
            resultados.append(
                _processar_pasta(
                    service,
                    sessao,
                    pasta,
                    forcar_contrato_nome=forcar_contrato_nome if is_raiz else None,
                    emit=emit,
                    aviso=aviso,
                    hoje=hoje,
                )
            )
        except ContratoNaoEncontrado:
            emit(f"[skipped] {pasta.nome_real} — no Crefaz contract in this folder.")
        except CalculoJaExiste as e:
            pulados.append({"pasta": e.pasta, "arquivo": e.arquivo})

    if not resultados:
        if pulados:
            emit("")
            emit(f"Nothing new — {len(pulados)} contract(s) already calculated (skipped).")
            return _resultado_vazio_pulados(pasta_raiz, pulados)
        raise ContratoNaoEncontrado(
            "Nenhum contrato Crefaz encontrado na pasta da cliente nem nas subpastas diretas."
        )

    emit("")
    emit(
        f"All done — {len(resultados)} folder(s) processed"
        + (f", {len(pulados)} already-calculated skipped." if pulados else ".")
    )
    resultado = _agregar(resultados, pasta_raiz)
    resultado.pulados = pulados
    return resultado


def executar_lote(
    nomes: list[str],
    sessao: SessaoAutenticada,
    *,
    status: StatusCallback = _noop,
    aviso: StatusCallback = _noop,
    hoje: Optional[date] = None,
) -> ResultadoLote:
    """Processa VÁRIOS clientes em sequência (v0.9.8), aplicando a regra de pular
    em cada um. Erro por-cliente (nome não encontrado/ambíguo/sem contrato) NÃO
    interrompe a tanda — vira status no relatório. Retorna ResultadoLote."""
    clientes: list[ClienteResultado] = []
    for nome in nomes:
        status("")
        status(f"=== Cliente: {nome} ===")
        try:
            res = executar(nome, sessao, status=status, aviso=aviso, hoje=hoje)
            eh_nada_novo = not res.arquivos_gerados and bool(res.pulados)
            clientes.append(
                ClienteResultado(nome, "nada_novo" if eh_nada_novo else "ok", resultado=res)
            )
        except PastaNaoEncontrada as e:
            status(f"[cliente não encontrado] {nome}")
            clientes.append(
                ClienteResultado(nome, "nao_encontrado", erro=str(e), sugestoes=e.sugestoes)
            )
        except PastaAmbigua as e:
            status(f"[cliente ambíguo] {nome}")
            clientes.append(ClienteResultado(nome, "ambiguo", erro=str(e), paths=e.paths))
        except CalculadoraError as e:
            # ContratoNaoEncontrado, EntradaInvalida, erros de parse/BACEN etc.
            status(f"[erro] {nome}: {e}")
            clientes.append(ClienteResultado(nome, "erro", erro=str(e)))

    resumo = {
        "total": len(clientes),
        "ok": sum(1 for c in clientes if c.status == "ok"),
        "nada_novo": sum(1 for c in clientes if c.status == "nada_novo"),
        "nao_encontrados": sum(1 for c in clientes if c.status in ("nao_encontrado", "ambiguo")),
        "erros": sum(1 for c in clientes if c.status == "erro"),
        "pulados_total": sum(len(c.resultado.pulados) for c in clientes if c.resultado),
    }
    status("")
    status(
        f"Batch done — {resumo['ok']} calculated · {resumo['nada_novo']} nothing-new · "
        f"{resumo['nao_encontrados']} not-found · {resumo['erros']} error(s)."
    )
    return ResultadoLote(clientes=clientes, resumo=resumo)


def _processar_pasta(
    service,
    sessao: SessaoAutenticada,
    pasta,
    *,
    forcar_contrato_nome: Optional[str],
    emit: StatusCallback,
    aviso: StatusCallback,
    hoje: date,
) -> ResultadoPipeline:
    """Processa UMA pasta (raiz ou subpasta). Lança ContratoNaoEncontrado se não
    houver contrato Crefaz (o orquestrador pula a pasta). Lança CalculoJaExiste se
    a pasta já tem cálculo — o orquestrador registra como pulado (não refaz)."""
    t0 = time.perf_counter()
    files_before = drive.contar_arquivos_na_pasta(service, pasta.id)
    emit(f"Items in folder (before run): {files_before}")

    calculo_existente = drive.buscar_calculo_existente(service, pasta.id)
    if calculo_existente:
        emit(
            f"[pulado] {pasta.nome_real}: já tem cálculo ({calculo_existente.name}, "
            f"modificado {calculo_existente.modified_time}) — não refeito."
        )
        raise CalculoJaExiste(pasta.nome_real, calculo_existente.name)

    emit("Locating Crefaz contract PDF...")
    contrato_arquivo = drive.localizar_contrato(
        service, pasta.id, forcar_nome=forcar_contrato_nome
    )
    emit(f"Contract file: {contrato_arquivo.name}")

    # v0.9.8: sequência de nomes derivada do prefixo do contrato.
    # Séries Temporais = contrato+1 · Cálculo PDF = contrato+2.
    # Contrato sem prefixo numérico → nomes legados (fallback nos helpers).
    seq_contrato = numero_prefixo(contrato_arquivo.name)
    nome_series = nome_series_temporais(seq_contrato)

    emit("Downloading and parsing contract...")
    pdf_bytes = drive.baixar_pdf(service, contrato_arquivo.id)
    dados_contrato = parser_contrato.parsear_contrato(pdf_bytes)
    emit(
        f"Contract parsed: note {dados_contrato.numero_cedula}, "
        f"term {dados_contrato.prazo} mo, rate {dados_contrato.taxa_mensal * 100:.2f}%"
    )

    parcelas = calculadora.parcelas_pagas(
        primeiro_vencimento=dados_contrato.primeiro_vencimento,
        prazo=dados_contrato.prazo,
        hoje=hoje,
    )
    quitado = calculadora.is_quitado(parcelas, dados_contrato.prazo)
    aba = calculadora.decidir_aba(dados_contrato.prazo, quitado)
    emit(
        f"Contract status: {'QUITADO (all installments due)' if quitado else 'ATIVO'} "
        f"| paid installments to date: {parcelas} | sheet: {aba}"
    )

    bacen_mes = dados_contrato.data_emissao.month
    bacen_ano = dados_contrato.data_emissao.year

    bacen_na_pasta = drive.localizar_bacen_na_pasta(service, pasta.id)
    bacen_file_id_subido: Optional[str] = None
    if bacen_na_pasta:
        emit(f"BACEN PDF in client folder: {bacen_na_pasta.name}")
        bacen_pdf_bytes = drive.baixar_pdf(service, bacen_na_pasta.id)
        bacen_origem = "pasta_cliente"
    else:
        emit(f"BACEN not in folder — fetching {bacen_mes:02d}-{bacen_ano} from central repo...")
        bacen_repo = drive.localizar_bacen_no_repositorio(service, bacen_mes, bacen_ano)
        bacen_pdf_bytes = drive.baixar_pdf(service, bacen_repo.id)
        bacen_origem = "serie_do_bacen"
        emit("Uploading BACEN copy into client folder...")
        bacen_file_id_subido, _ = drive.subir_ou_sobrescrever(
            service,
            pasta.id,
            nome_series,
            bacen_pdf_bytes,
            "application/pdf",
        )
        aviso(
            f"BACEN PDF was missing — copied «{nome_series}» "
            "from the central BACEN folder into this client folder."
        )

    taxa_bacen = parser_bacen.extrair_taxa_mes(
        parser_bacen._extrair_texto_pdf(bacen_pdf_bytes), bacen_mes, bacen_ano
    )
    emit(f"BACEN rate for {bacen_mes:02d}/{bacen_ano}: {taxa_bacen * 100:.2f}%")

    emit("Building filled workbook...")
    dados_planilha = DadosPlanilha(
        contrato=dados_contrato,
        taxa_bacen=taxa_bacen,
        parcelas_pagas=parcelas,
        data_calculo=hoje,
    )
    xlsx_bytes = gerar_xlsx(dados_planilha, quitado=quitado)

    nome_xlsx = nome_xlsx_saida(quitado)
    emit(f"Uploading {nome_xlsx}...")
    xlsx_id, xlsx_sobrescrito = drive.subir_ou_sobrescrever(
        service,
        pasta.id,
        nome_xlsx,
        xlsx_bytes,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    arquivos_capturas: list[ArquivoGerado] = []
    capturas_ok = True
    try:
        emit("Generating spreadsheet PDF and contract capture (imag.01)...")
        cap = gerar_capturas(
            xlsx_bytes,
            nome_aba=aba,
            incluir_png_pagina_inteira=False,
        )

        pdf_nome = nome_pdf(quitado, seq_contrato)
        emit(f"Uploading {pdf_nome}...")
        _, pdf_sobrescrito = drive.subir_ou_sobrescrever(
            service, pasta.id, pdf_nome, cap.pdf_bytes, "application/pdf"
        )
        arquivos_capturas.append(
            ArquivoGerado(pdf_nome, "sobrescrito" if pdf_sobrescrito else "novo")
        )
        emit("Spreadsheet PDF ready.")

        # imag.01.png — recorte do Item II do contrato Crefaz.
        # img02 (recorte da região PMT na planilha) foi removido em v0.6.9.
        conf_c = CAPTURA_IMG01_CONTRATO
        try:
            png_c = capturar_pagina_pdf(
                pdf_bytes,
                conf_c["marcador_regex"],
                NOME_IMAG_01,
                marcador_fim_regex=conf_c.get("marcador_fim_regex"),
                marcador_fim_inclusivo_regex=conf_c.get("marcador_fim_inclusivo_regex"),
                altura_fallback_ratio=conf_c.get("altura_fallback_ratio", 0.50),
            )
        except CapturasError as e:
            aviso(f"imag.01 (contract) failed: {e}")
            png_c = None
        if png_c is None:
            aviso("imag.01 skipped — Item II marker not found in contract PDF.")
            emit("[skipped] imag.01 — Item II marker not found.")
        else:
            _, sob_c = drive.subir_ou_sobrescrever(
                service, pasta.id, png_c.nome_arquivo, png_c.bytes_, "image/png"
            )
            arquivos_capturas.append(
                ArquivoGerado(png_c.nome_arquivo, "sobrescrito" if sob_c else "novo")
            )
            emit("imag.01 saved (contract Item II).")

        # imag.02.png — bloco INTEIRO "Parcela com Taxa Média e Expurgo de
        # Abusividades" (título + valores + derivação da fórmula PMT, como prova).
        # v0.9.3: recortado direto do PDF do Cálculo já renderizado (fiel à
        # planilha), em vez de re-render regional (que distorcia e gerava ##).
        emit("Generating spreadsheet capture (imag.02)...")
        try:
            png_r = recortar_bloco_pmt_pdf(cap.pdf_bytes, NOME_IMAG_02)
        except Exception as e:  # noqa: BLE001 — captura supplementar; nunca derruba o run
            aviso(f"imag.02 (PDF crop) failed: {e}")
            png_r = None
        if png_r is None:
            emit("[skipped] imag.02 — PARCELA block not found in calculation PDF.")
        else:
            _, sob_r = drive.subir_ou_sobrescrever(
                service, pasta.id, png_r.nome_arquivo, png_r.bytes_, "image/png"
            )
            arquivos_capturas.append(
                ArquivoGerado(png_r.nome_arquivo, "sobrescrito" if sob_r else "novo")
            )
            emit("imag.02 saved (Parcela com Taxa Média — bloco completo).")

        emit(f"Capture phase finished ({len(arquivos_capturas)} files).")
    except CapturasError as e:
        capturas_ok = False
        aviso(
            f"Captures skipped: {e}. XLSX is still valid. "
            "Install LibreOffice for automatic PDF/PNG generation."
        )
        emit(f"[skipped] Captures — {e}")

    arquivos: list[ArquivoGerado] = [
        ArquivoGerado(nome_xlsx, "sobrescrito" if xlsx_sobrescrito else "novo"),
    ]
    if bacen_origem == "serie_do_bacen":
        arquivos.append(ArquivoGerado(nome_series, "novo"))
    else:
        arquivos.append(ArquivoGerado(bacen_na_pasta.name, "mantido"))
    arquivos.extend(arquivos_capturas)

    # v0.6.9: 12 Log.txt deixou de ser salvo na pasta da cliente.
    # Audit trail vive na planilha central de runs (próximo bloco).

    duration = time.perf_counter() - t0
    files_after = drive.contar_arquivos_na_pasta(service, pasta.id)
    added, modified = _count_arquivos_por_status(arquivos)

    master_url = master_run_log_url()
    sheet_id = master_run_log_spreadsheet_id()
    tab_name = master_run_log_sheet_tab()
    row_appended = False
    if sheet_id:
        try:
            row = build_master_run_row(
                user_email=sessao.email,
                client_name=dados_contrato.nome_emitente,
                folder_url=drive.url_pasta(pasta.id),
                duration_sec=duration,
                files_before=files_before,
                files_after=files_after,
                files_added=added,
                files_modified=modified,
                cedula=str(dados_contrato.numero_cedula),
                term_months=dados_contrato.prazo,
                paid_installments=parcelas,
                rate_contract_pct=dados_contrato.taxa_mensal * 100,
                rate_bacen_pct=taxa_bacen * 100,
                bacen_ref=f"{bacen_mes:02d}/{bacen_ano}",
                bacen_source=bacen_origem,
                contract_pdf=contrato_arquivo.name,
                revcalc_version=__version__,
            )
            append_master_run_row(
                sessao.sheets_service(), sheet_id, tab_name, row
            )
            row_appended = True
            emit("Master run log: row appended (shared Google Sheet).")
        except Exception as e:
            logger.exception("Master run log append failed")
            aviso(f"Master run log failed: {e}")
            emit(f"[skipped] Master run log — {e}")
    else:
        emit(
            "[skipped] Master run log — REVCALC_MASTER_RUN_LOG_SPREADSHEET_ID not set"
        )

    summary_lines = ["=== Summary ==="]
    summary_lines.append(f"Executed by: {sessao.email}")
    if master_url:
        summary_lines.append(f"Master spreadsheet: {master_url}")
    summary_lines.extend(
        [
            f"Total duration: {duration:.1f}s",
            f"Items in folder: {files_before} → {files_after} (before → after)",
            f"Files added / overwritten (this run): {added} / {modified}",
            f"Capture pipeline: {'OK' if capturas_ok else 'partial or skipped'}",
            f"Master run log row: {'appended' if row_appended else 'skipped'}",
        ]
    )
    for line in summary_lines:
        emit(line)

    emit("Done.")

    return ResultadoPipeline(
        pasta_drive_path=pasta.path,
        pasta_drive_url=drive.url_pasta(pasta.id),
        xlsx_file_id=xlsx_id,
        log_file_id="",  # v0.6.9: log .txt deixou de ser salvo na pasta
        bacen_file_id=bacen_file_id_subido,
        arquivos_gerados=arquivos,
        master_run_log_url=master_url,
        master_run_log_row_appended=row_appended,
        executor_email=sessao.email,
        duration_sec=duration,
        files_before=files_before,
        files_after=files_after,
        files_added=added,
        files_modified=modified,
    )
