# Runbook humano — finalização v0.5.1 + entrega à Bruna

> ⚠️ **SUPERSEDED em 2026-04-29.** Este runbook orientava a v0.5.1 cirúrgica via Claude Code CLI no Cursor. Foi superado pelo caminho **DADOS+visual** (template já migrado pelo Cowork nesta sessão). Use `RUNBOOK_HUMANO_v2_DADOS.md` para os próximos passos. Mantido por contexto histórico.

---

> **Pra quem:** Rodrigo (Founder)
> **Quando:** agora — sessão de fechamento do MVP Crefaz
> **Duração esperada:** 15min (preparação) + ~2-3h (CLI rodando, você pode largar) + 30min (validação Bruna depois)
> **Pré-requisito técnico:** Cursor instalado, Claude Code CLI configurado (`claude` no PATH), git logado em `roseportaladvocacia.com.br` ou no seu github.com pessoal com acesso ao monorepo.

---

## Passo 1 — Preparar o terreno em `main` (10min)

A sessão Cowork anterior gerou os 3 docs do handoff dentro do worktree errado (`01_ADVENTURE_LABS/`, branch `feat/benditta-lp-essencial-monorepo`, onde a pasta Crefaz está untracked). Precisa migrar pra `main` antes do CLI rodar.

```bash
# 1. Vai pro worktree main
cd /Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS-main
git checkout main
git pull origin main

# 2. Confirma onde estão os 3 docs novos do handoff
ls "/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS/apps/clientes/02_rose/calculo-acao-crefaz/_handoff-v0.5.1-2026-04-28/"
# Deve listar: RETOMAR.md, template-modifications-v0.5.1-FINAL.md, PROMPT_CLAUDE_CODE_CLI.md, RUNBOOK_HUMANO.md

# 3. Copia os 2 docs canônicos pra docs/ em main (sobrescreve o RETOMAR.md antigo)
cp "/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS/apps/clientes/02_rose/calculo-acao-crefaz/_handoff-v0.5.1-2026-04-28/RETOMAR.md" \
   apps/clientes/02_rose/calculo-acao-crefaz/docs/RETOMAR.md

cp "/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS/apps/clientes/02_rose/calculo-acao-crefaz/_handoff-v0.5.1-2026-04-28/template-modifications-v0.5.1-FINAL.md" \
   apps/clientes/02_rose/calculo-acao-crefaz/docs/template-modifications-v0.5.1-FINAL.md

# 4. (Opcional, mas recomendado) Inclui o prompt do CLI no repo pra histórico
cp "/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS/apps/clientes/02_rose/calculo-acao-crefaz/_handoff-v0.5.1-2026-04-28/PROMPT_CLAUDE_CODE_CLI.md" \
   apps/clientes/02_rose/calculo-acao-crefaz/docs/PROMPT_CLAUDE_CODE_CLI.md

# 5. Confere o diff
git status
git diff --stat

# 6. Commit + push
git add apps/clientes/02_rose/calculo-acao-crefaz/docs/
git commit -m "docs(crefaz): consolidate D1-D6 decisions and v0.5.1 final plan

- Decisões D1-D6 fechadas em sessão Cowork de 2026-04-28
- v0.6 refactor descartada em favor de v0.5.1 patch cirúrgico
- Bloco A migra de Bruna manual no Excel pra agente Claude Code via openpyxl
- B7 novo (smoke 30 parcelas em PRICE 36x) adicionado
- D6 novo (XLSX print-ready: A4 paisagem + fit-to-page)
- Validação técnica passa por Bruna Scopel + Advogada Bruna (Rose Portal)"

git push origin main
```

**Critério de done deste passo:** `apps/clientes/02_rose/calculo-acao-crefaz/docs/RETOMAR.md` em `main` é o de 7175 bytes (não o antigo de 4728). E `template-modifications-v0.5.1-FINAL.md` existe em `docs/`.

---

## Passo 2 — Abrir Cursor + Claude Code CLI no worktree main (2min)

1. Abrir o Cursor.
2. `File → Open Folder…` → selecionar `/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS-main/`.
3. Abrir terminal integrado (`Ctrl+\`` ou `View → Terminal`).
4. Confirmar que está em `main` e atualizado:
   ```bash
   git branch --show-current  # deve dizer "main"
   git log --oneline -3       # último commit deve ser o que você acabou de pushar
   ```
5. Rodar:
   ```bash
   claude
   ```
   (Ou `claude code`, dependendo da sua instalação. Se não estiver no PATH, instale via `npm i -g @anthropic-ai/claude-code` ou verifique a doc oficial.)

---

## Passo 3 — Colar o prompt-mestre (1min)

1. Abre `apps/clientes/02_rose/calculo-acao-crefaz/docs/PROMPT_CLAUDE_CODE_CLI.md` (ou o do `_handoff-v0.5.1-2026-04-28/` se você não copiou) num editor à parte.
2. Copia **somente o conteúdo entre `═══ PROMPT ═══` e `═══ FIM DO PROMPT ═══`** (NÃO copie as 3 crases que delimitam o bloco — só o que está dentro).
3. Cola no Claude Code CLI.
4. Aperta Enter e larga o terminal aberto. Pode ir tomar um café ou trabalhar em outra coisa.

---

## Passo 4 — Acompanhar (passivo, ~2-3h)

O agente vai:
1. Ler os 3 docs canônicos (~5min)
2. Inspecionar template + código atual (~10min)
3. Criar `scripts/aplica_v0.5.1.py` e rodar Bloco A (~30-60min — esse é o passo mais arriscado, pode aparecer ajuste de cell style)
4. Implementar Bloco B + testes (~45-60min)
5. Rodar suite completa (~5min)
6. Criar 3-4 commits + tag + push (~5min)
7. Devolver resumo telegráfico

**Quando intervir:**
- Se ele parar reportando "A12 divergiu", abrir o XLSX gerado no LibreOffice ou Numbers (no Mac, evita ter que subir pro ASUS) e conferir o diff visualmente. Pode ser ajuste de offset que ele sozinho não decide.
- Se um teste quebrar e ele reportar regressão (não fixture stale), revisar antes de mandar continuar.
- Se aparecer pedido de credencial OAuth: o `.env` está em `01_ADVENTURE_LABS-main/apps/clientes/02_rose/calculo-acao-crefaz/.env` ou na raiz do worktree feat (pode precisar copiar).

**Quando NÃO intervir:**
- Avisos de openpyxl perdendo estilo cosmético (D3 cobre).
- Reorganizações pequenas de imports ou helpers — desde que não toque conteúdo jurídico.

---

## Passo 5 — Receber o resumo telegráfico (5min)

O agente vai devolver no formato:

```
v0.5.1 entregue.
Testes: 108 passando (3 novos).
Commits: abc1234 template, def5678 código, ghi9012 testes.
Tag: v0.5.1 → ghi9012.
Pushed: origin/main + tag.
Arquivos novos: ...
Arquivos modificados: ...
Surpresas/divergências: ...
Gate humano pendente:
  1. Bruna Scopel — Excel + Ctrl+P
  2. Advogada Bruna — célula a célula vs Adriano/Marlí
Próximos passos sugeridos: ...
```

Confere se:
- [ ] Tag `v0.5.1` aparece em `git tag -l`
- [ ] `git log --oneline -5` mostra os commits
- [ ] `templates/Calculo.original.xlsx` existe (backup pré-patch)
- [ ] Smoke E2E rodou sem erro

Se tudo ok → passo 6. Se algo errado → revisar com ele no chat.

---

## Passo 6 — Entregar pra Bruna Scopel (15min seu + tempo dela quando puder)

### O que mandar no WhatsApp pra Bruna

```
Oi amor, terminei a v0.5.1 da Calculadora Crefaz.
Os bugs visuais que apareceram nos testes (datas erradas, tabela
com nº fixo, vencimentos em branco no PRICE 36x+) estão corrigidos.
Agora preciso que você abra o Calculo.xlsx no Excel do ASUS e
me confirme 2 coisas:

1. Visual: as 4 abas (24X, 36x, 48x, 60x) abrem sem nada quebrado.
2. Print: Ctrl+P em qualquer aba mostra preview certinho em A4 paisagem,
   sem cortar tabela.

Não precisa rodar caso real ainda — quero só sua aprovação visual.

Depois disso, a Advogada Bruna confere os cálculos célula a célula.
Quando ambas aprovarem, comunico pra Roselaine que está atualizado.

Sem pressa, faça quando der.
```

**Se Bruna achar bug visual** → não tentar ajustar via Cowork ou CLI; abrir nova sessão com escopo claro do que mudou e por quê.

### O que mandar pra Advogada Bruna (via Jessica ou direto)

> Idealmente passa pela Jessica (account manager Rose) pra coordenar tom e timing — ela conhece o relacionamento. Use a skill `jessica-conta-rose` na próxima sessão pra rascunhar a mensagem.

Conteúdo essencial da entrega:
1. XLSX gerado pelo Adriano (12 parcelas) pela v0.5.0 (já existente — pegar do histórico)
2. XLSX gerado pelo Adriano pela v0.5.1 (novo — gerar manualmente rodando o pipeline)
3. Mesma coisa pra Marlí
4. Pedido específico: "Confere se os números (cédula, parcela, juros, total) batem entre v0.5.0 e v0.5.1. O que mudou foi só formato de data e estrutura da tabela — números devem ser idênticos."

---

## Passo 7 — Comunicar Roselaine (depois das duas aprovarem)

Mensagem curta, só ciência. Roselaine não precisa validar tecnicamente (D5 explícito). Ideia geral:

> "Roselaine, atualizamos a planilha de cálculo Crefaz pra corrigir alguns bugs visuais (datas em formato BR, tabelas dimensionadas pelo prazo do contrato). Funcionalidade está igual, só mais limpa pra impressão. Bruna Scopel e a Advogada Bruna validaram. Pode usar normal."

Use a skill `jessica-conta-rose` pra calibrar tom — Roselaine espera comunicação institucional, não técnica.

---

## Passo 8 — Empacotar `.exe` (Bruna Scopel, quando ela tiver janela)

**Não é seu problema agora.** A v0.5.1 entrega XLSX print-ready, não binário Windows.

Quando Bruna Scopel tiver tempo livre no ASUS:
1. `git pull` no monorepo
2. `cd apps/clientes/02_rose/calculo-acao-crefaz`
3. Ativar `.venv` no Windows
4. Rodar `pyinstaller --onefile --windowed src/calculadora_crefaz/__main__.py`
5. Testar o `.exe` numa pasta de cliente real

Se Bruna não tiver tempo, esperar v0.7 (GH Actions Win-only build automático no tag push).

---

## Recapitulação dos roles

| Quem | Faz o quê | Quando |
|------|-----------|--------|
| **Rodrigo** | Roda passos 1-3, recebe resumo, comunica Bruna | Hoje (~30min ativo) |
| **Claude Code CLI** | Executa Bloco A + Bloco B + commits + tag + push | Hoje (~2-3h passivo) |
| **Bruna Scopel** | Valida visual + Ctrl+P; depois empacota .exe | Quando tiver janela |
| **Advogada Bruna (Rose)** | Valida cálculos célula a célula vs v0.5.0 | Depois da Bruna Scopel aprovar visual |
| **Roselaine** | Recebe ciência (não valida) | Depois de ambas Brunas aprovarem |

---

## Se der ruim

- **CLI travou no meio:** `Ctrl+C`, lê o último output dele no terminal, identifica em qual passo (A1-A12 ou B1-B7) parou. Se foi no Bloco A: rode `git restore templates/` + `python scripts/aplica_v0.5.1.py` de novo (idempotente). Se foi no Bloco B: `git stash` + retomar manualmente ou abrir nova sessão CLI explicando onde parou.
- **Testes ficaram quebrados pós-patch:** `git stash` ou `git revert <hash>` dos commits do código (não do template). Reabrir nova sessão CLI mostrando log do pytest.
- **XLSX não abre no Excel da Bruna:** comparar com `templates/Calculo.original.xlsx` (backup) — se o original abria e o novo não, é regressão de openpyxl. Reverter, abrir nova sessão CLI com escopo "preservar XML do XLSX original".
- **Você decidiu que precisa cosmético afinal:** v0.6 — não tente forçar agora. Abre nova sessão Cowork com brief de redesign.
