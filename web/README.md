# Front — Calculadora Crefaz (Next.js / Vercel)

UI fina: login Google, campo do nome da cliente, log ao vivo (SSE) e link da
pasta no Drive. Todo o trabalho pesado está no backend (`../server`).

## Dev

```bash
cd web
cp .env.local.example .env.local   # aponte NEXT_PUBLIC_API_BASE pro backend
npm install
npm run dev                        # http://localhost:3000
```
Suba o backend em paralelo (`uvicorn server.app:app --port 8000`).

## Deploy na Vercel

1. **New Project** → importe o repo `adventurelabsbrasil/revcalc`.
2. **Root Directory:** `web`.
3. **Environment Variable:** `NEXT_PUBLIC_API_BASE=https://api.revcalc.adventurelabs.com.br`
4. **Domínio custom:** `revcalc.adventurelabs.com.br` (mesmo registrable domain da
   API → cookie de sessão first-party; ver nota no `../server/README.md`).

> O front não guarda segredo nenhum. A autenticação e o token do Google ficam
> 100% no backend (cookie de sessão opaco + token store cifrado no xeon).

## Fluxo

`GET /api/me` → se logado, mostra o form. Adicione um ou vários nomes (fila de
chips) e clique "Calcular": faz `POST /api/run {nomes:[…]}`, abre um `EventSource`
no `events_url` e transmite o progresso até `done`/`error`. O `done` traz o
relatório por-cliente (calculado / já feito / não encontrado). Não há diálogo de
sobrescrita — contratos já calculados são pulados (para refazer, apague o
`Calculo.xlsx` na pasta do Drive).
