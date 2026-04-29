# Retomar — Calculadora de Ação Crefaz

> **Última atualização:** 2026-04-28 (sessão Cowork — 5 decisões D1-D5 fechadas + D6 nova)
> **Próxima fase:** **v0.5.1** patch cirúrgico (NÃO mais v0.6 refactor)
> **Antes de qualquer construção:** o brief da v0.6 foi descartado em favor de escopo enxuto. Ler `template-modifications-v0.5.1-FINAL.md`.

## Estado atual em 1 minuto

- **v0.5.0 (MVP) está em produção lógica** — código completo, 105 testes verdes, smoke E2E real passou com Adriano e Marlí. Tag `v0.5.0` apontando pro commit `0deec0d`. Pushed pro `origin/main`.
- **Bugs visuais conhecidos** no template atual (datas em formato US, tabela de parcelas com nº fixo errado, colunas de vencimento erradas em algumas abas). Diagnóstico técnico completo em [`template-modifications-v0.5.1-FINAL.md`](./template-modifications-v0.5.1-FINAL.md).
- **Decisão revisada (2026-04-28):** **NÃO vamos refazer o template do zero (v0.6 abandonada)** — vamos aplicar patch cirúrgico **v0.5.1** que corrige os bugs sem refactor estrutural. Foco: agilidade + rigor nos dados, zero cosmético.
- **5 decisões D1-D5 fechadas** + 1 decisão nova D6 (print-ready XLSX). Plano de execução pronto em [`template-modifications-v0.5.1-FINAL.md`](./template-modifications-v0.5.1-FINAL.md).

## Decisões fechadas em 2026-04-28

| ID | Decisão | Resultado |
|----|---------|-----------|
| D1 | Estrutura de abas | **A — Manter 4 abas** (24X / 36x / 48x / 60x) |
| D2 | Mexer em `planilha.py` | **A — Preservado**, só mapeamento adicional + defesa em profundidade |
| D3 | Identidade visual | Sem ID nova, sem logo, sem fonte custom, zero cosmético |
| D4 | Conteúdo jurídico | Manter as 6 seções exatas |
| D5 | Validação final | **Bruna Scopel + Advogada Bruna (funcionária da Rose) validam** |
| D6 | Print/save final | **XLSX print-ready** — page setup uniforme, A4 paisagem, fit-to-page |
| Executor | Quem aplica Bloco A | Agente Cowork via openpyxl (não Bruna manualmente no Excel) |

## O que fazer agora (próxima sessão)

### Antes de abrir o Cowork

Nada. Os assets visuais (logos, paletas, fontes) **não são mais necessários** — D3 cortou identidade visual do escopo. Basta abrir a sessão.

### Abrindo a sessão Cowork dedicada

1. **Workspace folder**: `/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS-main/` (worktree em `main` — é onde os arquivos da Crefaz estão tracked).
2. Cola este prompt de abertura no chat:

```
Vou implementar a v0.5.1 patch da Calculadora de Ação Crefaz.

Estado:
- v0.5.0 está em main com tag pushada
- Decisões D1-D6 fechadas em 2026-04-28
- Plano de execução completo em apps/clientes/02_rose/calculo-acao-crefaz/docs/template-modifications-v0.5.1-FINAL.md

Antes de qualquer ação, lê:
1. apps/clientes/02_rose/calculo-acao-crefaz/docs/RETOMAR.md
2. apps/clientes/02_rose/calculo-acao-crefaz/docs/template-modifications-v0.5.1-FINAL.md
3. .claude/memory/calculo-acao-crefaz.md

Depois, executa nessa ordem:

Bloco A (modificações no template via openpyxl):
- Cria scripts/aplica_v0.5.1.py
- Implementa A1 → A12 do plano
- Roda o script
- Confirma com A12 (validação pós-execução)
- Backup: garante que templates/Calculo.original.xlsx existe

Bloco B (código Python):
- Implementa B1 → B7 do plano
- Atualiza testes (B5)
- Roda smoke E2E (B6 + B7 NOVO — caso 30 parcelas em PRICE 36x)
- Garante que todos os 105+ testes passam

Quando tudo verde:
- Commit separado pra template (apps/clientes/02_rose/calculo-acao-crefaz/templates/Calculo.xlsx + .original.xlsx)
- Commit pra código (B1-B7)
- Commit pros docs (já estão prontos)
- Tag v0.5.1
- Push origin main + tags

NÃO empacotar .exe ainda — Bruna Scopel faz isso depois quando tiver tempo livre no ASUS.
```

## Mapa dos arquivos

| Arquivo | Função |
|---------|--------|
| [`docs/RETOMAR.md`](./RETOMAR.md) | **Você está aqui** — ponto de entrada |
| [`docs/template-modifications-v0.5.1-FINAL.md`](./template-modifications-v0.5.1-FINAL.md) | Plano de execução completo da v0.5.1 (Bloco A + B + smokes) |
| [`docs/template-redesign-brief.md`](./template-redesign-brief.md) | **DESCARTADO** — brief da v0.6 abandonada. Mantido por contexto histórico. |
| [`docs/template-modifications-v0.5.1.md`](./template-modifications-v0.5.1.md) | **SUBSTITUÍDO** pela versão FINAL. Mantido por contexto histórico. |
| `.claude/memory/calculo-acao-crefaz.md` (raiz do monorepo) | Armadilhas técnicas (offsets de aba, tkinter no brew, OAuth) |
| `README.md` | Visão geral do projeto + uso |
| `templates/Calculo.xlsx` | Template atual (com bugs — vai ser modificado in-place na v0.5.1) |
| `templates/Calculo.original.xlsx` | Backup do template pré-v0.5.1 (criado pelo script) |
| `src/calculadora_crefaz/` | Código completo (parser, drive, planilha, ui, pipeline, etc) |
| `tests/` | 105 testes unitários + E2E |
| `scripts/aplica_v0.5.1.py` | (a criar) Script idempotente que aplica Bloco A |

## Roadmap pós-v0.5.0 (revisado 2026-04-28)

| Versão | Escopo | Status |
|--------|--------|--------|
| v0.5.0 | MVP funcional com bugs visuais conhecidos | ✅ Entregue |
| **v0.5.1** | **Patch cirúrgico — corrige bugs do template + print-ready** | ⏳ Próxima sessão (plano completo) |
| v0.6 | Refactor 1 aba dinâmica + branding (se necessário) | 📋 Backlog (descartado nesta rodada) |
| v0.7 | GH Actions Win-only + Releases (`.exe` automático) | 📋 Planejado |
| v0.8 | Capturas xlwings + Excel local da Bruna | 📋 Planejado |
| v0.9 | Notificação Telegram outbound | 📋 Planejado |
| v1.0 | Code-signing + Mac binary | 📋 Backlog |
| v1.1 | Histórico estruturado em Supabase | 📋 Backlog |
| v2.0 | Contratos quitados (cálculo retrospectivo) | 📋 Backlog |

## Decisões já cristalizadas (não mexer)

- **OAuth Internal no Workspace `roseportaladvocacia.com.br`** — `client_id` em `.env` (gitignored). Login com `roselaine@` no Mac do Founder pra debug; Bruna usa email dela.
- **Distribuição via PyInstaller `--onefile` Windows** — Bruna Scopel empacota no ASUS dela até v0.7 ficar pronto. Mac roda via `python -m calculadora_crefaz` direto.
- **Histórico no `12 Log.txt`** — agora em modo append (acumula execuções). Sem Supabase no MVP.
- **Dedup via verificação de `10 Cálculo*.xlsx`** na pasta da cliente. Flag `--force` pula a confirmação.
- **Matching simplificado** — equipe Rose renomeia contrato pra `09 Contrato Crefaz.pdf` antes de processar.
- **NOVO 2026-04-28** — Validação técnica passa por Bruna Scopel + Advogada Bruna (funcionária da Rose Portal), não Roselaine.
- **NOVO 2026-04-28** — Bloco A executado via openpyxl pelo agente Cowork, não Bruna manualmente no Excel.

## Pendências do lado humano (não-Cowork)

- Após v0.5.1 entregue: **Advogada Bruna** valida cálculos célula a célula contra outputs v0.5.0.
- Após validação: **Bruna Scopel** empacota `.exe` no ASUS pra primeiro teste em produção real (ou esperar v0.7 com GH Actions).
- Comunicar Roselaine que XLSX será atualizado (sem precisar pedir validação dela — só ciência).
- Decidir prazo de entrega da v0.5.1 com a equipe Rose.
