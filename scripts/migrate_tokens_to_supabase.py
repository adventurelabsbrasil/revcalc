#!/usr/bin/env python3
"""One-off: migra o token store de disco → Supabase (backend "supabase").

Lê os `<sha256(email)>.enc` de TOKEN_STORE_PATH e faz UPSERT em
public.revcalc_oauth_tokens. O blob JÁ é ciphertext Fernet — NÃO decripta, só move
os bytes (o email_hash é o próprio nome do arquivo). Idempotente (merge-duplicates).

Rodar UMA vez, no host que tem os tokens (ex.: xeon), dentro do container:
    docker exec revcalc-api python scripts/migrate_tokens_to_supabase.py
Exige SUPABASE_URL + SUPABASE_ANON_KEY no ambiente (o .env do container já tem).
Se pulado, os usuários apenas re-autenticam 1x — sem perda de dado.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root no path pra importar `server.*` quando chamado de scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from server.settings import get_settings  # noqa: E402


def main() -> int:
    s = get_settings()
    if not (s.supabase_url and s.supabase_anon_key):
        print("ERRO: SUPABASE_URL/SUPABASE_ANON_KEY ausentes no ambiente.", file=sys.stderr)
        return 1

    d: Path = s.token_store_path
    if not d.exists():
        print(f"Nada a migrar: {d} não existe.")
        return 0

    arquivos = sorted(d.glob("*.enc"))
    if not arquivos:
        print(f"Nada a migrar: sem .enc em {d}.")
        return 0

    url = f"{s.supabase_url}/rest/v1/{s.oauth_table}"
    headers = {
        "apikey": s.supabase_anon_key,
        "Authorization": f"Bearer {s.supabase_anon_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    now = datetime.now(timezone.utc).isoformat()

    ok, falhou = 0, 0
    with httpx.Client(timeout=15.0) as client:
        for f in arquivos:
            email_hash = f.stem  # o nome do arquivo já é sha256(email)
            row = {
                "email_hash": email_hash,
                "encrypted_creds": f.read_bytes().decode(),  # ciphertext ascii, sem decriptar
                "updated_at": now,
            }
            resp = client.post(url, headers=headers, json=row)
            if resp.status_code in (200, 201, 204):
                ok += 1
                print(f"  ✓ {email_hash[:12]}…")
            else:
                falhou += 1
                print(f"  ✗ {email_hash[:12]}… HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)

    print(f"Migração: {ok} ok, {falhou} falha(s), de {len(arquivos)} arquivo(s).")
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
