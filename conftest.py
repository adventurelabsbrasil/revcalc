"""Add src/ ao sys.path para os testes — evita precisar de PYTHONPATH=src."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Env vars dummy para importar `server.app` (create_app → get_settings exige OAuth
# configurado). setdefault → não sobrescreve env real se já estiver definido.
for _k, _v in {
    "GOOGLE_OAUTH_CLIENT_ID": "test-client-id",
    "GOOGLE_OAUTH_CLIENT_SECRET": "test-client-secret",
    "OAUTH_REDIRECT_URI": "https://revcalc-api.example/api/auth/callback",
    "FRONTEND_ORIGIN": "https://revcalc.example",
    "SESSION_SECRET": "test-session-secret",
}.items():
    os.environ.setdefault(_k, _v)
