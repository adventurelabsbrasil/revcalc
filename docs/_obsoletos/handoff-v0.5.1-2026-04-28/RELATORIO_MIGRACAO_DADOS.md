# Relatório — migração DADOS+visual concluída

> **Sessão:** Cowork 2026-04-29 (Rodrigo + Cowork via skill `xlsx`)
> **Objetivo:** ativar arquitetura `DADOS` + `PRICE` no template `Calculo.xlsx` sem mudança de código (o app já suporta dual-mode desde commit anterior).
> **Status:** ✅ entregue, validado matemática e estruturalmente.

---

## Estado descoberto na auditoria pré-migração

Auditoria do `templates/Calculo.xlsx` em 2026-04-29 revelou que **a v0.5.1 cirúrgica já estava aplicada** no template (em sessão anterior não documentada):

- PRICE 24X: tabela estendida até row 155, fórmulas `IF(...)` em D132:D155 e N132:N155, format `dd/mm/yyyy` em todas as datas
- PRICE 36x/48x/60x: fórmulas IF+EDATE em D, IF condicional em N
- 4 abas com page setup uniforme: orientation=landscape, paper=A4 (9), fitToWidth=1, print_area definido até CC
- PRICE 60x D4 já limpa (sem `'30/102024'`)
- `scripts/aplica_v0.5.1.py` presente — confirma execução prévia

Snapshot v0.5.0 (pré-cirúrgica) preservado em `templates/Calculo.original.xlsx` (294 KB).

Snapshot v0.5.1 cirúrgica (pré-DADOS) salvo em `templates/Calculo.preDADOS.xlsx` (235 KB) pra reversão se necessário.

---

## O que foi feito nesta sessão (delta DADOS+visual)

Script `scripts/migrar_para_dados.py` (idempotente — aborta se aba `DADOS` já existir):

1. **Criou aba `DADOS` na primeira posição**, oculta (`sheet_state="hidden"`):
   - A1:B1: cabeçalho "Campo / Valor" em negrito com fundo cinza
   - A2:A14: 13 labels em pt-BR (Título da operação, Data de emissão, 1º vencimento, …)
   - B2:B14: vazias com `number_format` por tipo:
     - Datas (B3, B4, B5, B14): `dd/mm/yyyy`
     - Currency (B6, B7, B8, B10): `R$ #,##0.00`
     - Percentage (B11, B12): `0.00%`
     - Inteiro (B9, B13): `0`
     - Texto (B2): `@`

2. **44 substituições** nas 4 PRICE — valores cravados → fórmulas `=DADOS!$B$X`:

   | Aba | Células substituídas |
   |-----|---------------------|
   | PRICE 24X | C1, D3, D5, I7, I9, I13, I15, I16, I17, AP15, BL8 |
   | PRICE 36x | C2, D4, D6, I8, I10, I14, I16, I17, I18, AP16, BL9 |
   | PRICE 48x | idem PRICE 36x |
   | PRICE 60x | idem PRICE 36x |

   `number_format` original de cada célula PRICE foi preservado (R$, %, dd/mm/yyyy etc).

3. **Não tocou** nas fórmulas da tabela de parcelas (D132+, N132+, AE132+, BF132+) — elas já apontam pra `$D$5`, `$I$15`, `$I$16` (na 24X) ou `$D$6`, `$I$16`, `$I$17` (nas outras), e Excel resolve transitivamente após D5/D6/I... virarem fórmulas DADOS.

4. **Não tocou** em page setup, print area, conteúdo jurídico, identidade visual.

---

## Validação matemática (caso Adriano)

Populamos `DADOS!B2:B14` com valores fictícios do caso Adriano (12 parcelas, 1ª venc 27/10/2025, valor parcela 226.79, taxa pactuada 18.77%, taxa BACEN 5.58%, 3 parcelas pagas), simulamos `gerar_xlsx` removendo as 3 PRICE não-usadas (mantendo só DADOS + PRICE 24X, como o app faz em runtime), e rodamos `scripts/recalc.py` da skill `xlsx` (LibreOffice headless).

**Resultado: 220 fórmulas resolvidas, 0 erros** (sem `#REF!`, `#NAME?`, `#DIV/0!`, `#VALUE!`, `#N/A`).

| Célula PRICE 24X | Esperado | Obtido | OK |
|------------------|----------|--------|----|
| C1 (título)      | "CÁLCULOS DA OPERAÇÃO Nº 1234567 - CLIENTE: ADRIANO TESTE x BANCO CREFAZ" | idêntico | ✓ |
| D3 (data emissão)| 22/09/2025 | 22/09/2025 | ✓ |
| D5 (1º venc)     | 27/10/2025 | 27/10/2025 | ✓ |
| I7 (valor princ.)| 2500.00 | 2500.00 | ✓ |
| I15 (qtd)        | 12 | 12 | ✓ |
| I16 (valor parc.)| 226.79 | 226.79 | ✓ |
| I17 (taxa pact.) | 18.77% | 18.77% | ✓ |
| AP15 (taxa BACEN)| 5.58% | 5.58% | ✓ |
| BL8 (parc. pagas)| 3 | 3 | ✓ |
| D132 (parcela 1) | 27/10/2025 | 27/10/2025 | ✓ |
| D133 (parcela 2) | 27/11/2025 | 27/11/2025 | ✓ |
| D138 (parcela 7) | 27/04/2026 | 27/04/2026 | ✓ |
| D143 (parcela 12)| 27/09/2026 | 27/09/2026 | ✓ |
| D144 (parcela 13)| vazio (IF retorna "") | None | ✓ |
| D155 (parcela 24)| vazio | None | ✓ |
| AE132, BF132     | replicam D132 | replicam | ✓ |
| N132 (cobrada)   | 226.79 | 226.79 | ✓ |
| N143 (cobrada 12)| 226.79 | 226.79 | ✓ |
| N144 (cobrada 13)| vazio | None | ✓ |

Cálculos derivados (RATE, NPER, valores cobrados em outras seções, totais Pagos vs Devidos) também resolveram sem erro.

---

## Arquivos entregues

No workspace folder (`apps/clientes/02_rose/calculo-acao-crefaz/`):

| Arquivo | Função | Status |
|---------|--------|--------|
| `templates/Calculo.xlsx` | Template novo (DADOS oculta + 4 PRICE com fórmulas DADOS) | substitui |
| `templates/Calculo.preDADOS.xlsx` | Snapshot v0.5.1 cirúrgica pré-migração DADOS — pra reversão | adiciona |
| `templates/Calculo.original.xlsx` | Snapshot v0.5.0 pré-cirúrgica — preservado | mantido |
| `scripts/migrar_para_dados.py` | Script idempotente da migração | adiciona |
| `scripts/aplica_v0.5.1.py` | Script da v0.5.1 cirúrgica (já existia) | mantido |
| `_handoff-v0.5.1-2026-04-28/HANDOFF_PLANILHA_DADOS_VS_VISUAL.md` | Documento canônico da decisão | adiciona |
| `_handoff-v0.5.1-2026-04-28/RELATORIO_MIGRACAO_DADOS.md` | Este relatório | adiciona |

Marcados como SUPERSEDED (mantidos por contexto histórico):
- `_handoff-v0.5.1-2026-04-28/PROMPT_PURO_PARA_COLAR.md`
- `_handoff-v0.5.1-2026-04-28/PROMPT_CLAUDE_CODE_CLI.md`
- `_handoff-v0.5.1-2026-04-28/RUNBOOK_HUMANO.md`

---

## Comportamento esperado em produção

Quando o app `gerar_xlsx` rodar com este template:

1. `usa_dados = "DADOS" in wb.sheetnames` → `True`
2. `_remover_abas_nao_usadas` mantém `DADOS` + `PRICE NN` (a do prazo do contrato).
3. `_preencher_aba_dados` escreve em `DADOS!B2:B14` com valores do contrato.
4. As fórmulas `=DADOS!$B$X` na PRICE resolvem automaticamente quando o XLSX é aberto no Excel.
5. PRICE permanece com `sheet_state="visible"`; DADOS permanece `hidden`.
6. Bruna (ou cliente final) abre → vê só a PRICE com tudo preenchido. Ctrl+P → PDF paisagem A4 print-ready.

---

## O que falta (Bloco B residual — vai pro CLI/Cursor)

Trabalho de código desacoplado da migração do template:

1. **`log_writer.py` — modo append** (separar execuções por `="*60`).
2. **Smoke `tests/e2e/test_caso_30_parcelas.py`** — caso 30 parcelas (PRICE 36x) no modo DADOS.
3. **Atualizar testes existentes** — cobrir cenário "template com aba DADOS" vs "template sem aba DADOS" (legacy).
4. **Re-rodar smoke E2E Adriano + Marlí** — confirmar números idênticos a v0.5.0 com template novo.
5. **Commits + tag v0.5.1**.

Ver `PROMPT_CLI_RESIDUAL.md` (gerado nesta sessão) pra o prompt auto-suficiente que Rodrigo cola no Claude Code CLI dentro do Cursor.

---

## Ações humanas pendentes

1. **Mover arquivos pra `main`** (worktree `01_ADVENTURE_LABS-main/`):
   - Copiar `templates/Calculo.xlsx`, `templates/Calculo.preDADOS.xlsx`, `scripts/migrar_para_dados.py`, e os docs do `_handoff/` pra `main`.
   - Commits separados (template + script + docs).

2. **Rodar Bloco B residual via Claude Code CLI** (ver `PROMPT_CLI_RESIDUAL.md`).

3. **Validação humana após CLI terminar:**
   - **Bruna Scopel**: abrir `Calculo.xlsx` no Excel real → confirmar que renderiza visual ok + Ctrl+P mostra preview correto em paisagem A4. (Se o ASUS não tiver Excel, validar via Numbers do Mac — pode haver leve degradação de fórmula visualização, mas zero impacto no XLSX final do cliente que é aberto no Excel da Rose.)
   - **Advogada Bruna (Rose Portal)**: confirmar que XLSX gerado por um caso real (Adriano ou Marlí) tem números idênticos aos da v0.5.0. Cálculo é igual, mudou só a forma de chegar (input direto na PRICE → input na DADOS, fórmulas resolvem o mesmo).

4. **Após ambas validarem**: comunicar Roselaine (ciência apenas, não validação técnica — D5).

5. **Empacotamento `.exe`**: Bruna Scopel quando tiver janela no ASUS, ou aguardar v0.7 (GH Actions Win-only build automático).
