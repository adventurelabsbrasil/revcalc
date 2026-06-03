"""Backend web da Calculadora Crefaz (FastAPI).

Embrulha o pipeline desktop (pacote calculadora_crefaz) num serviço HTTP:
OAuth web server-side, execução do pipeline em thread e progresso ao vivo via SSE.
Roda como container (precisa de LibreOffice no PATH para as capturas).
"""
