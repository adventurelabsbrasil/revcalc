"""Gera capturas (PDF + PNG) do XLSX usando LibreOffice headless + pypdfium2.

Fluxo:
1. Recebe `xlsx_bytes`, salva em arquivo temporário.
2. Chama `soffice --headless --convert-to pdf` para gerar PDF (uma página por
   "página de impressão" da planilha). Aproveita `page_setup` do template
   (paisagem A4, fitToWidth=1, fitToHeight=1 → 1 página/aba esperada).
3. Rasteriza cada página do PDF como PNG via pypdfium2 (DPI configurável).
4. Devolve PDF + lista de PNGs em memória, prontos pra upload no Drive.

Não exige Excel instalado. Funciona em macOS/Linux/Windows com LibreOffice
disponível no PATH (`soffice` ou `libreoffice`).

Uso:
    from .capturas import gerar_capturas, CapturasGeradas

    cap = gerar_capturas(xlsx_bytes, dpi=150)
    cap.pdf_bytes        # PDF do XLSX inteiro (1 página/aba típico)
    cap.pngs             # list[CapturaPng] com (nome_arquivo, bytes, pagina)
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


# ─── Modelos ───────────────────────────────────────────────────────────────


@dataclass
class CapturaPng:
    """Uma captura PNG (uma página rasterizada do PDF)."""

    nome_arquivo: str  # ex: "13 Print PRICE 24X p1.png" — o pipeline define
    bytes_: bytes
    pagina: int  # 1-indexed
    largura_px: int
    altura_px: int


@dataclass
class CapturasGeradas:
    """Pacote completo de capturas pra um XLSX."""

    pdf_bytes: bytes
    pngs: list[CapturaPng] = field(default_factory=list)

    @property
    def num_paginas(self) -> int:
        return len(self.pngs)


# ─── Erros ──────────────────────────────────────────────────────────────────


class CapturasError(Exception):
    """Falha em qualquer etapa da geração de capturas."""


class LibreOfficeIndisponivel(CapturasError):
    """`soffice`/`libreoffice` não está no PATH."""


# ─── Helpers ────────────────────────────────────────────────────────────────


def _encontrar_soffice() -> str:
    """Resolve o binário do LibreOffice headless.

    Procura `soffice` (Linux/macOS) e `libreoffice` (alguns Linux).
    """
    for nome in ("soffice", "libreoffice"):
        caminho = shutil.which(nome)
        if caminho:
            return caminho
    raise LibreOfficeIndisponivel(
        "LibreOffice não encontrado no PATH. "
        "Instale: `brew install --cask libreoffice` (macOS), "
        "`apt install libreoffice` (Linux), ou baixe do site oficial (Windows)."
    )


def _xlsx_para_pdf(xlsx_bytes: bytes, *, timeout_s: int = 60) -> bytes:
    """Converte XLSX → PDF via LibreOffice headless. Retorna os bytes do PDF."""
    soffice = _encontrar_soffice()

    with tempfile.TemporaryDirectory(prefix="cap_crefaz_") as tmp:
        tmp_dir = Path(tmp)
        xlsx_path = tmp_dir / "in.xlsx"
        xlsx_path.write_bytes(xlsx_bytes)

        cmd = [
            soffice,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(tmp_dir),
            str(xlsx_path),
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise CapturasError(
                f"LibreOffice excedeu {timeout_s}s convertendo XLSX → PDF."
            )
        except subprocess.CalledProcessError as e:
            raise CapturasError(
                f"LibreOffice falhou (exit {e.returncode}): {e.stderr or e.stdout}"
            )

        logger.debug("soffice stdout: %s", res.stdout)
        pdf_path = tmp_dir / "in.pdf"
        if not pdf_path.exists():
            raise CapturasError(
                f"PDF esperado em {pdf_path} não foi gerado. soffice stdout: {res.stdout}"
            )
        return pdf_path.read_bytes()


def _pdf_para_pngs(pdf_bytes: bytes, *, dpi: int = 150) -> list[tuple[bytes, int, int]]:
    """Rasteriza PDF → lista de (png_bytes, largura_px, altura_px) — 1 entrada por página.

    Usa pypdfium2 (binding lightweight de PDFium, sem dependência de Poppler).
    """
    try:
        import pypdfium2 as pdfium
    except ImportError as e:
        raise CapturasError(
            f"pypdfium2 não instalado: {e}. Adicione ao requirements.txt."
        )

    import io
    from PIL import Image  # noqa: F401  # validar disponibilidade

    pdf = pdfium.PdfDocument(pdf_bytes)
    saidas: list[tuple[bytes, int, int]] = []
    scale = dpi / 72.0  # 72 DPI = referência interna do PDF
    for pagina in pdf:
        img = pagina.render(scale=scale).to_pil()
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        saidas.append((buf.getvalue(), img.size[0], img.size[1]))
    return saidas


# ─── API pública ────────────────────────────────────────────────────────────


def gerar_capturas(
    xlsx_bytes: bytes,
    *,
    dpi: int = 150,
    nome_aba: str = "CÁLCULO",
) -> CapturasGeradas:
    """Gera PDF + PNGs a partir de um XLSX em memória.

    Args:
        xlsx_bytes: bytes do XLSX (geralmente saída de `planilha.gerar_xlsx`).
        dpi: resolução das PNGs. 150 dá legibilidade sólida com peso ~300KB/página.
        nome_aba: nome da aba visual (usado pra compor nome dos PNGs).

    Returns:
        `CapturasGeradas` com `pdf_bytes` e `pngs` (uma entrada por página de impressão).

    Raises:
        LibreOfficeIndisponivel: soffice não está no PATH.
        CapturasError: outra falha durante a conversão.
    """
    pdf_bytes = _xlsx_para_pdf(xlsx_bytes)
    paginas_raw = _pdf_para_pngs(pdf_bytes, dpi=dpi)

    pngs: list[CapturaPng] = []
    total = len(paginas_raw)
    for i, (png_bytes, w, h) in enumerate(paginas_raw, start=1):
        if total == 1:
            sufixo = ""
        else:
            sufixo = f" p{i}de{total}"
        nome = f"13 Print {nome_aba}{sufixo}.png"
        pngs.append(
            CapturaPng(
                nome_arquivo=nome,
                bytes_=png_bytes,
                pagina=i,
                largura_px=w,
                altura_px=h,
            )
        )

    logger.info(
        "Capturas geradas: PDF (%d KB) + %d PNG(s) total %d KB",
        len(pdf_bytes) // 1024,
        len(pngs),
        sum(len(p.bytes_) for p in pngs) // 1024,
    )
    return CapturasGeradas(pdf_bytes=pdf_bytes, pngs=pngs)


def nome_pdf(nome_aba: str = "CÁLCULO") -> str:
    """Nome do PDF unificado salvo na pasta da cliente."""
    return f"13 Print {nome_aba}.pdf"


# ─── Capturas regionais (XLSX por range) ────────────────────────────────────


def _trim_whitespace(png_bytes: bytes, *, padding_px: int = 12) -> tuple[bytes, int, int]:
    """Remove margem branca ao redor do conteúdo no PNG.

    Usa `Image.getbbox()` invertendo branco→preto pra detectar o bounding box
    do conteúdo. Adiciona `padding_px` ao redor pra não cortar bordas finas.

    Returns:
        (png_bytes_trimmed, largura, altura)
    """
    import io
    from PIL import Image, ImageChops

    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    # Cria fundo branco da mesma dimensão e calcula diferença → não-branco
    bg = Image.new("RGB", img.size, (255, 255, 255))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox is None:
        # Imagem totalmente branca — devolve original
        return png_bytes, img.size[0], img.size[1]

    left, top, right, bottom = bbox
    left = max(0, left - padding_px)
    top = max(0, top - padding_px)
    right = min(img.size[0], right + padding_px)
    bottom = min(img.size[1], bottom + padding_px)
    cropped = img.crop((left, top, right, bottom))

    buf = io.BytesIO()
    cropped.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), cropped.size[0], cropped.size[1]


def _concat_pngs_verticalmente(
    paginas_raw: list[tuple[bytes, int, int]],
) -> tuple[bytes, int, int]:
    """Concatena páginas PNG verticalmente em uma única imagem."""
    import io
    from PIL import Image

    if not paginas_raw:
        raise CapturasError("Sem páginas para concatenar.")

    imagens = [Image.open(io.BytesIO(png)).convert("RGB") for png, _, _ in paginas_raw]
    largura = max(img.size[0] for img in imagens)
    altura = sum(img.size[1] for img in imagens)
    canvas = Image.new("RGB", (largura, altura), (255, 255, 255))
    y = 0
    for img in imagens:
        canvas.paste(img, (0, y))
        y += img.size[1]

    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue(), largura, altura


def gerar_capturas_regionais(
    xlsx_bytes: bytes,
    regioes: dict[str, str],
    *,
    nome_aba: str = "CÁLCULO",
    dpi: int = 150,
    trim: bool = True,
    on_status: Callable[[str], None] | None = None,
) -> list[CapturaPng]:
    """Gera 1 PNG por região, alterando print_area temporariamente.

    Para cada (label, range_xlsx) em `regioes`:
    1. Carrega XLSX em memória
    2. Define `ws.print_area = range_xlsx`, limpa header/footer
    3. Salva XLSX modificado
    4. Converte com soffice → PDF (1 página)
    5. Rasteriza pra PNG
    6. Aplica trim de whitespace (se `trim=True`)
    7. Nome final: "13 Print {label}.png"

    Args:
        xlsx_bytes: bytes do XLSX original (saída de `planilha.gerar_xlsx`).
        regioes: dict {label_curto: range_xlsx (ex: "C6:Y18")}.
        nome_aba: aba visual de onde extrair as regiões.
        dpi: resolução das PNGs.
        trim: corta whitespace ao redor após render.

    Returns:
        Lista de `CapturaPng`, uma por região.
    """
    from io import BytesIO
    from openpyxl import load_workbook

    from openpyxl.utils import column_index_from_string, range_boundaries

    saidas: list[CapturaPng] = []
    total = len(regioes)
    for idx, (label, range_xlsx) in enumerate(regioes.items(), start=1):
        if on_status:
            on_status(f"Captura regional {idx}/{total}: {label}...")
        # 1. Carrega + ajusta print_area
        wb = load_workbook(BytesIO(xlsx_bytes))
        if nome_aba not in wb.sheetnames:
            raise CapturasError(
                f"Aba {nome_aba!r} não encontrada no XLSX. Abas: {wb.sheetnames}"
            )
        ws = wb[nome_aba]
        ws.print_area = f"{nome_aba}!{range_xlsx}"
        # Orientação adaptativa: se a região é mais ALTA que LARGA, usa portrait;
        # senão landscape. Evita que blocos quadrados/altos sejam comprimidos demais.
        col_min, row_min, col_max, row_max = range_boundaries(range_xlsx)
        n_cols = col_max - col_min + 1
        n_rows = row_max - row_min + 1
        # heurística: cells visuais ~ width 8 chars (~80 pt) × height 15 pt → ratio largura/altura ~5
        # se n_rows / n_cols > ~0.5, vira mais alto que largo em proporção visual
        if n_rows / max(1, n_cols) > 0.5:
            ws.page_setup.orientation = "portrait"
        else:
            ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = 9  # A4

        # Força altura mínima das rows na região. Blocos do template têm rows
        # com 3pt usadas só pra mesclagem vertical de fórmulas expandidas;
        # sem ajuste, o conteúdo fica comprimido/invisível no PDF.
        # Heurística: se o range tem muitas linhas curtas (típico fórmula PMT
        # expandida com letras "n", "i", "1+i^n", etc.), bump pra 18pt;
        # senão, 12pt basta pra blocos de tabela compactos.
        rows_curtas = sum(
            1 for r in range(row_min, row_max + 1)
            if (ws.row_dimensions[r].height or 0) > 0
            and (ws.row_dimensions[r].height or 0) < 6
        )
        altura_min_pt = 18 if rows_curtas >= 5 else 12
        for r in range(row_min, row_max + 1):
            h = ws.row_dimensions[r].height
            if h is None or h < altura_min_pt:
                ws.row_dimensions[r].height = altura_min_pt
        # Blocos matemáticos longos: permitir múltiplas páginas e concatenar depois.
        bloco_longo = label in ("04 Conforme Pactuado", "05 Parcela Taxa Media")
        # Cabe em 1 página (default)
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 2 if bloco_longo else 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        # Limpa header/footer pra não aparecer "Cálculo de Ação Crefaz" / "Página 1 de 1"
        for hf_attr in ("oddHeader", "oddFooter", "evenHeader", "evenFooter"):
            hf = getattr(ws, hf_attr, None)
            if hf is not None:
                for align in ("left", "center", "right"):
                    section = getattr(hf, align, None)
                    if section is not None:
                        section.text = ""
        # Margens mínimas pra reduzir whitespace
        ws.page_margins.left = 0.1
        ws.page_margins.right = 0.1
        ws.page_margins.top = 0.1
        ws.page_margins.bottom = 0.1
        ws.page_margins.header = 0.0
        ws.page_margins.footer = 0.0
        wb.calculation.fullCalcOnLoad = True

        # 2. Salva e converte
        out = BytesIO()
        wb.save(out)
        xlsx_regional = out.getvalue()

        try:
            pdf_bytes = _xlsx_para_pdf(xlsx_regional)
            paginas_raw = _pdf_para_pngs(pdf_bytes, dpi=dpi)
        except CapturasError as e:
            logger.warning("Falha ao gerar região %s (%s): %s", label, range_xlsx, e)
            if on_status:
                on_status(f"Captura regional {idx}/{total} falhou: {label}.")
            continue

        if not paginas_raw:
            logger.warning("Região %s gerou 0 páginas — ignorada.", label)
            if on_status:
                on_status(f"Captura regional {idx}/{total} sem páginas: {label}.")
            continue

        # 3. Primeira página (default) ou concatenação vertical (blocos longos)
        if bloco_longo and len(paginas_raw) > 1:
            png_bytes, w, h = _concat_pngs_verticalmente(paginas_raw)
        else:
            png_bytes, w, h = paginas_raw[0]
        if trim:
            png_bytes, w, h = _trim_whitespace(png_bytes)
        nome = f"13 Print {label}.png"
        saidas.append(
            CapturaPng(
                nome_arquivo=nome,
                bytes_=png_bytes,
                pagina=1,
                largura_px=w,
                altura_px=h,
            )
        )
        logger.info(
            "Região %s capturada: %s (%dx%d, %d KB)",
            label, nome, w, h, len(png_bytes) // 1024,
        )
        if on_status:
            on_status(f"Captura regional {idx}/{total} concluída: {label}.")

    return saidas


# ─── Capturas de páginas de PDFs ────────────────────────────────────────────


def capturar_pagina_pdf(
    pdf_bytes: bytes,
    marcador_regex: str,
    nome_arquivo: str,
    *,
    dpi: int = 150,
    marcador_fim_regex: str | None = None,
    altura_fallback_ratio: float = 0.50,
) -> CapturaPng | None:
    """Captura como PNG a primeira página do PDF que contém o marcador.

    Args:
        pdf_bytes: bytes do PDF (contrato Crefaz ou Séries BACEN).
        marcador_regex: regex (re.IGNORECASE) buscado no texto extraído.
        nome_arquivo: nome do PNG resultante (ex: "13 Print 07 Item II do Contrato.png").
        dpi: resolução do PNG.

    Returns:
        `CapturaPng` da primeira página que casa, ou None se não encontrar.
    """
    import io
    import re
    try:
        import pypdfium2 as pdfium
    except ImportError as e:
        raise CapturasError(f"pypdfium2 não instalado: {e}") from e
    try:
        import pdfplumber
    except ImportError as e:
        raise CapturasError(f"pdfplumber não instalado: {e}") from e

    pattern = re.compile(marcador_regex, re.IGNORECASE)

    # Procura página por página + localização vertical dos marcadores
    pagina_alvo: int | None = None  # 0-indexed
    y_inicio: float | None = None
    y_fim: float | None = None
    fim_pattern = re.compile(marcador_fim_regex, re.IGNORECASE) if marcador_fim_regex else None

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            texto = page.extract_text() or ""
            if pattern.search(texto):
                pagina_alvo = i
                try:
                    words = page.extract_words() or []
                except Exception:
                    words = []
                tops = [w["top"] for w in words if pattern.search(w.get("text", ""))]
                if tops:
                    y_inicio = max(0.0, min(tops) - 10.0)
                if fim_pattern:
                    bottoms = [w["bottom"] for w in words if fim_pattern.search(w.get("text", ""))]
                    if bottoms:
                        y_fim = max(bottoms) + 12.0
                break

    if pagina_alvo is None:
        logger.warning(
            "Marcador %r não encontrado no PDF — captura ignorada (%s).",
            marcador_regex, nome_arquivo,
        )
        return None

    # Renderiza a página alvo (apenas bloco, não página inteira)
    pdf = pdfium.PdfDocument(pdf_bytes)
    page = pdf[pagina_alvo]
    page_h = float(page.get_height())
    if y_inicio is None:
        y_inicio = 0.0
    if y_fim is None or y_fim <= y_inicio:
        y_fim = min(page_h, y_inicio + page_h * altura_fallback_ratio)
    y_inicio = max(0.0, min(y_inicio, page_h))
    y_fim = max(y_inicio + 10.0, min(y_fim, page_h))

    img = page.render(
        scale=dpi / 72.0,
        crop=(0.0, y_inicio, float(page.get_width()), y_fim),
    ).to_pil()
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    png_bytes = buf.getvalue()

    logger.info(
        "PDF capturado: %s (página %d, %dx%d, %d KB)",
        nome_arquivo, pagina_alvo + 1, img.size[0], img.size[1], len(png_bytes) // 1024,
    )
    return CapturaPng(
        nome_arquivo=nome_arquivo,
        bytes_=png_bytes,
        pagina=pagina_alvo + 1,
        largura_px=img.size[0],
        altura_px=img.size[1],
    )
