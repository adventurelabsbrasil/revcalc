# Prompt-mestre — Claude Code CLI (Cursor) — Bloco B residual pós-migração DADOS

> **Contexto:** o template `Calculo.xlsx` já está migrado para arquitetura DADOS+visual (relatório em `_handoff-v0.5.1-2026-04-28/RELATORIO_MIGRACAO_DADOS.md`). Esse prompt cobre só o trabalho **residual de código** — log append, smoke 30 parcelas, testes do dual-mode, commits, tag.
>
> **Onde abrir o CLI:** worktree `01_ADVENTURE_LABS-main/`, branch `main`, com `git pull` recente.
>
> **Pré-condição:** os 3 arquivos do `_handoff/` (template novo, snapshot pré-DADOS, script de migração) já devem ter sido copiados pra `main` e commitados — ver passo 1 do `RUNBOOK_HUMANO_v2_DADOS.md`.

---

## Como usar

1. Garante que `main` está com os 3 arquivos do template/scripts já commitados (passo 1 do runbook v2).
2. No Cursor, abre `01_ADVENTURE_LABS-main/`, abre terminal integrado.
3. Roda `claude` (ou `claude code`).
4. Cola **somente o conteúdo entre `═══ PROMPT ═══` e `═══ FIM DO PROMPT ═══`**.
5. Larga rodando ~45-90min. Recebe resumo telegráfico.

---

## ═══ PROMPT ═══

```
Você é o agente que vai fechar o Bloco B residual da v0.5.1 da Calculadora de Ação Crefaz. O template já foi migrado pra arquitetura DADOS+visual em sessão Cowork anterior — ver relatório no repo. Sua tarefa é só código + testes + commits + tag. Sem perguntas intermediárias, sem confirmações — vá até o fim ou até um blocker real, devolva resumo telegráfico.

═══ Estado atual ═══

- v0.5.0 está em main (tag pushada, 105 testes verdes, smoke E2E real OK).
- Template `templates/Calculo.xlsx` já migrado pra DADOS+visual (aba DADOS oculta com B2:B14 + 44 fórmulas =DADOS!$B$X nas 4 PRICE). Recalc com LibreOffice deu 0 erros.
- `templates/Calculo.preDADOS.xlsx` é o snapshot pré-migração (reversão).
- `templates/Calculo.original.xlsx` é o snapshot v0.5.0 pré-cirúrgica.
- `scripts/migrar_para_dados.py` é o script idempotente da migração (já rodado).
- Código `src/calculadora_crefaz/planilha.py` já tem `_preencher_aba_dados` e detecção automática (`usa_dados = NOME_ABA_DADOS in wb.sheetnames`). Lógica dual-mode pronta — só falta exercitar com testes.
- `src/calculadora_crefaz/config.py` tem `CELULAS_DADOS` mapeando 13 campos pra B2:B14.

═══ Leitura obrigatória antes de codar ═══

1. apps/clientes/02_rose/calculo-acao-crefaz/_handoff-v0.5.1-2026-04-28/HANDOFF_PLANILHA_DADOS_VS_VISUAL.md
2. apps/clientes/02_rose/calculo-acao-crefaz/_handoff-v0.5.1-2026-04-28/RELATORIO_MIGRACAO_DADOS.md
3. apps/clientes/02_rose/calculo-acao-crefaz/src/calculadora_crefaz/planilha.py (entender dual-mode)
4. apps/clientes/02_rose/calculo-acao-crefaz/src/calculadora_crefaz/log_writer.py (estado atual)
5. apps/clientes/02_rose/calculo-acao-crefaz/tests/test_planilha.py
6. apps/clientes/02_rose/calculo-acao-crefaz/tests/test_log_writer.py (se existir; senão, criar)

═══ Trabalho ═══

▸ B1. log_writer.py — modo append

  Comportamento atual: provavelmente sobrescreve `12 Log.txt` a cada execução. Mudar pra append:
  - Se arquivo existe: lê conteúdo anterior, concatena com `\n\n` + ("=" * 60) + `\n\n` + bloco novo.
  - Se não existe: escreve só o bloco.
  Manter encoding utf-8. Não mudar o formato do bloco em si.

▸ B2. tests/test_log_writer.py

  Adicionar/atualizar teste:
  - Caso 1: arquivo não existe → escreve bloco.
  - Caso 2: arquivo existe → adiciona separador + bloco novo no final, preservando bloco anterior.
  - Caso 3 (regression): rodar duas vezes seguidas, verificar que bloco anterior está intacto.

▸ B3. tests/test_planilha.py — cobrir dual-mode

  Adicionar 2 cenários:
  - Cenário "template com DADOS" (ler `templates/Calculo.xlsx` real): após `gerar_xlsx`, o XLSX gerado deve ter aba DADOS com B2:B14 preenchidos com valores do contrato; aba PRICE NN do prazo presente; outras 3 PRICE removidas; nenhuma célula PRICE de input foi sobrescrita pelo app (continua como fórmula =DADOS!$B$X).
  - Cenário "template sem DADOS" (ler `templates/Calculo.preDADOS.xlsx`): após `gerar_xlsx`, comportamento legacy — escreve direto na PRICE NN nas células de `celulas_para_aba(aba)`.

  Reaproveitar fixtures existentes (Adriano, Marlí). Asserts mais importantes:
  - `wb["DADOS"]["B9"].value == contrato.prazo`
  - `wb["DADOS"]["B4"].value == contrato.primeiro_vencimento`
  - `wb["PRICE 24X"]["I15"].value` (modo DADOS) deve ser `'=DADOS!$B$9'` (string fórmula) — NÃO o número 12.

▸ B4. tests/e2e/test_caso_30_parcelas.py

  Caso mockado novo:
  - Mock contrato com prazo=30, primeiro_vencimento=2026-05-01, valor_prestacao=500.00, taxa_mensal=0.18, valor_nominal=12000, tarifas=80, tributos_iof=120 (valores fictícios).
  - Mock taxa_bacen=0.0558, parcelas_pagas=0, data_calculo=2026-04-29.
  - Chama `gerar_xlsx`, recebe bytes, abre via openpyxl com BytesIO.
  - Asserts:
    - Sheetnames == ["DADOS", "PRICE 36x"] (ou apenas as 2; ordem pode variar)
    - DADOS!B9 == 30, B4 == datetime(2026,5,1), B10 == 500.00
    - PRICE 36x I16 == "=DADOS!$B$9" (string fórmula)
    - PRICE 36x D6 == "=DADOS!$B$4"
    - DADOS sheet_state == "hidden"
    - PRICE 36x page_setup.orientation == "landscape"

▸ B5. Smoke E2E Adriano + Marlí — re-validar com template novo

  Se houver script orquestrador de smoke E2E no projeto, rodá-lo. Se não, executar manualmente:
  ```
  PYTHONPATH=src .venv/bin/python -c "
  from datetime import date
  from calculadora_crefaz.planilha import DadosPlanilha, gerar_xlsx
  # ... montar DadosPlanilha de Adriano / Marlí com fixtures existentes ...
  bytes_xlsx = gerar_xlsx(dados)
  open('/tmp/adriano.xlsx', 'wb').write(bytes_xlsx)
  "
  ```
  Confirmar via openpyxl que o XLSX gerado tem DADOS preenchida e PRICE 24X com fórmulas resolvendo (precisa abrir com data_only=True após algum tipo de recálculo — ou só inspecionar fórmulas e confiar no recalc anterior).

▸ B6. Rodar suíte completa

  PYTHONPATH=src .venv/bin/pytest -v
  Esperado: 105 antigos + ~5-7 novos passando. Zero falhas.

▸ B7. Commits + tag + push

  Commits separados:
  - commit 1: "build(crefaz): migrate template to DADOS+visual architecture"
    Arquivos: templates/Calculo.xlsx, templates/Calculo.preDADOS.xlsx, scripts/migrar_para_dados.py
  - commit 2: "feat(crefaz): log_writer in append mode"
    Arquivos: src/calculadora_crefaz/log_writer.py
  - commit 3: "test(crefaz): cover dual-mode (DADOS + legacy) and 30-installments smoke"
    Arquivos: tests/test_planilha.py, tests/test_log_writer.py, tests/e2e/test_caso_30_parcelas.py
  - commit 4: "docs(crefaz): consolidate D1-D6 + DADOS migration handoff"
    Arquivos: apps/clientes/02_rose/calculo-acao-crefaz/_handoff-v0.5.1-2026-04-28/* (e cópia em docs/ se aplicável)

  Tag:
  git tag -a v0.5.1 -m "v0.5.1 — DADOS+visual: template em duas camadas, log append, dual-mode tests"

  Push:
  git push origin main && git push origin v0.5.1

═══ O que NÃO fazer ═══

- NÃO mexer no template (já foi migrado pelo Cowork — relatório no _handoff/).
- NÃO mexer em conteúdo jurídico, identidade visual, número de abas.
- NÃO commitar `.env`, OAuth tokens, secrets.
- NÃO empacotar .exe — Bruna Scopel faz no ASUS quando puder.
- NÃO pedir validação à Roselaine (D5: gate técnico é Bruna Scopel + Advogada Bruna).
- NÃO mudar `_preencher_aba_dados` ou `_preencher_aba` em planilha.py — eles já estão corretos.

═══ Critérios de done ═══

[ ] log_writer em append mode + teste passando
[ ] test_planilha cobre dual-mode (template com DADOS + template legacy via Calculo.preDADOS.xlsx)
[ ] test_caso_30_parcelas existe e passa
[ ] smoke E2E Adriano + Marlí re-validado (XLSX gerado tem DADOS preenchida + PRICE 24X com fórmulas)
[ ] Suíte completa: 110+ testes passando, zero falhas
[ ] 4 commits separados criados
[ ] Tag v0.5.1 criada
[ ] Push origin main + tag

═══ Output esperado (telegráfico) ═══

> v0.5.1 entregue (DADOS+visual).
> Testes: X passando (Y novos).
> Commits: <hash1> template, <hash2> log_writer, <hash3> testes, <hash4> docs.
> Tag: v0.5.1 → <hash>.
> Pushed: origin/main + tag.
> Arquivos novos: scripts/migrar_para_dados.py, templates/Calculo.preDADOS.xlsx, tests/e2e/test_caso_30_parcelas.py, _handoff-v0.5.1-2026-04-28/* (4 arquivos).
> Arquivos modificados: templates/Calculo.xlsx, src/calculadora_crefaz/log_writer.py, tests/test_planilha.py, tests/test_log_writer.py.
> Surpresas: <livre — esperado: nenhuma; possível: openpyxl serialização de fórmulas em formato esperado pelos asserts>.
> Gate humano pendente:
>   1. Bruna Scopel — abrir Calculo.xlsx no Excel/Numbers, conferir visual + Ctrl+P.
>   2. Advogada Bruna — comparar XLSX gerado v0.5.1 vs v0.5.0 (números idênticos esperados).
> Próximos passos: comunicar Roselaine (ciência); empacotar .exe quando Bruna Scopel tiver janela.

═══ Se algo falhar ═══

- Se um teste antigo quebrar e for regressão real (não fixture stale): pare, reporte com pytest -v completo, aguarde instrução.
- Se openpyxl ler `=DADOS!$B$9` como string mas o app via `wb["PRICE 24X"]["I15"].value` retornar algo diferente do esperado: investigar diferenças entre `data_only=True/False` ao carregar.
- Se `git pull` tiver conflito: pare e reporte.
- Se aparecer pedido de credencial OAuth: o `.env` está em `01_ADVENTURE_LABS-main/apps/clientes/02_rose/calculo-acao-crefaz/.env` (gitignored).

Agora execute. Vai até o fim.
```

## ═══ FIM DO PROMPT ═══
