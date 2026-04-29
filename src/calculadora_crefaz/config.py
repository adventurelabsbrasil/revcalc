"""Constantes do pipeline — IDs do Drive, paths, regex, mapeamento de campos."""

import re
import sys
from pathlib import Path

# ─── Drive ──────────────────────────────────────────────────────────────────

# Pasta-mãe "EMPRESTIMO DE ENERGIA" no Drive da Rose
PASTA_MAE_ID = "1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN"

# Pasta "Série do Bacen" dentro de "EMPRESTIMO DE ENERGIA/03. MODELOS/"
PASTA_BACEN_ID = "1w8aWxOURJewINVPlyGKlitEE-EpStWUe"

# Subpastas de estado seguem o padrão "NN. NOME DO ESTADO"
REGEX_PASTA_ESTADO = re.compile(r"^\d{2}\.\s+")

# ─── OAuth ──────────────────────────────────────────────────────────────────

OAUTH_SCOPES = ["https://www.googleapis.com/auth/drive"]
DOMINIOS_PERMITIDOS = ("roseportaladvocacia.com.br", "adventurelabs.com.br")
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

# Cálculo já existente (para dedup)
REGEX_CALCULO_EXISTENTE = re.compile(r"^10\s+c[áa]lculo.*\.xlsx$", re.IGNORECASE)

# ─── Parser do Contrato Crefaz ──────────────────────────────────────────────

# Marcadores do bloco Item II
MARCADOR_ITEM_II_INICIO = "II.EMPRÉSTIMO CONCEDIDO"
MARCADOR_ITEM_II_FIM = "III.CUSTO EFETIVO TOTAL"

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
REGEX_CEDULA = re.compile(r"C[ÉE]DULA\s+DE\s+CR[ÉE]DITO\s+BANC[ÁA]RIO\s+N\.?[ºo°]?\s*(\d+)")
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

def _resolver_template_path() -> Path:
    """Resolve TEMPLATE_PATH em dev e no bundle do PyInstaller.

    - Em dev (src/calculadora_crefaz/config.py): sobe 2 níveis até a raiz do projeto.
    - No bundle PyInstaller: usa sys._MEIPASS (diretório temporário extraído).
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "templates" / "Calculo.xlsx"
    return Path(__file__).resolve().parents[2] / "templates" / "Calculo.xlsx"


TEMPLATE_PATH = _resolver_template_path()

# Crefaz só opera contratos de até 24 parcelas — uma única aba visual.
NOME_ABA_CALCULO = "CÁLCULO"


def aba_para_prazo(prazo: int) -> str:
    if 1 <= prazo <= 24:
        return NOME_ABA_CALCULO
    raise ValueError(f"Prazo {prazo} fora do template (1-24).")


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


def celulas_para_aba(aba: str) -> dict[str, str]:
    """Aceita 'CÁLCULO' (v0.6.0+) e 'PRICE 24X' (legacy preDADOS) — mesmo mapa."""
    if aba in (NOME_ABA_CALCULO, "PRICE 24X"):
        return dict(CELULAS_CALCULO)
    raise ValueError(
        f"Aba desconhecida: {aba!r}. Esperado: {NOME_ABA_CALCULO!r} ou 'PRICE 24X'."
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


# ─── Capturas regionais — escopo v0.6.0 ────────────────────────────────────

# Ranges XLSX dos 6 blocos individuais da aba CÁLCULO.
# Cada região vira 1 PNG separado na pasta da cliente, prefixado por "13 Print NN".
# Mapeamento auditado em 2026-04-29 contra `templates/Calculo.xlsx` v0.6.0.
REGIOES_CALCULO = {
    "01 Dados do Contrato":      "C6:Y18",   # bloco esquerdo top — header azul + 12 valores
    "02 Valores Recalculados":   "AD6:AZ19", # bloco centro top — taxa BACEN + diferenças
    "03 Saldo Recalculado":      "BE6:CB19", # bloco direito top — saldo + sub-quadro controvertido
    "04 Conforme Pactuado":      "C25:Y49",  # bloco esquerdo bottom — fórmula PMT taxa contrato
    "05 Parcela Taxa Media":     "AD25:AZ49",# bloco centro bottom — fórmula PMT taxa BACEN
    "06 Percentual + Indevidas": "BE29:CB31",# 2 caixinhas lado a lado: % superior à média + total indevidas (incl. borda inferior)
}

# Capturas extraídas dos PDFs já presentes na pasta da cliente.
# Cada entrada: (nome_png, regex_marker, quantas_paginas_apos_o_marker)
CAPTURAS_PDF = {
    "07 Item II do Contrato": {
        "tipo": "contrato",  # PDF baixado do Drive como `contrato_arquivo`
        "marcador_regex": r"II\.?\s*EMPR[ÉE]STIMO\s+CONCEDIDO",
    },
    "08 Series BACEN": {
        "tipo": "bacen",  # PDF BACEN (já em memória durante o pipeline)
        "marcador_regex": r"S[ée]ries?\s+selecionadas?",
    },
}

# ─── Saída ──────────────────────────────────────────────────────────────────

NOME_XLSX_SAIDA = "10 Cálculo {nome}.xlsx"
NOME_BACEN_PASTA_CLIENTE = "11 Series Temporais.pdf"
NOME_LOG = "12 Log.txt"
NOME_CONTRATO_PADRAO = "09 Contrato Crefaz.pdf"

# ─── Validação ──────────────────────────────────────────────────────────────

TOLERANCIA_VALIDACAO_REAIS = 1.00
PRAZO_MINIMO = 1
PRAZO_MAXIMO = 24  # Crefaz não opera contratos com mais de 24 parcelas (v0.6.0)
