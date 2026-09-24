# Backend web — Calculadora Crefaz (FastAPI)

Embrulha o engine desktop (`calculadora_crefaz`) num serviço HTTP: OAuth web
server-side, execução do pipeline em thread e progresso ao vivo via SSE. Roda
como **container** (precisa de LibreOffice no PATH para as capturas).

Arquitetura: **front Next.js na Vercel** → **este backend num container no xeon**
(atrás do Traefik) → **Google Drive**. O engine de cálculo roda inalterado.

## Pré-requisito: OAuth no Google Cloud (Fase 0)

1. No projeto Google Cloud **do Workspace da Rose** (`roseportaladvocacia.com.br`):
2. **OAuth consent screen** → tipo **Internal**. Isso dispensa verificação/CASA
   do Google para o escopo restrito `.../auth/drive` (vale só p/ usuários do
   Workspace; usuário Adventure pode precisar entrar como membro/convidado).
3. **Credentials → Create OAuth client ID → Web application**.
   - Authorized redirect URI: `https://api.revcalc.adventurelabs.com.br/api/auth/callback`
   - (dev: `http://localhost:8000/api/auth/callback`)
4. Guarde **client_id** e **client_secret** no `.env`.

## Variáveis de ambiente

Veja `.env.example` na raiz. Mínimo:

| Var | Exemplo | Nota |
|-----|---------|------|
| `GOOGLE_OAUTH_CLIENT_ID` | `…apps.googleusercontent.com` | OAuth client **Web** |
| `GOOGLE_OAUTH_CLIENT_SECRET` | `GOCSPX-…` | idem |
| `OAUTH_REDIRECT_URI` | `https://api.revcalc.…/api/auth/callback` | = redirect cadastrado no Google |
| `FRONTEND_ORIGIN` | `https://revcalc.adventurelabs.com.br` | origem do front (CORS + redirect pós-login) |
| `SESSION_SECRET` | (32+ bytes aleatórios) | assina cookie/stream token; `openssl rand -hex 32` |
| `TOKEN_STORE_BACKEND` | `disk` | `disk` (volume) ou `supabase` (estado compartilhado p/ HA ativo/ativo) |
| `TOKEN_STORE_PATH` | `/data/tokens` | volume do token store cifrado (backend `disk`) |
| `REVCALC_OAUTH_TABLE` | `revcalc_oauth_tokens` | tabela do token store (backend `supabase`) |
| `COOKIE_DOMAIN` | `.adventurelabs.com.br` | cookie first-party entre `revcalc.` e `api.revcalc.` |
| `COOKIE_SAMESITE` | `lax` | `lax` se front+api no mesmo domínio; `none` se cross-site |
| `COOKIE_SECURE` | `true` | `false` só em dev http |
| `TOKEN_ENC_KEY` | (Fernet key) | opcional; se ausente, derivada do `SESSION_SECRET` |
| `REVCALC_PASTA_MAE_ID` / `REVCALC_PASTA_BACEN_ID` | (Drive IDs) | opcional; fallback = prod Rose |

> **Cookies first-party:** sirva o front num subdomínio do mesmo domínio da API
> (ex.: `revcalc.adventurelabs.com.br` via domínio custom na Vercel +
> `api.revcalc.adventurelabs.com.br` no xeon) e use `COOKIE_DOMAIN=.adventurelabs.com.br`
> + `COOKIE_SAMESITE=lax`. Assim o cookie de sessão não é bloqueado como
> "third-party". (O SSE não depende de cookie — usa um stream token assinado na URL.)

> **Token store — `disk` vs `supabase` (HA ativo/ativo).** No backend `disk`, cada
> host guarda os tokens no seu volume → num deploy multi-host (xeon + beelink) o
> usuário re-loga quando a Cloudflare o roteia pro replica sem o token dele. O backend
> `supabase` guarda o token (mesmo ciphertext Fernet) em `public.revcalc_oauth_tokens`
> via PostgREST + anon key (server-side), compartilhado entre os hosts → sessão
> sobrevive ao failover. **Só ciphertext vai pro banco; a chave deriva do
> `SESSION_SECRET`, que DEVE ser idêntico em todos os hosts.** RLS escopada só a essa
> tabela (`db/revcalc_oauth_tokens.sql`); a service_role **não** vive no container.
> Migração disco→Supabase: `scripts/migrate_tokens_to_supabase.py` (roda 1x, não
> decifra). Rollout: deploy com `disk` → migrar → flip `TOKEN_STORE_BACKEND=supabase`
> nos dois hosts. Ver adventure-labs#1188.

## Deploy no xeon

```bash
# na raiz do repo, com .env preenchido
sudo docker compose up -d --build
curl -fsS http://127.0.0.1:8000/healthz   # {"status":"ok","libreoffice":true}
```

O merge do GitHub não atualiza o container automaticamente. Para não deixar o
servidor atrás do `main`, toda mudança em `src/`, `server/` ou `templates/`
deve seguir esta sequência:

1. Atualizar o clone de produção e confirmar que não há alterações rastreadas
   locais antes de alinhar ao `main`:

   ```bash
   cd ~/revcalc
   git fetch origin
   git status --short --branch
   git switch main
   git reset --hard origin/main
   ```

   Arquivos `.bak` e logs não rastreados devem ser preservados; o `reset` não
   pode apagar alterações rastreadas sem autorização.

2. Rebuildar o container e validar a entrega real:

   ```bash
   sudo docker compose up -d --build
   curl -fsS http://127.0.0.1:8000/healthz
   sudo docker exec revcalc-api grep -n competencia_bacen /app/src/calculadora_crefaz/pipeline.py
   sudo docker ps --filter name=revcalc-api
   ```

   O healthcheck deve estar saudável e o marcador específico do commit deve
   existir dentro do container. Para mudanças de regra, executar também um
   smoke que diferencie o mês da emissão do primeiro vencimento.

3. Só depois validar o deploy **Production** da Vercel e executar o smoke web.
   A entrega só está concluída quando backend e frontend apontam para o mesmo
   `main`.

> O `beelink` não faz mais parte da topologia de produção. Não usar o antigo
> procedimento de rebuild em dois hosts.

Aponte o Traefik para `127.0.0.1:8000` (ou use os labels comentados no
`docker-compose.yml` ligando à rede do Traefik). TLS no Traefik.

> **1 worker só.** O registry de runs e as filas SSE são em-processo — múltiplos
> workers fariam o SSE cair em um worker diferente do que roda o job. O compose
> já fixa `--workers 1`.

## Dev local (sem container)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[web]"
export OAUTHLIB_INSECURE_TRANSPORT=1   # permite redirect http em dev
export COOKIE_SECURE=false
# preencha .env (redirect = http://localhost:8000/api/auth/callback)
uvicorn server.app:app --reload --port 8000
```
Precisa de LibreOffice instalado localmente para as capturas (`soffice` no PATH);
sem ele o cálculo ainda roda — só não gera os prints (degradação não-fatal).

## Rotas

| Método | Rota | Função |
|--------|------|--------|
| GET | `/healthz` | liveness + LibreOffice disponível |
| GET | `/api/auth/login` | redireciona pro consent Google |
| GET | `/api/auth/callback` | troca code, valida domínio, seta cookie |
| POST | `/api/auth/logout` | limpa cookie + apaga token |
| GET | `/api/me` | `{email}` do logado (401 se não) |
| POST | `/api/run` | inicia run do lote (`{nomes:[…]}` ou `{nome}` compat); `400` se nenhum nome válido |
| GET | `/api/run/{id}/events?t=…` | SSE com o progresso ao vivo |

### Fluxo do run (lote + pular já-calculados — v0.9.8)
`POST /api/run {nomes:[…]}` (ou `{nome}` para um só) → o backend valida (≥2 palavras
por nome, via `run_input.extrair_nomes`) e devolve `{run_id, events_url}`; o front
abre o `EventSource`. **Sem pré-check/confirmação:** o run processa cada cliente em
sequência (`pipeline.executar_lote`), **pula** contratos que já têm cálculo
(`Calculo[.quitado].xlsx`) e isola erro por-cliente. O evento `done` traz o
relatório por-cliente (`{clientes:[…], resumo:{…}}`). Para refazer um cálculo,
apague o arquivo na pasta do Drive (não há sobrescrita pela UI).
