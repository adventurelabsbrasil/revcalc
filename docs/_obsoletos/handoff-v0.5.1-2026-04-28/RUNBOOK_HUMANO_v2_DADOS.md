# Runbook humano v2 — finalização v0.5.1 com DADOS+visual + entrega à Bruna

> **Substitui:** `RUNBOOK_HUMANO.md` (SUPERSEDED em 2026-04-29).
> **Pra quem:** Rodrigo (Founder).
> **Estado:** template já migrado pra DADOS+visual nesta sessão Cowork. Falta só Bloco B residual via CLI + entrega humana.
> **Duração esperada:** 10min (preparação main) + ~45-90min (CLI rodando, passivo) + ~30min de validação Bruna depois.

---

## Passo 1 — Migrar arquivos do worktree atual pra `main` (10min)

Os arquivos novos estão em `01_ADVENTURE_LABS/apps/clientes/02_rose/calculo-acao-crefaz/` (worktree `feat/benditta-lp-essencial-monorepo`, untracked). Precisa mover pra `main`.

```bash
# 1. Vai pro worktree main
cd /Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS-main
git checkout main
git pull origin main

# 2. Copia os arquivos novos do worktree feat
SRC=/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS/apps/clientes/02_rose/calculo-acao-crefaz
DST=apps/clientes/02_rose/calculo-acao-crefaz

# Template novo + snapshot pré-DADOS
cp "$SRC/templates/Calculo.xlsx" "$DST/templates/Calculo.xlsx"
cp "$SRC/templates/Calculo.preDADOS.xlsx" "$DST/templates/Calculo.preDADOS.xlsx"

# Script de migração
mkdir -p "$DST/scripts"
cp "$SRC/scripts/migrar_para_dados.py" "$DST/scripts/migrar_para_dados.py"

# Docs do handoff
mkdir -p "$DST/docs"
cp "$SRC/_handoff-v0.5.1-2026-04-28/HANDOFF_PLANILHA_DADOS_VS_VISUAL.md" "$DST/docs/HANDOFF_PLANILHA_DADOS_VS_VISUAL.md"
cp "$SRC/_handoff-v0.5.1-2026-04-28/RELATORIO_MIGRACAO_DADOS.md" "$DST/docs/RELATORIO_MIGRACAO_DADOS.md"
cp "$SRC/_handoff-v0.5.1-2026-04-28/PROMPT_CLI_RESIDUAL.md" "$DST/docs/PROMPT_CLI_RESIDUAL.md"
cp "$SRC/_handoff-v0.5.1-2026-04-28/RETOMAR.md" "$DST/docs/RETOMAR.md"  # sobrescreve a versão antiga
cp "$SRC/_handoff-v0.5.1-2026-04-28/template-modifications-v0.5.1-FINAL.md" "$DST/docs/template-modifications-v0.5.1-FINAL.md"

# 3. Confere o diff
git status
git diff --stat

# 4. Commit do template + script (1 commit)
git add "$DST/templates/Calculo.xlsx" "$DST/templates/Calculo.preDADOS.xlsx" "$DST/scripts/migrar_para_dados.py"
git commit -m "build(crefaz): migrate template to DADOS+visual architecture

- Aba DADOS oculta com B2:B14 contrato (13 campos)
- 44 substituições nas 4 PRICE: valores cravados → fórmulas =DADOS!\$B\$X
- Snapshot v0.5.1 pré-migração preservado em Calculo.preDADOS.xlsx
- Script idempotente em scripts/migrar_para_dados.py
- Validado: 220 fórmulas resolvem com 0 erros (caso Adriano via LibreOffice recalc)"

# 5. Commit dos docs (1 commit separado)
git add "$DST/docs/"
git commit -m "docs(crefaz): consolidate DADOS+visual migration handoff

- HANDOFF_PLANILHA_DADOS_VS_VISUAL.md: decisão e plano canônico
- RELATORIO_MIGRACAO_DADOS.md: validação matemática caso Adriano (zero erros)
- PROMPT_CLI_RESIDUAL.md: prompt para Claude Code CLI fechar Bloco B
- RETOMAR.md atualizado, template-modifications-v0.5.1-FINAL.md preservado"

# 6. Push
git push origin main
```

**Critério de done:** `git log --oneline -3` no `main` mostra os 2 commits novos. `apps/clientes/02_rose/calculo-acao-crefaz/templates/Calculo.xlsx` em main agora tem aba DADOS.

---

## Passo 2 — Abrir Cursor + Claude Code CLI no worktree main (2min)

1. Abre o Cursor.
2. `File → Open Folder…` → `/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS-main/`.
3. Abre terminal integrado.
4. Confirma:
   ```bash
   git branch --show-current  # main
   git log --oneline -3       # commits que você acabou de pushar
   ls apps/clientes/02_rose/calculo-acao-crefaz/templates/  # Calculo.xlsx, Calculo.preDADOS.xlsx, Calculo.original.xlsx
   ```
5. Roda:
   ```bash
   claude
   ```

---

## Passo 3 — Colar o prompt residual no CLI (1min)

1. Abre `apps/clientes/02_rose/calculo-acao-crefaz/docs/PROMPT_CLI_RESIDUAL.md` em outro tab.
2. Copia **o conteúdo entre `═══ PROMPT ═══` e `═══ FIM DO PROMPT ═══`** (não as 3 crases delimitadoras).
3. Cola no Claude Code CLI.
4. Aperta Enter, larga rodando.

---

## Passo 4 — Acompanhar (passivo, ~45-90min)

O agente vai:
1. Ler os 6 docs/arquivos canônicos (~5min)
2. Implementar log_writer append + teste (~10min)
3. Atualizar test_planilha pra cobrir dual-mode (~15min) — ler templates real + preDADOS
4. Criar test_caso_30_parcelas.py (~10min)
5. Re-rodar smoke E2E Adriano + Marlí (~10min)
6. Rodar suíte completa (~3min)
7. Criar 4 commits + tag + push (~5min)

**Quando intervir:** se ele reportar regressão real em teste antigo, ou conflito git no pull, ou falha no smoke E2E. Se for questão de fixture stale ou serialização openpyxl, deixa ele resolver.

---

## Passo 5 — Receber resumo telegráfico (5min)

Confere se:
- [ ] Tag `v0.5.1` aparece em `git tag -l`
- [ ] `git log --oneline -10` mostra os 4 commits novos do CLI + os 2 que você fez no passo 1
- [ ] Push do tag confirmado
- [ ] Suíte de testes verde

Se tudo ok → passo 6. Se algo errado → revisar com ele no chat.

---

## Passo 6 — Entregar pra Bruna Scopel (sua janela: 5min de mensagem)

Mensagem WhatsApp:

```
Oi amor, terminei a v0.5.1 da Calculadora Crefaz.

Mudou a arquitetura do template — agora tem uma aba "DADOS" oculta
que recebe os valores do contrato, e as 4 abas PRICE puxam de lá via
fórmulas. Cliente final continua vendo só uma aba PRICE com tudo
preenchido, igual antes — mas o caminho dos dados é mais limpo.

Preciso que abra o Calculo.xlsx (qualquer cliente que rodar a partir
de agora vai gerar com esse template novo) e confirme:

1. As 4 abas (24X, 36x, 48x, 60x) renderizam ok visualmente
2. Ctrl+P em qualquer aba mostra preview certinho em A4 paisagem,
   sem cortar tabela
3. (Se conseguir abrir no Excel real, melhor que Numbers) — Numbers
   às vezes não exibe fórmula direito, mas no Excel da Rose vai
   funcionar 100%

Não precisa rodar caso real ainda — quero só sua aprovação visual.

Depois disso, a Advogada Bruna confere os cálculos célula a célula
contra um output da v0.5.0 conhecido. Aprovou? Comunico Roselaine
que está atualizado.

Sem pressa, faça quando der.
```

**Se Bruna não tiver Excel no Mac/ASUS:** o XLSX gerado pelo app na pasta da cliente é que será aberto pela equipe Rose (que tem Excel). Bruna só precisa validar visualmente que o template está coerente — Numbers/Sheets serve.

---

## Passo 7 — Entregar pra Advogada Bruna (via Jessica)

> Use a skill `jessica-conta-rose` em sessão Cowork futura pra rascunhar a mensagem com tom calibrado da conta. Conteúdo essencial:

1. Pegar 2 XLSX da v0.5.0 já existentes (Adriano + Marlí — devem estar no histórico do Drive).
2. Rodar o pipeline com a v0.5.1 nos mesmos contratos → gerar 2 XLSX da v0.5.1.
3. Pedir: "Confere se números (cédula, valor parcela, taxa, total devido, total pago, excesso BACEN) batem entre v0.5.0 e v0.5.1 pros 2 casos. O que mudou foi só o caminho dos dados (template foi reorganizado), os números devem ser idênticos."
4. Tempo estimado dela: 15-30min.

---

## Passo 8 — Comunicar Roselaine (depois das duas aprovarem)

Use Jessica pra calibrar tom. Mensagem curta, ciência apenas:

> "Roselaine, atualizamos o template da Calculadora Crefaz pra organizar melhor o cálculo internamente. Funcionalmente é igual — mesmo XLSX final na pasta da cliente, mesmas seções jurídicas, mesmas datas em formato BR, mesma impressão paisagem. Só ficou mais robusto pra evitar bugs futuros. Bruna Scopel e a Advogada Bruna validaram. Pode usar normal."

---

## Passo 9 — Empacotar `.exe` (Bruna Scopel, sem urgência)

Não bloqueia v0.5.1. Quando Bruna Scopel tiver janela no ASUS:
1. `git pull` no monorepo
2. `cd apps/clientes/02_rose/calculo-acao-crefaz`
3. Ativar `.venv` no Windows
4. `pyinstaller --onefile --windowed src/calculadora_crefaz/__main__.py`
5. Testar `.exe` com 1 caso real

Alternativa: aguardar v0.7 (GH Actions Win-only build automático).

---

## Recapitulação dos roles

| Quem | Faz o quê | Quando |
|------|-----------|--------|
| **Rodrigo** | Passos 1-3 (mover arquivos pra main + abrir CLI), receber resumo, comunicar Bruna | Hoje (~30min ativo) |
| **Claude Code CLI** | Bloco B residual (log append + smoke + testes dual-mode + commits + tag) | Hoje (~45-90min passivo) |
| **Bruna Scopel** | Validar visual + Ctrl+P; depois empacotar .exe quando puder | Quando tiver janela |
| **Advogada Bruna (Rose)** | Comparar números v0.5.0 vs v0.5.1 (2 casos) | Depois Bruna Scopel aprovar visual |
| **Roselaine** | Recebe ciência (não valida) | Depois ambas Brunas aprovarem |

---

## Se der ruim

- **CLI travou no meio:** `Ctrl+C`, lê o último output. Se foi no log_writer: rode `git restore src/calculadora_crefaz/log_writer.py`. Se foi nos testes: rode `git stash` e reabre nova sessão CLI explicando onde parou.
- **Suíte de testes vermelha pós-changes:** `git revert <hash>` dos commits do código. Reabrir nova sessão com log do pytest.
- **XLSX não abre / abre quebrado em algum lugar:** comparar com `templates/Calculo.preDADOS.xlsx` (snapshot v0.5.1 sem DADOS) — se o pré abre e o novo não, é a inserção de DADOS que quebrou. Reverter via `git revert` do commit do template e abrir nova sessão Cowork.
- **Cálculos divergem entre v0.5.0 e v0.5.1 pra Advogada Bruna:** PARAR, NÃO publicar pra Roselaine. Investigar célula a célula com a Advogada — se for bug do template novo, abrir nova sessão Cowork; se for bug que já existia em v0.5.0, abrir issue separada.
