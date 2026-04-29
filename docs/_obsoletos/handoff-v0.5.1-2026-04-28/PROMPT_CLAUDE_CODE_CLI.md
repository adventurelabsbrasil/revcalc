# Prompt-mestre — Claude Code CLI (Cursor) — finalização v0.5.1

> ⚠️ **SUPERSEDED em 2026-04-29.** Este prompt orientava a v0.5.1 cirúrgica completa (Bloco A openpyxl + Bloco B código). O Bloco A foi descartado a favor da arquitetura **DADOS+visual** (template já migrado pelo Cowork). Bloco B foi reduzido — ver `PROMPT_CLI_RESIDUAL.md` e `HANDOFF_PLANILHA_DADOS_VS_VISUAL.md`. Mantido por contexto histórico.

---

> **Como usar:** Rodrigo abre o terminal do Cursor no worktree `01_ADVENTURE_LABS-main/`, roda `claude` (ou `claude code`), e cola **TUDO** que está dentro do bloco `═══ PROMPT ═══` abaixo. O que vem antes do bloco é instrução pra você (Rodrigo); o que vem dentro é o que o agente lê.
>
> **Pré-condição:** os 3 arquivos do handoff (`RETOMAR.md`, `template-modifications-v0.5.1-FINAL.md`, este arquivo) já devem ter sido copiados pra `apps/clientes/02_rose/calculo-acao-crefaz/docs/` em `main` e commitados antes de abrir o CLI. Veja `RUNBOOK_HUMANO.md` passo 1.
>
> **O que o CLI consegue fazer (e por isso este prompt é apropriado):** filesystem real, Bash real (git, pytest, openpyxl), pode rodar scripts, abrir XLSX local, validar com `python -m calculadora_crefaz`, criar commits e push. Não precisa pedir confirmação a cada passo — opera autônomo até o gate humano (Bruna).

---

## ═══ PROMPT ═══

```
Você é o agente que vai finalizar o MVP da Calculadora de Ação Crefaz na versão v0.5.1 (patch cirúrgico). O escopo está completamente fechado — não redecida nada, execute. Quando terminar, devolva resumo telegráfico pro Founder.

═══ Contexto mínimo ═══

- Projeto: Adventure Labs / cliente Rose Portal Advocacia / produto interno "Calculadora de Ação Crefaz"
- Estado: v0.5.0 em produção lógica (tag v0.5.0 no commit 0deec0d, pushed em origin/main, 105 testes verdes, smoke E2E real OK)
- Meta v0.5.1: corrigir bugs visuais do template Calculo.xlsx (datas em formato US, tabela com nº fixo de linhas, vencimentos errados em PRICE 36x/48x/60x) + deixar XLSX print-ready (A4 paisagem, fit-to-page) — sem refactor estrutural, sem cosmético novo
- Decisões D1-D6 já fechadas em sessão Cowork de 2026-04-28 (não revisitar)
- Validação humana final: Bruna Scopel (sócia/esposa) abre o XLSX no Excel real + Advogada Bruna (funcionária da Rose) confere cálculos célula a célula. NÃO pedir validação à Roselaine (cliente final).

═══ Leitura obrigatória antes de qualquer linha de código ═══

Leia nesta ordem (todos relativos à raiz do monorepo):

1. apps/clientes/02_rose/calculo-acao-crefaz/docs/RETOMAR.md
2. apps/clientes/02_rose/calculo-acao-crefaz/docs/template-modifications-v0.5.1-FINAL.md  ← plano completo, é a fonte de verdade
3. apps/clientes/02_rose/calculo-acao-crefaz/README.md  (visão geral + uso)
4. apps/clientes/02_rose/calculo-acao-crefaz/src/calculadora_crefaz/planilha.py  (entender o mapeamento atual antes de mexer)
5. apps/clientes/02_rose/calculo-acao-crefaz/src/calculadora_crefaz/log_writer.py
6. apps/clientes/02_rose/calculo-acao-crefaz/templates/Calculo.xlsx  (inspecione com openpyxl, NÃO reescreva ainda)

═══ Armadilhas técnicas conhecidas (memorize antes de tocar em código) ═══

1. **Offset +1 entre PRICE 24X e as outras 3 abas.**
   - Em PRICE 24X: Quantidade de parcelas em I15, Valor da parcela em I16, Taxa em I17. Tabela de parcelas começa na row 132. Célula nova "Data do 1º vencimento" vai em D5.
   - Em PRICE 36x/48x/60x: Quantidade em I16, Valor em I17, Taxa em I18. Tabela começa na row 133. Célula nova vai em D6.
   - Esse offset é regra do template, não bug. Respeitá-lo nas fórmulas IF e EDATE.

2. **Limites de cada tabela (última row preenchida):**
   - PRICE 24X → row 155 (depois de estender de 146 pra 155 no passo A3)
   - PRICE 36x → row 168
   - PRICE 48x → row 180
   - PRICE 60x → row 192

3. **Datas em US contaminam o template todo.** 124 células com number_format `mm-dd-yy`. O passo A7 troca pra `dd/mm/yyyy` em massa. Mas o código (B2) deve aplicar `dd/mm/yyyy` defensivamente em qualquer célula de data que escrever — não confiar só no template.

4. **Coluna D da tabela de parcelas vira fórmula.** Antes era valor hardcoded da Jaqueline. Depois de A4/A5, é `=IF(C<=$I$15, EDATE($D$5, C-1), "")`. Código NÃO deve sobrescrever D132+ — confirmar em B3 que `MAPEAMENTO_*` só inclui cabeçalho e inputs.

5. **PRICE 60x D4 tem sujeira hardcoded** — string `'30/102024'` (resíduo de cliente antigo). Apagar no passo A9.

6. **Tkinter no Python do brew quebra na UI.** Se o smoke E2E exigir UI, usar o `.venv` do projeto (já configurado com tk binding correto). Não rodar via python do sistema. PYTHONPATH=src .venv/bin/python ... é o invocador padrão.

7. **OAuth Google Drive interno do workspace `roseportaladvocacia.com.br`.** O `.env` tem `GOOGLE_OAUTH_CLIENT_ID` e secret. Está gitignored. Login com `roselaine@roseportaladvocacia.com.br` no Mac do Founder pra debug; em produção a Bruna usa o email dela. NÃO commitar credenciais.

8. **Histórico em `12 Log.txt` agora é append** — cada execução acrescenta bloco no final separado por `="*60` (passo B4). Não sobrescrever o arquivo inteiro.

9. **Dedup via verificação de `10 Cálculo*.xlsx` na pasta da cliente.** Flag `--force` pula a confirmação. Não mexer nesse contrato.

10. **openpyxl pode perder cell styles sutis** — toleramos (D3 = zero cosmético). Se notar quebra crítica de borda/sombreado durante A1-A11, registrar no resumo final mas seguir.

═══ Plano de execução ═══

Siga `docs/template-modifications-v0.5.1-FINAL.md` literalmente. Resumo da sequência (sem perder o detalhe do plano):

▸ BLOCO A — modificações no template via openpyxl

  1. Crie scripts/aplica_v0.5.1.py — script idempotente que executa A1 a A11 em ordem.
     - Helper copy_cell_style(src, dst) preservando font, fill, border, alignment, number_format.
     - Backup automático: copia templates/Calculo.xlsx pra templates/Calculo.original.xlsx ANTES de salvar (só se backup ainda não existir — idempotência).
     - Salva templates/Calculo.xlsx no final.
     - Termina executando A12 (validação) e imprime relatório.

  2. Rode o script:
     PYTHONPATH=src .venv/bin/python scripts/aplica_v0.5.1.py

  3. Confira a saída do A12 contra o "esperado" do plano (D5 vazia com formato dd/mm/yyyy, D132 com fórmula IF, C155=24, page orientation=landscape, fitToWidth=1).

  4. Se algo divergir, NÃO siga pro Bloco B. Pare, reporte o diff e aguarde instrução. Se tudo ok, prossiga.

▸ BLOCO B — código Python

  5. Edite src/calculadora_crefaz/planilha.py — adicione mapeamento D5 (PRICE 24X) e D6 (outras abas) → dados.primeiro_vencimento, com tipo "date".

  6. Confirme que dados.primeiro_vencimento existe na dataclass. Se não existir, propague desde parser_contrato.py (provavelmente já existe — auditar).

  7. Adicione defesa em profundidade: ao escrever data em qualquer cell via openpyxl, force `cell.number_format = "dd/mm/yyyy"`.

  8. Confirme em planilha.py que MAPEAMENTO_* NÃO inclui D132+ (a tabela de parcelas é fórmula, intocável).

  9. Edite src/calculadora_crefaz/log_writer.py — comportamento append:
     - Se arquivo existe: lê, concatena com `\n\n` + ("="*60) + `\n\n` + bloco novo.
     - Se não existe: escreve só o bloco.

  10. Atualize tests/ adicionando asserts pros novos comportamentos:
      - test_planilha.py: D5/D6 recebem primeiro_vencimento; number_format das datas é dd/mm/yyyy; D132+ não foi tocada (continua fórmula); page setup das 4 abas é landscape A4 fitToWidth=1.
      - test_log_writer.py: append funciona — ler 2x e validar separador.

  11. Crie tests/e2e/test_caso_30_parcelas.py — caso mockado de 30 parcelas (cai em PRICE 36x):
      - quantidade_parcelas=30, primeiro_vencimento=01/05/2026, valor_parcela=500.00
      - valida XLSX final: aba PRICE 36x escolhida; D6=01/05/2026 BR; D133..D162 com EDATE crescente; D163..D168 vazias; N133..N162=500; N163..N168 vazias.

  12. Rode TODA a suíte:
      PYTHONPATH=src .venv/bin/pytest -v
      Esperado: 105+ testes passando (105 antigos + os novos do B5 e B7).

  13. Re-rode o smoke E2E original (se houver script orquestrador) ou execute manualmente o pipeline com os fixtures do Adriano (12 parcelas, 1ª venc 27/10/2025) e Marlí (18 parcelas, 1ª venc 02/02/2026). Validar que XLSX final mostra datas em formato BR e tabela com o nº correto de linhas preenchidas.

▸ COMMITS, TAG, PUSH

  14. Commits separados (uma mudança lógica por commit):
      - commit 1: "build(crefaz): apply v0.5.1 template patch via openpyxl"
        Arquivos: templates/Calculo.xlsx + templates/Calculo.original.xlsx + scripts/aplica_v0.5.1.py
      - commit 2: "feat(crefaz): add primeiro_vencimento mapping + log append + dd/mm/yyyy defense"
        Arquivos: src/calculadora_crefaz/planilha.py, log_writer.py
      - commit 3: "test(crefaz): cover v0.5.1 changes (D5/D6, log append, 30-installments smoke)"
        Arquivos: tests/test_planilha.py, test_log_writer.py, e2e/test_caso_30_parcelas.py
      - commit 4 (opcional, se docs ainda não estavam): "docs(crefaz): consolidate D1-D6 decisions and v0.5.1 plan"

  15. Tag:
      git tag -a v0.5.1 -m "v0.5.1 — patch cirúrgico: template print-ready + datas BR + tabela parametrizada"

  16. Push:
      git push origin main && git push origin v0.5.1

═══ O que NÃO fazer ═══

- NÃO empacotar .exe. Bruna Scopel faz isso no ASUS dela manualmente até v0.7 ficar pronto.
- NÃO mexer no conteúdo jurídico. As 6 seções permanecem exatamente como estão (D4).
- NÃO adicionar logo, paleta nova, fonte custom, header/footer com branding Adventure Labs (D3 = zero cosmético).
- NÃO refatorar pra 1 aba dinâmica. Manter as 4 abas (D1).
- NÃO pedir validação à Roselaine. O gate técnico é Bruna Scopel + Advogada Bruna (D5).
- NÃO commitar `.env`, OAuth tokens, ou qualquer secret.
- NÃO subir Calculo.original.xlsx pro repo se ele já estava lá em v0.5.0 — verifique antes; se não estava, suba (é o backup pré-patch).

═══ Critérios de done ═══

[ ] scripts/aplica_v0.5.1.py existe, é idempotente, rodou sem warning crítico
[ ] templates/Calculo.original.xlsx existe (backup pré-patch)
[ ] templates/Calculo.xlsx tem: D5/D6 nova com formato dd/mm/yyyy; tabela 24X estendida até row 155; coluna D das 4 abas com fórmula IF+EDATE; N com IF condicional; PRICE 60x D4 limpa; page setup uniforme landscape A4 fitToWidth=1
[ ] A12 (validação openpyxl) passou contra o esperado documentado
[ ] planilha.py mapeia D5 (24X) e D6 (outras) pra primeiro_vencimento
[ ] log_writer.py em modo append
[ ] Todos os testes passam (105+ esperados)
[ ] test_caso_30_parcelas.py existe e passa
[ ] Smoke E2E Adriano + Marlí re-validados
[ ] 4 commits separados criados
[ ] Tag v0.5.1 criada e pushed
[ ] origin/main + tags atualizados

═══ Output esperado (telegráfico, no fim) ═══

Quando terminar, responda exatamente neste formato:

> v0.5.1 entregue.
> Testes: X passando (Y novos).
> Commits: <hash1> template, <hash2> código, <hash3> testes [, <hash4> docs].
> Tag: v0.5.1 → <hash>.
> Pushed: origin/main + tag.
> Arquivos novos: scripts/aplica_v0.5.1.py, tests/e2e/test_caso_30_parcelas.py, templates/Calculo.original.xlsx.
> Arquivos modificados: templates/Calculo.xlsx, src/.../planilha.py, src/.../log_writer.py, tests/test_planilha.py, tests/test_log_writer.py.
> Surpresas/divergências: <livre>.
> Gate humano pendente:
>   1. Bruna Scopel — abrir Calculo.xlsx no Excel real, conferir visual + Ctrl+P (PDF preview).
>   2. Advogada Bruna — validar cálculos célula a célula contra um output v0.5.0 conhecido (Adriano ou Marlí).
> Próximos passos sugeridos: comunicar Roselaine que XLSX foi atualizado (ciência apenas); agendar empacotamento .exe quando Bruna Scopel tiver janela.

═══ Se algo falhar ═══

- Se o A12 mostrar divergência: pare, reporte diff exato (esperado vs obtido por célula), aguarde instrução. Não tente "consertar criativamente".
- Se um teste antigo quebrar: investigar se é regressão ou se a fixture ficou stale por causa do template novo. Se for fixture, regenerar; se for regressão, pare e reporte.
- Se openpyxl perder estilo crítico: registrar antes/depois (screenshot do XLSX no Mac via `qlmanage -t` ou só descrição textual), reportar no resumo final, mas NÃO interromper se for cosmético menor (D3 cobre).
- Se `git pull` tiver conflito: parar e reportar.
- Se algum smoke E2E exigir credencial Google e ela não estiver no .env local: parar e pedir ao Founder.

Agora execute. Sem perguntas, sem confirmações intermediárias — vá até o fim ou até um blocker real.
```

## ═══ FIM DO PROMPT ═══

---

## Notas sobre este prompt

**Por que ele é auto-suficiente:**
- Cita os 3 docs canônicos por path absoluto dentro do repo (não depende de URLs ou conversas anteriores).
- Inlinearmos as 10 armadilhas técnicas porque o `.claude/memory/calculo-acao-crefaz.md` mencionado no handoff antigo **não existe** no monorepo principal — caso contrário o CLI tentaria ler um arquivo fantasma.
- Define explicitamente o que NÃO fazer (cinco "não") porque o CLI tende a sugerir melhorias cosméticas; o escopo aqui é cirúrgico.
- O formato de output telegráfico foi padronizado pra você conferir done sem ler a saída inteira.

**Por que não pedimos OK intermediário:**
- O Bloco A roda local, idempotente, com backup automático — reversível em 1 comando.
- O Bloco B é coberto por testes — se quebrar, é detectado.
- O gate humano vem depois (Bruna Scopel + Advogada), não no meio da execução.
- Pedidos intermediários quebrariam o fluxo no Cursor e te custariam tempo voltando ao terminal.

**Único ponto de pausa explícito:** se A12 divergir do esperado, o agente para e reporta. Esse é o único checkpoint técnico onde o agente pode ter alucinado num copy de cell style.
