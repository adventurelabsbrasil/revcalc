-- revcalc_feedback — caixa de feedback do app (Melhoria / Falha / Log de erro / Dúvida).
--
-- Projeto Supabase canônico: ftctmseyrqhckutpfdeq (Adventure).
-- O backend FastAPI (server/feedback.py) insere via PostgREST com a service_role key
-- — nunca exposto ao browser. RLS é service-only (espelha o padrão das tabelas adv_*):
-- sem policy para anon/authenticated, então só a service_role (que bypassa RLS) lê/escreve.
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
-- Intencional: nenhuma policy. anon/authenticated não acessam; só service_role (backend).
