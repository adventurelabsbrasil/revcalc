# Prompt — Próxima sessão Cowork (implementação v0.5.1)

> **Quando usar:** assim que Rodrigo abrir uma nova sessão Cowork no worktree certo.
> **Workspace folder a selecionar:** `/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS-main/`
> **Branch esperada:** `main` (com `git pull` antes pra garantir que está sincronizado)

---

## Passo 0 — Antes de abrir o Cowork (preparar o terreno em main)

No terminal, no worktree main:

```bash
cd /Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS-main
git checkout main
git pull origin main

# Copiar os 2 docs gerados pela sessão anterior pra dentro do repo
# (assumindo que você baixou outputs/ pra /tmp ou similar)
cp /tmp/template-modifications-v0.5.1-FINAL.md apps/clientes/02_rose/calculo-acao-crefaz/docs/
cp /tmp/RETOMAR.md apps/clientes/02_rose/calculo-acao-crefaz/docs/RETOMAR.md  # sobrescreve o anterior

# Commit dos docs
git add apps/clientes/02_rose/calculo-acao-crefaz/docs/
git commit -m "docs(crefaz): consolidar decisões D1-D6 + plano v0.5.1 final

- Decisões D1-D5 fechadas em sessão Cowork de 2026-04-28
- D6 nova (XLSX print-ready) adicionada
- v0.6 refactor descartada em favor de v0.5.1 patch cirúrgico
- Bloco A migra de Bruna manual no Excel pra agente Cowork via openpyxl
- B7 novo (smoke 30 parcelas em PRICE 36x) adicionado"
git push origin main
```

---

## Passo 1 — Prompt de abertura pra colar no Cowork

Cola isso assim que a sessão abrir:

```
Vou implementar a v0.5.1 patch da Calculadora de Ação Crefaz.

Estado:
- v0.5.0 está em main com tag pushada
- Decisões D1-D6 fechadas em 2026-04-28 (sessão Cowork anterior)
- Plano de execução completo está no repo

Antes de qualquer ação, lê estes 3 arquivos pra ter contexto completo:
1. apps/clientes/02_rose/calculo-acao-crefaz/docs/RETOMAR.md
2. apps/clientes/02_rose/calculo-acao-crefaz/docs/template-modifications-v0.5.1-FINAL.md
3. .claude/memory/calculo-acao-crefaz.md

Depois, executa nessa ordem (sem pedir OK a cada passo — só pra:
"executei Bloco A com sucesso, vou pra Bloco B" e "todos os testes verdes,
pronto pra commit"):

═══ Bloco A — Modificações no template via openpyxl ═══

1. Cria scripts/aplica_v0.5.1.py — script idempotente
2. Implementa A1 → A12 do plano (todos os passos do Bloco A do FINAL.md)
3. Roda o script: PYTHONPATH=src .venv/bin/python scripts/aplica_v0.5.1.py
4. Confirma com A12 (validação pós-execução)
5. Backup automático: garante que templates/Calculo.original.xlsx existe ANTES
   de salvar templates/Calculo.xlsx novo

═══ Bloco B — Código Python ═══

6. Implementa B1 → B5 (mapeamento D5/D6, defesa em profundidade no number_format,
   confirma B3, log_writer append, testes atualizados)
7. Roda B6 (smoke Adriano + Marlí original)
8. Implementa e roda B7 NOVO (caso hipotético 30 parcelas em PRICE 36x —
   teste mockado em tests/e2e/test_caso_30_parcelas.py)
9. Garante que TODOS os testes passam:
   PYTHONPATH=src .venv/bin/pytest -v

═══ Quando tudo verde ═══

10. Commits separados:
    - commit 1: template (Calculo.xlsx + Calculo.original.xlsx)
    - commit 2: código (planilha.py, log_writer.py, etc)
    - commit 3: testes (incluindo test_caso_30_parcelas.py)
    - commit 4: scripts/aplica_v0.5.1.py (caso ainda não esteja commitado)
11. Tag: git tag -a v0.5.1 -m "v0.5.1 — patch cirúrgico template + print-ready"
12. Push: git push origin main && git push origin v0.5.1

═══ NÃO fazer ═══

- NÃO empacotar .exe — Bruna Scopel faz no ASUS depois
- NÃO mexer em conteúdo jurídico (D4 = manter as 6 seções)
- NÃO adicionar logo, paleta, fonte custom (D3 = zero cosmético)
- NÃO pedir validação à Roselaine (D5 = Bruna Scopel + Advogada Bruna)
- NÃO refatorar pra 1 aba dinâmica (D1 = manter 4 abas)

═══ Quando terminar ═══

Me devolve um resumo telegráfico:
- Quantos testes passaram (deve ser 105+ os novos do B5/B7)
- Quais arquivos mudaram
- Tag e commits criados
- O que falta humano fazer (ex: agendar abrir XLSX com a Advogada Bruna)
```

---

## Passo 2 — O que humano faz depois

1. **Bruna Scopel** abre `templates/Calculo.xlsx` (via Excel real no ASUS) e:
   - Confere visual
   - Faz Ctrl+P → conferir preview de impressão (deve caber em A4 paisagem sem cortar)
   - Roda 1 caso real de cliente da Rose pra confirmar que pipeline preenche tudo correto

2. **Advogada Bruna (funcionária da Rose Portal)** valida:
   - Cálculos célula a célula contra um output v0.5.0 conhecido (Adriano ou Marlí)
   - Datas em formato BR
   - Estrutura jurídica das 6 seções intacta

3. Se ambas aprovarem: comunicar Roselaine que XLSX foi atualizado (apenas ciência).

4. **Bruna Scopel** empacota `.exe` no ASUS quando tiver tempo (ou aguarda v0.7 com GH Actions).

---

## Notas operacionais

- **Por que worktree main e não a branch atual:** o worktree mountado na sessão anterior (Cowork) estava em `feat/benditta-lp-essencial-monorepo`, onde a pasta `calculo-acao-crefaz` está untracked. Implementação precisa rodar onde os arquivos são tracked = main.
- **Os docs já estão consolidados** — não precisa redecidir nada. Os 6 trade-offs (D1-D6) estão fechados.
- **Estimativa de duração da próxima sessão:** ~2-3h se rodar limpo, +1h se aparecer surpresa em openpyxl preservando estilos.
