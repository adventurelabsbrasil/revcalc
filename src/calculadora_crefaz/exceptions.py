"""Exceptions tipadas — uma por modo de falha do pipeline."""

from __future__ import annotations


class CalculadoraError(Exception):
    """Base para erros da calculadora."""


class EntradaInvalida(CalculadoraError):
    """Nome do cliente vazio, único nome, ou caracteres inválidos."""


class AuthError(CalculadoraError):
    """Falha de autenticação OAuth ou domínio não autorizado."""


class PastaNaoEncontrada(CalculadoraError):
    """Cliente não encontrado em nenhum dos 2 níveis do Drive.

    Atributo `sugestoes`: lista de até 3 nomes próximos via fuzzy match.
    """

    def __init__(self, nome_buscado: str, sugestoes: list[str] | None = None):
        self.nome_buscado = nome_buscado
        self.sugestoes = sugestoes or []
        msg = f"Pasta de '{nome_buscado}' não encontrada."
        if self.sugestoes:
            msg += " Você quis dizer: " + ", ".join(self.sugestoes) + "?"
        super().__init__(msg)


class PastaAmbigua(CalculadoraError):
    """Nome casa em mais de uma pasta (raiz + estado, ou múltiplos estados)."""

    def __init__(self, nome_buscado: str, paths: list[str]):
        self.nome_buscado = nome_buscado
        self.paths = paths
        msg = f"Pasta de '{nome_buscado}' encontrada em múltiplos locais:\n  - " + "\n  - ".join(paths)
        super().__init__(msg)


class ContratoNaoEncontrado(CalculadoraError):
    """Nenhum PDF na pasta casa o padrão de Contrato Crefaz."""


class ContratoAmbiguo(CalculadoraError):
    """Múltiplos PDFs casam o padrão de contrato. Use --contrato '<nome>' para forçar."""

    def __init__(self, candidatos: list[str]):
        self.candidatos = candidatos
        msg = "Múltiplos contratos candidatos encontrados:\n  - " + "\n  - ".join(candidatos)
        msg += "\nUse --contrato '<nome>' para forçar."
        super().__init__(msg)


class ContratoParseError(CalculadoraError):
    """Item II do contrato não pôde ser extraído (campo ausente ou regex falhou)."""

    def __init__(self, campo: str, detalhe: str = ""):
        self.campo = campo
        msg = f"Falha ao extrair campo '{campo}' do contrato."
        if detalhe:
            msg += f" {detalhe}"
        super().__init__(msg)


class BacenNaoEncontrado(CalculadoraError):
    """PDF do BACEN ausente em ambos os locais (pasta cliente + Série do Bacen).

    Sugerir contactar o administrador do repositório BACEN/Drive.
    """


class BacenParseError(CalculadoraError):
    """Taxa do mês alvo não encontrada no PDF BACEN."""

    def __init__(self, mes: int, ano: int, detalhe: str = ""):
        self.mes = mes
        self.ano = ano
        msg = f"Taxa BACEN para {mes:02d}/{ano} não encontrada no PDF."
        if detalhe:
            msg += f" {detalhe}"
        super().__init__(msg)


class PrazoForaDoTemplate(CalculadoraError):
    """Prazo > 60 — template não suporta."""

    def __init__(self, prazo: int):
        self.prazo = prazo
        super().__init__(f"PRAZO FORA DO TEMPLATE: {prazo} parcelas (máximo suportado: 60).")


class BloqueioDedup(CalculadoraError):
    """Cálculo já existe e usuário não confirmou sobrescrita."""


class ValidacaoContratoWarning(Warning):
    """Soma Nominal + IOF + Tarifas diverge de Valor do Empréstimo. Não bloqueia."""
