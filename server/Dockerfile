# Backend web da Calculadora Crefaz.
# Roda da árvore-fonte (PYTHONPATH=/app/src) em vez de `pip install` do pacote,
# porque config._resolver_template_path() resolve o template como
# parents[2]/templates/Calculo.xlsx — só funciona com o layout do repo intacto.
#
# Build (a partir da RAIZ do repo):
#   docker build -f server/Dockerfile -t revcalc-api:latest .
FROM python:3.12-slim

# LibreOffice (xlsx→pdf nas capturas) + fontes p/ PNG sem tofu. curl p/ healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-calc \
        fonts-dejavu \
        fonts-liberation \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY server/requirements-web.txt /app/server/requirements-web.txt
RUN pip install --no-cache-dir -r /app/server/requirements-web.txt

# Engine + servidor + template
COPY src/ /app/src/
COPY server/ /app/server/
COPY templates/ /app/templates/

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    TOKEN_STORE_PATH=/data/tokens \
    HOME=/home/revcalc

# Usuário não-root + volume do token store
RUN useradd -m -u 10001 revcalc \
    && mkdir -p /data/tokens \
    && chown -R revcalc:revcalc /data /home/revcalc
USER revcalc

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

# 1 worker: o registry de runs + filas SSE são em-processo (single-firm).
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
