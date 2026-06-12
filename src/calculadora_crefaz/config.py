"""Constantes do pipeline — IDs do Drive, paths, regex, mapeamento de campos."""

import os
import re
import sys
from pathlib import Path

# ─── Drive ──────────────────────────────────────────────────────────────────

# Pasta-mãe "EMPRESTIMO DE ENERGIA" no Drive (layout do tenant)
PASTA_MAE_ID = os.environ.get("REVCALC_PASTA_MAE_ID", "1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN")

# Pasta "Série do Bacen" dentro de "EMPRESTIMO DE ENERGIA/03. MODELOS/"
PASTA_BACEN_ID = os.environ.get("REVCALC_PASTA_BACEN_ID", "1w8aWxOURJewINVPlyGKlitEE-EpStWUe")

# Subpastas de estado seguem o padrão "NN. NOME DO ESTADO"
REGEX_PASTA_ESTADO = re.compile(r"^\d{2}\.\s+")

# ─── OAuth ──────────────────────────────────────────────────────────────────

# Web: só `drive`. O `spreadsheets` (master run log v0.6.9) fica fora até
# habilitar Sheets API + setar REVCALC_MASTER_RUN_LOG_SPREADSHEET_ID — assim o
# consent já minted (drive-only) continua válido e não pede permissão a mais.
OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]
# Domínios autorizados a logar — externalizável via env REVCALC_DOMINIOS_PERMITIDOS.
_DOMINIOS_ENV = os.environ.get("REVCALC_DOMINIOS_PERMITIDOS", "").strip()
DOMINIOS_PERMITIDOS = (
    tuple(d.strip().lower() for d in _DOMINIOS_ENV.split(",") if d.strip())
    if _DOMINIOS_ENV
    else ("roseportaladvocacia.com.br", "adventurelabs.com.br")
)
KEYRING_SERVICE = "calculadora-crefaz"

# ─── Identificação de arquivos na pasta da cliente ──────────────────────────

# Padrões aceitos para o contrato Crefaz (case-insensitive)
REGEX_CONTRATO = [
    re.compile(r"^\d{2}\s+contrato\s+crefaz.*\.pdf$", re.IGNORECASE),
    re.compile(r"^contrato\s+crefaz.*\.pdf$", re.IGNORECASE),
]

# Prefixos auxiliares que NUNCA são contrato (excluir do match)
PREFIXOS_NAO_CONTRATO = (
    "01 procuração", "01 procuracao",
    "02 cnh", "02 declaração", "02 declaracao",
    "03 declaração", "03 declaracao", "03 id",
    "04 comprovante",
    "05 extrato",
    "06 declaração", "06 declaracao",
    "07 cpf",
    "08 pesquisa",
    "10 cálculo", "10 calculo",
    "11 series", "11 séries",
    "12 log",
    "contrato honorários", "contrato honorarios",
    "contrato isenção", "contrato isencao",
    "declaração de isenção", "declaracao de isencao",
    "declaração isenção", "declaracao isencao",
    "situação cpf", "situacao cpf",
    "kit procuração", "kit procuracao",
)

# BACEN na pasta da cliente
REGEX_BACEN_PASTA_CLIENTE = re.compile(
    r"^11\s+s[ée]ries\s+temporais.*\.pdf$", re.IGNORECASE
)

# BACEN em Série do Bacen segue padrão "MM-YYYY.pdf"
def nome_arquivo_bacen(mes: int, ano: int) -> str:
    return f"{mes:02d}-{ano}.pdf"

# Cópias do Drive (ex: "Cópia de XYZ.pdf") — ignorar
REGEX_COPIA = re.compile(r"^c[óo]pia\s+de\s+", re.IGNORECASE)

# Cálculo já existente (para dedup). Casa o nome legado ("10 Cálculo NOME.xlsx")
# e os nomes novos v0.9.0 exatos ("Calculo.xlsx" / "Calculo quitado.xlsx"), com/sem
# acento. NÃO casa "calculo qualquer.xlsx" (evita falso-positivo de dedup).
REGEX_CALCULO_EXISTENTE = re.compile(
    r"^(10\s+c[áa]lculo.*|c[áa]lculo( quitado)?)\.xlsx$", re.IGNORECASE
)

# ─── Parser do Contrato Crefaz ──────────────────────────────────────────────

# Marcadores do bloco Item II
# Marcadores do Item II — Crefaz emite em duas variantes:
#   - "II.EMPRÉSTIMO CONCEDIDO"  (sem espaço entre 'II.' e 'EMPRÉSTIMO') — PDFs antigos
#   - "II. EMPRÉSTIMO CONCEDIDO" (com espaço)                            — PDFs novos (2025+)
# Mesma coisa para o III. — usamos regex tolerante a partir de v0.6.9.
MARCADOR_ITEM_II_INICIO = re.compile(
    r"II\.\s*EMPR[ÉE]STIMO\s+CONCEDIDO", re.IGNORECASE
)
MARCADOR_ITEM_II_FIM = re.compile(
    r"III\.\s*CUSTO\s+EFETIVO\s+TOTAL", re.IGNORECASE
)

# Regex para campos do Item II (tolerância a espaços e quebras de linha)
REGEX_ITEM_II = {
    "data_emissao": re.compile(r"Data\s+de\s+Emiss[ãa]o:\s*(\d{2}/\d{2}/\d{4})"),
    "prazo": re.compile(r"Prazo:\s*(\d+)"),
    "primeiro_vencimento": re.compile(r"1[ºo]\s+Vencimento:\s*(\d{2}/\d{2}/\d{4})"),
    "ultimo_vencimento": re.compile(r"[ÚU]ltimo\s+Vencimento:\s*(\d{2}/\d{2}/\d{4})"),
    "valor_nominal": re.compile(r"Valor\s+Nominal:\s*R\$\s*([\d.,]+)"),
    "valor_emprestimo": re.compile(r"Valor\s+do\s+Empr[ée]stimo:\s*R\$\s*([\d.,]+)"),
    "valor_total_contratado": re.compile(r"Valor\s+Total\s+Contratado:\s*R\$\s*([\d.,]+)"),
    "valor_prestacao": re.compile(r"Valor\s+da\s+Presta[çc][ãa]o:\s*R\$\s*([\d.,]+)"),
    "taxa_mensal": re.compile(r"Taxa\s+de\s+Juros\s+Mensal:\s*([\d,]+)\s*%"),
    "taxa_anual": re.compile(r"Taxa\s+de\s+Juros\s+Anual:\s*([\d,]+)\s*%"),
    "tributos_iof": re.compile(r"Tributos/IOF:\s*R\$\s*([\d.,]+)"),
    "tarifas": re.compile(r"Tarifas:\s*R\$\s*([\d.,]+)"),
}

# Cabeçalho fora do Item II
# Crefaz emite o número da cédula em duas variantes:
#   - "Nº. 3314993" (ordinal + ponto)  — ex.: ERENI, ELIANE, ADRIANA
#   - "N.º 4195331" (ponto + ordinal)  — ex.: FABÍOLA, MARILEI, ROSA
# A classe `[\.\sº°o]{0,4}` aceita qualquer combinação até 4 chars,
# incluindo `o` minúsculo (resultado de NFKC sobre `º`).
# IGNORECASE cobre eventual minúscula no cabeçalho.
REGEX_CEDULA = re.compile(
    r"C[ÉE]DULA\s+DE\s+CR[ÉE]DITO\s+BANC[ÁA]RIO\s+N[\.\sº°o]{0,4}(\d+)",
    re.IGNORECASE,
)
REGEX_NOME_EMITENTE = re.compile(r"Nome:\s*(.+?)\s+CPF", re.DOTALL)

# ─── Parser BACEN ───────────────────────────────────────────────────────────

# Padrão das linhas do PDF BACEN: "{mes}/{ano}    {anual}    {mensal}"
MESES_PT = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
REGEX_LINHA_BACEN = re.compile(
    r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)/(\d{4})\s+([\d,]+)\s+([\d,]+)",
    re.IGNORECASE,
)

# ─── Template / Planilha ────────────────────────────────────────────────────

def _resolver_template_dir() -> Path:
    """Diretório `templates/` em dev e no bundle do PyInstaller.

    - Em dev (src/calculadora_crefaz/config.py): sobe 2 níveis até a raiz do projeto.
    - No bundle PyInstaller: usa sys._MEIPASS (diretório temporário extraído).
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "templates"
    return Path(__file__).resolve().parents[2] / "templates"


def _resolver_template_path() -> Path:
    return _resolver_template_dir() / "Calculo.xlsx"


TEMPLATE_PATH = _resolver_template_path()
# Template do fluxo QUITADO (contrato pago integralmente) — 4 abas PRICE 24/36/48/60.
# Cálculo retrospectivo (saldo zerado + montante cobrado a mais). v0.9.0.
TEMPLATE_QUITADO_PATH = _resolver_template_dir() / "Calculo.quitado.xlsx"

# Fluxo ATIVO: Crefaz só opera contratos de até 24 parcelas — uma única aba visual.
NOME_ABA_CALCULO = "CÁLCULO"

# Fluxo QUITADO: abas por faixa de prazo (até 60 parcelas — contratos históricos).
ABAS_QUITADO = ("PRICE 24X", "PRICE 36x", "PRICE 48x", "PRICE 60x")


def aba_para_prazo(prazo: int) -> str:
    if 1 <= prazo <= 24:
        return NOME_ABA_CALCULO
    raise ValueError(f"Prazo {prazo} fora do template (1-24).")


def aba_para_prazo_quitado(prazo: int) -> str:
    """Mapeia prazo → aba do template quitado (1–24→24X, 25–36→36x, 37–48→48x, 49–60→60x)."""
    if 1 <= prazo <= 24:
        return "PRICE 24X"
    if 25 <= prazo <= 36:
        return "PRICE 36x"
    if 37 <= prazo <= 48:
        return "PRICE 48x"
    if 49 <= prazo <= 60:
        return "PRICE 60x"
    raise ValueError(f"Prazo {prazo} fora do template quitado (1-60).")


# Células de input na aba CÁLCULO (sem offset — só uma aba existe agora).
# Mantém referências da PRICE 24X original; fórmulas internas continuam apontando
# pra $D$5, $I$15, $I$16 etc. (renomear aba não quebra fórmulas internas).
CELULAS_CALCULO = {
    "titulo": "C1",
    "data_pactuacao": "D3",
    "primeiro_vencimento": "D5",
    "valor_principal": "I7",
    "tac": "I9",
    "iof": "I13",
    "qtd_parcelas": "I15",
    "valor_prestacao": "I16",
    "taxa_pactuada": "I17",
    "taxa_bacen": "AP15",
    "parcelas_pagas": "BL8",
}

# Alias retrocompatível com código antigo que importava CELULAS_PRICE_24X.
CELULAS_PRICE_24X = CELULAS_CALCULO

# Offset de linha das abas quitado em relação à 24X (layout idêntico, +1 linha).
# 24X é alinhada à CÁLCULO (offset 0); 36x/48x/60x deslocam todas as linhas em +1.
_OFFSET_LINHA_ABA_QUITADO = {"PRICE 24X": 0, "PRICE 36x": 1, "PRICE 48x": 1, "PRICE 60x": 1}

_RE_COORD = re.compile(r"^([A-Z]+)(\d+)$")


def _desloca_coord(coord: str, offset: int) -> str:
    """Desloca a LINHA de uma coordenada A1 (ex.: 'I9' + 1 → 'I10'). Coluna intacta."""
    m = _RE_COORD.match(coord)
    if not m:
        raise ValueError(f"Coordenada inválida: {coord!r}")
    col, linha = m.group(1), int(m.group(2))
    return f"{col}{linha + offset}"


def celulas_para_aba(aba: str) -> dict[str, str]:
    """Mapa de células de input por aba.

    Aceita 'CÁLCULO' (ativo v0.6.0+) e as abas quitado 'PRICE 24X/36x/48x/60x'.
    As abas quitado compartilham o layout da 24X com offset de linha (+1 nas longas).
    """
    if aba == NOME_ABA_CALCULO:
        return dict(CELULAS_CALCULO)
    if aba in _OFFSET_LINHA_ABA_QUITADO:
        offset = _OFFSET_LINHA_ABA_QUITADO[aba]
        return {k: _desloca_coord(v, offset) for k, v in CELULAS_CALCULO.items()}
    raise ValueError(
        f"Aba desconhecida: {aba!r}. Esperado: {NOME_ABA_CALCULO!r} ou {ABAS_QUITADO}."
    )


# Aba "DADOS" (opcional no template) — só valores; abas PRICE visuais referenciam =DADOS!...
# Ativar no Excel: ver docs/HANDOFF_PLANILHA_DADOS_VS_VISUAL.md
NOME_ABA_DADOS = "DADOS"
CELULAS_DADOS = {
    "titulo": "B2",
    "data_emissao": "B3",
    "primeiro_vencimento": "B4",
    "ultimo_vencimento": "B5",
    "valor_principal": "B6",
    "tac": "B7",
    "iof": "B8",
    "qtd_parcelas": "B9",
    "valor_prestacao": "B10",
    "taxa_pactuada": "B11",
    "taxa_bacen": "B12",
    "parcelas_pagas": "B13",
    "data_calculo": "B14",
}


# ─── Capturas (v0.6.9) ───────────────────────────────────────────────────────
# Geradas na pasta da cliente:
#   - 13 Print CÁLCULO.pdf — impressão A4 paisagem da planilha completa.
#   - imag.01.png          — trecho "II. Empréstimo concedido" do PDF do contrato.
#
# img02 (recorte da região PMT na planilha) foi REMOVIDO em v0.6.9 — o recorte
# estava inconsistente entre clientes. Constantes mantidas como código morto
# para reativação futura quando o algoritmo for refeito (ROADMAP v0.7 → v0.8).
# Recorte "PARCELA COM TAXA MÉDIA E EXPURGO DE ABUSIVIDADES" (lado direito da planilha).
# Bloco de altura fixa ancorado no título (AD25 na 24X/CÁLCULO; +1 linha nas abas
# quitado longas 36x/48x/60x). v0.9.0: por aba, pois as quitado deslocam o layout.
REGIAO_IMG02_XLSX = "AD25:AZ73"  # default (CÁLCULO / PRICE 24X)
REGIOES_CAPTURA_XLSX = {"img02": REGIAO_IMG02_XLSX}

_REGIAO_IMG02_POR_ABA = {
    "CÁLCULO": "AD25:AZ73",
    "PRICE 24X": "AD25:AZ73",
    "PRICE 36x": "AD26:AZ74",
    "PRICE 48x": "AD26:AZ74",
    "PRICE 60x": "AD26:AZ74",
}


def regiao_img02_para_aba(aba: str) -> str:
    """Região do recorte imag.02 conforme a aba (offset de layout nas abas quitado)."""
    return _REGIAO_IMG02_POR_ABA.get(aba, REGIAO_IMG02_XLSX)

# imag.01 = bloco "EMPRÉSTIMO CONCEDIDO" inteiro (cabeçalho → C.E.T. TAXA ANUAL).
# Robusto a "II." ou "III." (o nº da seção varia entre layouts de contrato Crefaz).
# Fim = início da seção seguinte "DA LIBERAÇÃO DO CRÉDITO" (ancorado no texto, sem
# depender do nº), o que inclui as linhas C.E.T. MENSAL/ANUAL no recorte.
CAPTURA_IMG01_CONTRATO = {
    "marcador_regex": r"(?:II|III)\.?\s*EMPR[ÉE]STIMO\s+CONCEDIDO",
    "marcador_fim_regex": r"DA\s+LIBERA[ÇC][ÃA]O\s+DO\s+CR[ÉE]DITO",
    "altura_fallback_ratio": 0.45,
}

# ─── Saída ──────────────────────────────────────────────────────────────────

# v0.9.0: nome sem numeração/acento/nome do cliente ("salvar como Calculo").
# Variante quitado mantém o sufixo (espelha a convenção manual da Rose).
NOME_XLSX_SAIDA = "Calculo.xlsx"
NOME_XLSX_SAIDA_QUITADO = "Calculo quitado.xlsx"


def nome_xlsx_saida(quitado: bool = False) -> str:
    return NOME_XLSX_SAIDA_QUITADO if quitado else NOME_XLSX_SAIDA


NOME_BACEN_PASTA_CLIENTE = "11 Series Temporais.pdf"
NOME_IMAG_01 = "imag.01.png"
NOME_IMAG_02 = "imag.02.png"  # v0.7.0: recorte "Parcela c/ Taxa Média e Expurgo" da planilha
NOME_CONTRATO_PADRAO = "09 Contrato Crefaz.pdf"
# NOME_LOG removido em v0.6.9: log txt deixou de ser salvo na pasta da cliente.
# Audit trail vive na planilha central de runs (REVCALC_MASTER_RUN_LOG_SPREADSHEET_ID).


def _env_from_dotenv(name: str) -> str:
    """Lê env ou `.env` na raiz do projeto calculadora (mesmo critério que `auth`)."""
    val = os.environ.get(name)
    if val is not None:
        return val.strip()
    raiz = Path(__file__).resolve().parents[2]
    env_path = raiz / ".env"
    if env_path.exists():
        for linha in env_path.read_text().splitlines():
            linha = linha.strip()
            if linha.startswith(f"{name}="):
                return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def master_run_log_spreadsheet_id() -> str | None:
    """ID da planilha Google **central** (uma só para toda a equipa). Linhas via Sheets API."""
    v = _env_from_dotenv("REVCALC_MASTER_RUN_LOG_SPREADSHEET_ID")
    return v or None


def master_run_log_sheet_tab() -> str:
    """Nome da aba onde se faz append (default `Runs`)."""
    v = _env_from_dotenv("REVCALC_MASTER_RUN_LOG_TAB")
    return v or "Runs"


def master_run_log_url() -> str | None:
    """URL para abrir a planilha central; opcionalmente override em `REVCALC_MASTER_RUN_LOG_URL`."""
    v = _env_from_dotenv("REVCALC_MASTER_RUN_LOG_URL")
    if v:
        return v
    sid = master_run_log_spreadsheet_id()
    if sid:
        return f"https://docs.google.com/spreadsheets/d/{sid}/edit"
    return None

# ─── Validação ──────────────────────────────────────────────────────────────

TOLERANCIA_VALIDACAO_REAIS = 1.00
PRAZO_MINIMO = 1
PRAZO_MAXIMO = 24  # ATIVO: Crefaz não opera contratos com mais de 24 parcelas (v0.6.0)
PRAZO_MAXIMO_QUITADO = 60  # QUITADO: contratos históricos vão até 60 parcelas (v0.9.0)
