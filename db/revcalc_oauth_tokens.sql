-- revcalc_oauth_tokens — token store OAuth do app, backend "supabase" (HA ativo/ativo).
--
-- Projeto Supabase canônico: ftctmseyrqhckutpfdeq (Adventure).
-- O backend FastAPI (server/token_store.py) faz UPSERT/SELECT/DELETE via PostgREST
-- com a ANON key (server-side, NUNCA no browser) — mesmo padrão de feedback.py.
--
-- Segurança: a coluna encrypted_creds guarda SÓ ciphertext (Fernet), cuja chave
-- deriva do SESSION_SECRET que vive apenas nos backends (xeon/beelink) — o banco
-- nunca vê a chave nem o plaintext. Guardamos email_hash (sha256), não o email cru
-- (minimização de PII). Diferente do feedback (INSERT-only), o token store precisa
-- de SELECT/UPDATE/DELETE — as policies abaixo são escopadas SÓ a esta tabela, então
-- um eventual vazamento da anon só alcança ciphertext desta tabela (inútil sem o
-- SESSION_SECRET, que se vazar junto já compromete tudo de qualquer forma). RLS
-- explícita e default-deny (mindful do fail-open sistêmico, adventure-labs#841).
-- A service_role NÃO vive no container de propósito (bypassaria o RLS do banco todo).
--
-- Aditiva e reversível: DROP TABLE public.revcalc_oauth_tokens; desfaz tudo.
-- Aplicar via MCP apply_migration (gated, OK do founder) — não auto.

CREATE TABLE IF NOT EXISTS public.revcalc_oauth_tokens (
  email_hash      text PRIMARY KEY,                     -- sha256(lower(email)) hex — sem email cru (PII min.)
  encrypted_creds text NOT NULL,                        -- Fernet(creds.to_json()) — ciphertext; chave nunca vai ao DB
  updated_at      timestamptz NOT NULL DEFAULT now()    -- refrescado no UPSERT (merge-duplicates)
);

COMMENT ON TABLE  public.revcalc_oauth_tokens IS 'Token store OAuth cifrado do revcalc (Rose), backend supabase p/ HA ativo/ativo xeon+beelink. Só ciphertext; chave Fernet vive nos backends (SESSION_SECRET).';
COMMENT ON COLUMN public.revcalc_oauth_tokens.encrypted_creds IS 'Fernet ciphertext de Credentials.to_json() (refresh+access token do Google). Indecifrável sem SESSION_SECRET.';

ALTER TABLE public.revcalc_oauth_tokens ENABLE ROW LEVEL SECURITY;

-- Policies escopadas SÓ a esta tabela, p/ o role anon (a chave que o backend carrega).
-- SELECT/INSERT/UPDATE/DELETE porque o fluxo precisa ler (load), gravar (save/refresh)
-- e apagar (logout). service_role bypassa RLS (triagem/manutenção nossa via MCP).
DROP POLICY IF EXISTS revcalc_oauth_tokens_sel_anon ON public.revcalc_oauth_tokens;
CREATE POLICY revcalc_oauth_tokens_sel_anon
  ON public.revcalc_oauth_tokens FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS revcalc_oauth_tokens_ins_anon ON public.revcalc_oauth_tokens;
CREATE POLICY revcalc_oauth_tokens_ins_anon
  ON public.revcalc_oauth_tokens FOR INSERT TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS revcalc_oauth_tokens_upd_anon ON public.revcalc_oauth_tokens;
CREATE POLICY revcalc_oauth_tokens_upd_anon
  ON public.revcalc_oauth_tokens FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS revcalc_oauth_tokens_del_anon ON public.revcalc_oauth_tokens;
CREATE POLICY revcalc_oauth_tokens_del_anon
  ON public.revcalc_oauth_tokens FOR DELETE TO anon, authenticated USING (true);
