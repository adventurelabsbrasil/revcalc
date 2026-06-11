-- revcalc_feedback — caixa de feedback do app (Melhoria / Falha / Log de erro / Dúvida).
--
-- Projeto Supabase canônico: ftctmseyrqhckutpfdeq (Adventure).
-- O backend FastAPI (server/feedback.py) insere via PostgREST com a ANON key
-- (não a service_role) + uma policy INSERT-only. Least-privilege deliberado: a
-- service_role bypassa o RLS do banco INTEIRO (Sueli, financeiro, Dino...) e não
-- deve viver num container client-facing. Com a anon key, um vazamento só permite
-- INSERT em revcalc_feedback — não lê nada nem toca outra tabela (RLS das demais).
--
-- Aditiva e reversível: DROP TABLE public.revcalc_feedback; desfaz tudo.
-- Aplicar via MCP apply_migration (gated, OK do founder) — não auto.

CREATE TABLE IF NOT EXISTS public.revcalc_feedback (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at   timestamptz NOT NULL DEFAULT now(),
  tipo         text NOT NULL CHECK (tipo IN ('feat','bug','erro_sistema','duvida')),
  mensagem     text,                                  -- texto do usuário (obrigatório no manual; opcional no auto)
  email        text,                                  -- quem reportou (do cookie de sessão)
  origem       text NOT NULL DEFAULT 'manual' CHECK (origem IN ('manual','auto')),
  contexto     jsonb NOT NULL DEFAULT '{}'::jsonb,    -- url, user_agent, erro capturado, linhas de log
  app_version  text,                                  -- versão do app no momento do envio
  status       text NOT NULL DEFAULT 'novo' CHECK (status IN ('novo','triado','resolvido','descartado')),
  severidade   text CHECK (severidade IN ('baixa','media','alta','critica')),
  github_issue text                                   -- preenchido na promoção manual p/ issue (owner/repo#N)
);

COMMENT ON TABLE  public.revcalc_feedback IS 'Feedback do app revcalc (Rose). Tipos: feat/bug/erro_sistema/duvida. origem auto = botão de reporte de erro do sistema.';
COMMENT ON COLUMN public.revcalc_feedback.contexto IS 'jsonb não-PII-sensível por padrão; em erro_sistema pode conter linhas de log da run (dado do próprio tenant Rose).';

CREATE INDEX IF NOT EXISTS revcalc_feedback_created_idx ON public.revcalc_feedback (created_at DESC);
CREATE INDEX IF NOT EXISTS revcalc_feedback_status_idx  ON public.revcalc_feedback (status);

ALTER TABLE public.revcalc_feedback ENABLE ROW LEVEL SECURITY;

-- INSERT-only para anon (a chave que o app carrega). Sem policy de SELECT/UPDATE/
-- DELETE → anon não lê nem altera. service_role (triagem nossa via MCP/console)
-- bypassa o RLS normalmente. Por isso o backend usa Prefer: return=minimal (não
-- há RETURNING/SELECT permitido p/ anon).
DROP POLICY IF EXISTS revcalc_feedback_insert_anon ON public.revcalc_feedback;
CREATE POLICY revcalc_feedback_insert_anon
  ON public.revcalc_feedback
  FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);
