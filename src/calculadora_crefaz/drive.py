"""Integração com Google Drive: busca em 2 níveis, dedup, download, upload."""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from rapidfuzz import process as fuzz_process
from unidecode import unidecode

from .config import (
    NOME_BACEN_PASTA_CLIENTE,
    PASTA_BACEN_ID,
    PASTA_MAE_ID,
    PREFIXOS_NAO_CONTRATO,
    REGEX_BACEN_PASTA_CLIENTE,
    REGEX_CALCULO_EXISTENTE,
    REGEX_CONTRATO,
    REGEX_COPIA,
    REGEX_PASTA_ESTADO,
    nome_arquivo_bacen,
)
from .exceptions import (
    BacenNaoEncontrado,
    ContratoNaoEncontrado,
    PastaAmbigua,
    PastaNaoEncontrada,
)

logger = logging.getLogger(__name__)

# Nome deve conter explicitamente "Contrato Crefaz" (evita outro tipo de contrato na pasta).
REGEX_CONTEM_CONTRATO_CREFAZ = re.compile(r"contrato\s+crefaz", re.IGNORECASE)

MIME_FOLDER = "application/vnd.google-apps.folder"
MIME_PDF = "application/pdf"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_TXT = "text/plain"


# ─── Modelos ────────────────────────────────────────────────────────────────


@dataclass
class ArquivoDrive:
    id: str
    name: str
    mime_type: str
    modified_time: Optional[str] = None
    parent_path: str = ""


@dataclass
class PastaCliente:
    id: str
    nome_real: str  # nome como aparece no Drive
    path: str  # ex: "EMPRESTIMO DE ENERGIA/10. RIO GRANDE DO SUL/MARLI..."


# ─── Helpers de normalização ────────────────────────────────────────────────


def _norm(s: str) -> str:
    """Normaliza pra matching: minúsculas, sem acentos, espaços colapsados."""
    return " ".join(unidecode(s).lower().split())


def _nome_combina(buscado: str, candidato: str) -> bool:
    return _norm(buscado) == _norm(candidato)


# ─── Listagem (camada fina sobre Drive API) ─────────────────────────────────


def _listar_filhos(service, parent_id: str, mime_type: Optional[str] = None) -> list[dict[str, Any]]:
    """Lista os filhos diretos de uma pasta. Pagina até esgotar."""
    q_parts = [f"'{parent_id}' in parents", "trashed = false"]
    if mime_type:
        q_parts.append(f"mimeType = '{mime_type}'")
    q = " and ".join(q_parts)

    results: list[dict[str, Any]] = []
    page_token = None
    while True:
        resp = service.files().list(
            q=q,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
            pageToken=page_token,
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


# ─── Busca da pasta da cliente em 2 níveis ──────────────────────────────────


def localizar_pasta_cliente(service, nome_buscado: str) -> PastaCliente:
    """Busca em 2 níveis: raiz de EMPRESTIMO DE ENERGIA, depois subpastas de estado.

    Lança PastaNaoEncontrada (com sugestões fuzzy) ou PastaAmbigua.
    """
    # ─── Nível 1: raiz ──────────────────────────────────────────────────────
    pastas_raiz = _listar_filhos(service, PASTA_MAE_ID, MIME_FOLDER)

    # Separar pastas de estado (que matcham regex) das demais (clientes em legado)
    pastas_estado = [p for p in pastas_raiz if REGEX_PASTA_ESTADO.match(p["name"])]
    pastas_cliente_raiz = [
        p for p in pastas_raiz if not REGEX_PASTA_ESTADO.match(p["name"])
    ]

    matches: list[PastaCliente] = []

    for p in pastas_cliente_raiz:
        if _nome_combina(nome_buscado, p["name"]):
            matches.append(
                PastaCliente(
                    id=p["id"],
                    nome_real=p["name"],
                    path=f"EMPRESTIMO DE ENERGIA/{p['name']}",
                )
            )

    # ─── Nível 2: dentro de cada estado ─────────────────────────────────────
    for estado in pastas_estado:
        clientes_estado = _listar_filhos(service, estado["id"], MIME_FOLDER)
        for c in clientes_estado:
            if _nome_combina(nome_buscado, c["name"]):
                matches.append(
                    PastaCliente(
                        id=c["id"],
                        nome_real=c["name"],
                        path=f"EMPRESTIMO DE ENERGIA/{estado['name']}/{c['name']}",
                    )
                )

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        raise PastaAmbigua(nome_buscado, [m.path for m in matches])

    # ─── 0 matches: gerar sugestões via fuzzy ───────────────────────────────
    candidatos: list[str] = [p["name"] for p in pastas_cliente_raiz]
    for estado in pastas_estado:
        clientes_estado = _listar_filhos(service, estado["id"], MIME_FOLDER)
        candidatos.extend(c["name"] for c in clientes_estado)

    norm_para_real: dict[str, str] = {_norm(c): c for c in candidatos}
    matches_fuzzy = fuzz_process.extract(_norm(nome_buscado), list(norm_para_real.keys()), limit=3)
    sugestoes = [norm_para_real[m[0]] for m in matches_fuzzy if m[1] > 60]

    raise PastaNaoEncontrada(nome_buscado, sugestoes)


def listar_subpastas(service, pasta: PastaCliente) -> list[PastaCliente]:
    """Subpastas DIRETAS (1 nível) da pasta da cliente — cada uma candidata a um
    contrato próprio (ex.: VLADIMIR: ativo na raiz + quitados em subpastas). v0.9.4."""
    filhos = _listar_filhos(service, pasta.id, MIME_FOLDER)
    return [
        PastaCliente(id=f["id"], nome_real=f["name"], path=f"{pasta.path}/{f['name']}")
        for f in filhos
    ]


# ─── Identificação de arquivos ──────────────────────────────────────────────


def _prioridade_contrato_crefaz(nome: str) -> tuple:
    """Ordem de preferência menor = melhor. Empate final pelo nome (estável).

    1) ``NN Contrato Crefaz.pdf`` — só o padrão numerado, sem texto extra
    2) ``NN Contrato Crefaz <resto>.pdf`` — numerado com sufixo (ex.: nome do cliente)
    3) ``Contrato Crefaz.pdf`` — sem número
    4) ``Contrato Crefaz <resto>.pdf`` — não numerado com sufixo (ex.: antigo)
    """
    nl = nome.strip().lower()
    m = re.match(r"^(\d{2})\s+contrato\s+crefaz\.pdf$", nl)
    if m:
        return (0, int(m.group(1)), nome)
    m = re.match(r"^(\d{2})\s+contrato\s+crefaz\s+(.+)\.pdf$", nl)
    if m:
        return (1, int(m.group(1)), nome)
    if nl == "contrato crefaz.pdf":
        return (2, 0, nome)
    m = re.match(r"^contrato\s+crefaz\s+(.+)\.pdf$", nl)
    if m:
        return (3, 0, nome)
    return (4, 0, nome)


def _e_contrato(nome: str) -> bool:
    """True se o nome bate algum padrão de contrato Crefaz e não é prefixo auxiliar."""
    nome_lower = nome.lower()
    if REGEX_COPIA.match(nome):
        return False
    for prefixo in PREFIXOS_NAO_CONTRATO:
        if nome_lower.startswith(prefixo):
            return False
    if not REGEX_CONTEM_CONTRATO_CREFAZ.search(nome):
        return False
    return any(rx.match(nome) for rx in REGEX_CONTRATO)


def _e_bacen_pasta_cliente(nome: str) -> bool:
    if REGEX_COPIA.match(nome):
        return False
    return bool(REGEX_BACEN_PASTA_CLIENTE.match(nome))


def _e_calculo_existente(nome: str) -> bool:
    return bool(REGEX_CALCULO_EXISTENTE.match(nome))


def localizar_contrato(service, pasta_id: str, forcar_nome: Optional[str] = None) -> ArquivoDrive:
    """Encontra o PDF do contrato Crefaz na pasta.

    O nome deve conter **Contrato Crefaz** (duas palavras). Se houver vários,
    aplica prioridade: ``NN Contrato Crefaz.pdf`` (sem sufixo) > numerado com
    sufixo > ``Contrato Crefaz.pdf`` > outros.

    `forcar_nome`: se passado, usa exatamente esse arquivo (match exato do nome)
    e ignora a heurística.
    """
    arquivos = _listar_filhos(service, pasta_id, MIME_PDF)

    if forcar_nome:
        for a in arquivos:
            if a["name"] == forcar_nome:
                return ArquivoDrive(id=a["id"], name=a["name"], mime_type=a["mimeType"])
        raise ContratoNaoEncontrado(
            f"Arquivo forçado '{forcar_nome}' não encontrado na pasta."
        )

    candidatos = [a for a in arquivos if _e_contrato(a["name"])]

    if not candidatos:
        raise ContratoNaoEncontrado(
            "Nenhum PDF na pasta casa o padrão de contrato Crefaz. "
            "Renomeie o contrato para '09 Contrato Crefaz.pdf' antes de processar."
        )

    candidatos.sort(key=lambda a: _prioridade_contrato_crefaz(a["name"]))
    escolhido = candidatos[0]
    if len(candidatos) > 1:
        outros = [a["name"] for a in candidatos[1:]]
        logger.warning(
            "Vários PDFs 'Contrato Crefaz' na pasta — usando '%s' (prioridade sobre: %s)",
            escolhido["name"],
            outros,
        )

    return ArquivoDrive(
        id=escolhido["id"],
        name=escolhido["name"],
        mime_type=escolhido["mimeType"],
    )


def localizar_bacen_na_pasta(service, pasta_id: str) -> Optional[ArquivoDrive]:
    """Procura `11 Series Temporais.pdf` na pasta da cliente. Retorna None se não existe."""
    arquivos = _listar_filhos(service, pasta_id, MIME_PDF)
    for a in arquivos:
        if _e_bacen_pasta_cliente(a["name"]):
            return ArquivoDrive(id=a["id"], name=a["name"], mime_type=a["mimeType"])
    return None


def localizar_bacen_no_repositorio(service, mes: int, ano: int) -> ArquivoDrive:
    """Procura `MM-YYYY.pdf` na pasta Série do Bacen.

    Lança BacenNaoEncontrado se não existir nem na pasta cliente nem aqui.
    """
    arquivos = _listar_filhos(service, PASTA_BACEN_ID, MIME_PDF)
    nome_alvo = nome_arquivo_bacen(mes, ano)
    for a in arquivos:
        if REGEX_COPIA.match(a["name"]):
            continue
        if a["name"] == nome_alvo:
            return ArquivoDrive(id=a["id"], name=a["name"], mime_type=a["mimeType"])
    raise BacenNaoEncontrado(
        f"PDF BACEN '{nome_alvo}' não encontrado na pasta Série do Bacen "
        "e nem na pasta da operação. Peça ao administrador do Drive para disponibilizar o PDF BACEN desse mês."
    )


def buscar_calculo_existente(service, pasta_id: str) -> Optional[ArquivoDrive]:
    """Verifica se já existe `10 Cálculo*.xlsx` na pasta (para dedup)."""
    q = (
        f"'{pasta_id}' in parents and trashed = false and "
        f"mimeType = '{MIME_XLSX}'"
    )
    resp = service.files().list(
        q=q,
        fields="files(id, name, modifiedTime)",
        pageSize=100,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    for a in resp.get("files", []):
        if _e_calculo_existente(a["name"]):
            return ArquivoDrive(
                id=a["id"],
                name=a["name"],
                mime_type=MIME_XLSX,
                modified_time=a.get("modifiedTime"),
            )
    return None


def buscar_arquivo_por_nome(service, pasta_id: str, nome_alvo: str) -> Optional[ArquivoDrive]:
    """Procura um arquivo com nome exato dentro da pasta (qualquer mime)."""
    arquivos = _listar_filhos(service, pasta_id)
    for a in arquivos:
        if a["name"] == nome_alvo:
            return ArquivoDrive(
                id=a["id"],
                name=a["name"],
                mime_type=a["mimeType"],
                modified_time=a.get("modifiedTime"),
            )
    return None


# ─── Download / Upload ──────────────────────────────────────────────────────


def baixar_pdf(service, file_id: str) -> bytes:
    """Baixa o conteúdo de um arquivo do Drive em memória."""
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def subir_arquivo(
    service,
    pasta_id: str,
    nome: str,
    conteudo: bytes,
    mime_type: str,
    sobrescrever_id: Optional[str] = None,
) -> str:
    """Faz upload de bytes para a pasta. Retorna o file_id.

    Se `sobrescrever_id` for passado, faz update (mantém o mesmo file_id).
    """
    media = MediaIoBaseUpload(io.BytesIO(conteudo), mimetype=mime_type, resumable=False)

    if sobrescrever_id:
        return service.files().update(
            fileId=sobrescrever_id,
            media_body=media,
            supportsAllDrives=True,
        ).execute()["id"]

    return service.files().create(
        body={"name": nome, "parents": [pasta_id]},
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()["id"]


def subir_ou_sobrescrever(
    service,
    pasta_id: str,
    nome: str,
    conteudo: bytes,
    mime_type: str,
) -> tuple[str, bool]:
    """Sobrescreve se existir arquivo com o mesmo nome na pasta; senão cria.

    Retorna (file_id, foi_sobrescrito).
    """
    existente = buscar_arquivo_por_nome(service, pasta_id, nome)
    if existente:
        fid = subir_arquivo(
            service, pasta_id, nome, conteudo, mime_type, sobrescrever_id=existente.id
        )
        return fid, True
    fid = subir_arquivo(service, pasta_id, nome, conteudo, mime_type)
    return fid, False


def url_pasta(pasta_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{pasta_id}"


def url_arquivo(service, file_id: str) -> str:
    """Link webView do arquivo no Drive (planilhas abrem no Sheets)."""
    meta = (
        service.files()
        .get(fileId=file_id, fields="webViewLink,id", supportsAllDrives=True)
        .execute()
    )
    return meta.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"


def contar_arquivos_na_pasta(service, pasta_id: str) -> int:
    """Total de itens diretos na pasta (arquivos + subpastas), não recursivo."""
    return len(_listar_filhos(service, pasta_id))
