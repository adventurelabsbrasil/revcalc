# Handoff — Planilha em duas camadas: `DADOS` + `PRICE` (visual / print)

> **Status:** decisão fechada em 2026-04-29 — substitui o plano v0.5.1 cirúrgico (Bloco A openpyxl).
> **Path canônico no repo:** `apps/clientes/02_rose/calculo-acao-crefaz/docs/HANDOFF_PLANILHA_DADOS_VS_VISUAL.md` (em `main`).
> **Origem:** redação do Founder (Rodrigo), versão 2026-04-29, validada contra o código atual.

---

## Objetivo

Separar (1) **fonte de dados** preenchida pelo app Python e (2) **layout visual** idêntico ao atual, pronto pra **prints** e **PDF paisagem** do conteúdo completo (v0.6+ com xlwings/Excel).

---

## Premissa: o código já suporta

Auditoria em `src/calculadora_crefaz/config.py` (linhas 164-181) e `src/calculadora_crefaz/planilha.py` (linhas 121-159) — confirmado em 2026-04-29:

- `NOME_ABA_DADOS = "DADOS"` definido em `config.py`.
- `CELULAS_DADOS` mapeia 13 campos para `B2:B14` na aba DADOS (mapa abaixo).
- `gerar_xlsx`:
  - Linha 141: `usa_dados = NOME_ABA_DADOS in wb.sheetnames` — detecção automática por presença da aba.
  - Linha 142-143: preserva `DADOS` ao remover abas não-usadas.
  - Linha 146-153: bifurca — se DADOS existe, chama `_preencher_aba_dados` (escreve só em `DADOS!B2:B14`); senão, comportamento legacy (`_preencher_aba` na PRICE).
- `_preencher_aba_dados` (linhas 102-118) já popula os 13 campos, incluindo `data_calculo` (B14) e `ultimo_vencimento` (B5) — campos que o legacy não persiste.

**Implicação:** se `templates/Calculo.xlsx` ganhar uma aba `DADOS`, o app passa pro modo novo automaticamente, sem mudança de código. Se a aba não existir, continua legacy. Migração é reversível por add/remove da aba.

---

## 1. Mapa da aba `DADOS` (contrato com o código)

| Campo lógico        | Célula | Tipo            |
|---------------------|--------|-----------------|
| título operação     | `B2`   | texto           |
| data emissão        | `B3`   | data            |
| 1º vencimento       | `B4`   | data            |
| último vencimento   | `B5`   | data            |
| valor principal     | `B6`   | número (R$)     |
| TAC / tarifas       | `B7`   | número (R$)     |
| IOF                 | `B8`   | número (R$)     |
| qtd parcelas        | `B9`   | inteiro         |
| valor prestação     | `B10`  | número (R$)     |
| taxa pactuada       | `B11`  | decimal (0,1449)|
| taxa BACEN          | `B12`  | decimal         |
| parcelas pagas      | `B13`  | inteiro         |
| data do cálculo     | `B14`  | data            |

**Coluna A (recomendado):** rótulos em pt-BR (“Data de emissão”, “1º vencimento”, …) para leitura humana. O app **não** depende de A.

Se precisar mudar células: alterar **`CELULAS_DADOS` em `config.py`** e este handoff **juntos**, no mesmo commit.

---

## 2. Trabalho no template Calculo.xlsx

> **Executor desta migração:** Cowork via computer-use no Excel local do Mac do Founder (decisão 2026-04-29). Rodrigo mantém o Excel aberto com o template enquanto Claude opera. Validação a cada passo: capturar screenshot e conferir.

### Sequência

1. **Backup pré-migração**
   - Copiar `templates/Calculo.xlsx` → `templates/Calculo.original.xlsx` (Finder ou shell `cp`) **antes** de qualquer edição. Backup é o gate de reversão.

2. **Inserir aba `DADOS`** no início do livro (primeira aba)
   - Botão direito numa aba existente → "Inserir" → "Planilha" → mover pra primeira posição.
   - Renomear pra `DADOS` exatamente (case-sensitive).

3. **Preencher coluna A da DADOS** com 13 labels
   - `A2` "Título da operação", `A3` "Data de emissão", `A4` "1º vencimento", `A5` "Último vencimento", `A6` "Valor principal", `A7` "TAC / tarifas", `A8` "IOF", `A9` "Quantidade de parcelas", `A10` "Valor da prestação", `A11` "Taxa pactuada", `A12` "Taxa BACEN", `A13` "Parcelas pagas", `A14` "Data do cálculo".
   - Coluna B fica vazia em B2:B14 — será preenchida pelo app.

4. **Aplicar number_format por tipo na coluna B**
   - `B3, B4, B5, B14` (datas) → `dd/mm/yyyy`
   - `B6, B7, B8, B10` (R$) → `R$ #,##0.00`
   - `B11, B12` (taxas decimais) → `0,00%` (Excel multiplica por 100 ao exibir; valor armazenado é 0,1449 = 14,49%)
   - `B9, B13` (inteiros) → `0`

5. **Em CADA aba PRICE (24X, 36x, 48x, 60x), substituir valores cravados por fórmulas `=DADOS!$B$X`**

   Endereços a substituir (offset +1 entre PRICE 24X e as outras 3):

   | Campo                | PRICE 24X | PRICE 36x/48x/60x | Fórmula a colocar |
   |----------------------|-----------|-------------------|-------------------|
   | Título               | `C1`      | `C1`              | `=DADOS!$B$2`     |
   | Data pactuação       | `D3`      | `D4`              | `=DADOS!$B$3`     |
   | 1º Vencimento        | `D5`      | `D6`              | `=DADOS!$B$4`     |
   | Valor principal      | `I7`      | `I8`              | `=DADOS!$B$6`     |
   | TAC                  | `I9`      | `I10`             | `=DADOS!$B$7`     |
   | IOF                  | `I13`     | `I14`             | `=DADOS!$B$8`     |
   | Qtd parcelas         | `I15`     | `I16`             | `=DADOS!$B$9`     |
   | Valor prestação      | `I16`     | `I17`             | `=DADOS!$B$10`    |
   | Taxa pactuada        | `I17`     | `I18`             | `=DADOS!$B$11`    |
   | Taxa BACEN           | `AP15`    | `AP16`            | `=DADOS!$B$12`    |
   | Parcelas pagas       | `BL8`     | `BL9`             | `=DADOS!$B$13`    |

   **Observação:** as 4 PRICE referenciam o **mesmo** `DADOS!$B$X` — uma única fonte de verdade.

6. **Limpar dados hardcoded da Jaqueline na PRICE 24X**
   - `D132:D146` atualmente contém datas hardcoded. Apagar tudo (Delete na seleção).

7. **Estender tabela PRICE 24X de 15 → 24 linhas**
   - Selecionar `C132:N146` → copiar formatação (Format Painter) pra `C147:N155`.
   - `C147:C155` → preencher números 16, 17, …, 24.

8. **Popular coluna D das 4 PRICE com IF+EDATE**
   - PRICE 24X (`D132:D155`):
     - `D132` = `=IF($C132<=DADOS!$B$9, DADOS!$B$4, "")`
     - `D133` = `=IF($C133<=DADOS!$B$9, EDATE(DADOS!$B$4, $C133-1), "")`
     - Arrastar `D133` até `D155`.
   - PRICE 36x (`D133:D168`), 48x (`D133:D180`), 60x (`D133:D192`):
     - `D133` = `=IF($C133<=DADOS!$B$9, DADOS!$B$4, "")`
     - `D134` = `=IF($C134<=DADOS!$B$9, EDATE(DADOS!$B$4, $C134-1), "")`
     - Arrastar até a última row da aba.

9. **Popular coluna N (Parcela cobrada) com IF condicional**
   - PRICE 24X (`N132:N155`): `=IF($C132<=DADOS!$B$9, DADOS!$B$10, "")` — arrastar.
   - PRICE 36x/48x/60x (`N133:N…`): mesma fórmula.

10. **Replicar D nas colunas AE e BF (já existentes no template)**
    - `AE132` = `=D132` (24X) ou `AE133` = `=D133` (outras) — arrastar até última row.
    - `BF132` = `=AE132` (24X) ou `BF133` = `=AE133` (outras) — arrastar.

11. **Apagar sujeira em PRICE 60x D4**
    - `D4` da PRICE 60x tem string `'30/102024'` (resíduo cliente antigo). Deletar.

12. **Number format em massa: todas as datas → `dd/mm/yyyy`**
    - Selecionar coluna D inteira em cada PRICE → format → `dd/mm/yyyy`.
    - Idem AE, BF nas mesmas faixas.

13. **Page setup uniforme nas 4 PRICE (D6 = print-ready)**
    - Para cada PRICE: Layout → Orientação Paisagem → A4.
    - Layout → "Ajustar à largura: 1 página" / "Altura: automática".
    - Margens: Estreitas (top/bot 0,3 cm, left/right 0,7 cm — equivalente a margens ABNT comprimidas).
    - Layout → "Definir Área de Impressão" abrangendo tabela completa de cada aba (testar com Visualização de Impressão).

14. **(Opcional) Esconder aba DADOS pro Ctrl+P não imprimi-la**
    - Botão direito na aba `DADOS` → "Ocultar". Impressão pula DADOS naturalmente; valores continuam acessíveis pro app via fórmula.

15. **Salvar como `templates/Calculo.xlsx`** (sobrescreve o atual).
    - Backup `Calculo.original.xlsx` continua intacto da etapa 1.

---

## 3. Saída do app (Drive) com DADOS ativada

Com `DADOS` presente, o ficheiro gerado em runtime terá **2 abas**:
1. `DADOS` (com B2:B14 preenchidas pelo app, A inalterada).
2. A PRICE do prazo (`PRICE 24X` se prazo ≤ 24, `36x` se 25-36, etc).

As outras 3 PRICE são removidas automaticamente em `_remover_abas_nao_usadas` (linha 49-52 de `planilha.py`).

Se DADOS estiver oculta, o XLSX final mantém ela oculta — o usuário final só vê a aba PRICE.

---

## 4. Bloco residual de código (CLI / sessão futura)

A maior parte do Bloco B do plano v0.5.1 **caiu** porque a arquitetura DADOS resolve mapeamento, formato e print. Sobra trabalho residual de polimento que entra num commit separado:

### B-residual

1. **`_set_date_cell` defensivo** — já implementado em `planilha.py` linhas 69-73 (`cell.number_format = "dd/mm/yyyy"`). **Validar com teste**, não reescrever.

2. **`log_writer.py` em modo append** — comportamento aprovado por Rodrigo:
   - Se `12 Log.txt` existe: lê, concatena `\n\n` + (`=`*60) + `\n\n` + bloco novo, escreve.
   - Se não existe: escreve só o bloco.

3. **Smoke `test_caso_30_parcelas.py`** — caso mockado de 30 parcelas (cai em PRICE 36x):
   - Mock contrato com `prazo=30`, `primeiro_vencimento=2026-05-01`, `valor_prestacao=500.00`.
   - Rodar `gerar_xlsx`, validar XLSX final tem aba DADOS preenchida (B9=30, B4=2026-05-01, B10=500.00) + aba PRICE 36x única + page setup landscape.
   - Reabrir o XLSX final com openpyxl com `data_only=True` (forçar recálculo) é tricky — alternativa: validar só o conteúdo de DADOS, e visualmente em Excel real depois.

4. **Atualizar testes existentes** — `tests/test_planilha.py` precisa cobrir o novo modo:
   - Caso template com aba DADOS → escreve em B2:B14, **não** toca PRICE.
   - Caso template sem aba DADOS (legacy) → escreve nas células PRICE como antes.
   - Garantir que ambos cenários passam.

5. **Smoke E2E Adriano + Marlí** — re-rodar com template novo e confirmar XLSX final tem números idênticos aos da v0.5.0 (cálculo é igual, mudou só a forma de chegar nos valores).

### Critério de done do CLI

- Tag `v0.5.1` criada após template novo + B-residual estarem em `main`.
- Commit do template separado do commit do código (auditável).

---

## 5. Prints / PDF completo (roadmap)

- **v0.5.x:** só geração XLSX; sem capturas PNG na pasta cliente.
- **v0.6:** fluxo Windows + xlwings: imprimir/registrar **aba visual** (DADOS oculta na captura).
- PDF paisagem "conteúdo completo": usar **área de impressão** já definida na PRICE ou export range xlwings → PDF.

---

## 6. Verificação rápida após migração

```bash
cd apps/clientes/02_rose/calculo-acao-crefaz
PYTHONPATH=src .venv/bin/pytest tests/ -q
```

Se testes falharem:
- **Asserts antigos contra células PRICE diretas:** os valores ainda devem ser idênticos pelas fórmulas. Se diverge, é referência quebrada (fórmula apontando pra célula errada da DADOS) ou typo no endereço PRICE.
- **Asserts contra `DADOS!B2:B14`:** garantir que o teste carrega o XLSX gerado e lê de DADOS quando a aba existe.

---

## 7. Prompt curto pra retomada futura

```
No repo 01_ADVENTURE_LABS, projeto apps/clientes/02_rose/calculo-acao-crefaz.
Migrar templates/Calculo.xlsx para modelo de duas abas conforme
docs/HANDOFF_PLANILHA_DADOS_VS_VISUAL.md: aba DADOS com mapa B2:B14
em config.CELULAS_DADOS; abas PRICE só com fórmulas apontando para DADOS;
manter layout visual e print area paisagem.
Validar com pytest tests/test_planilha.py.
```

---

## 8. O que mudou em relação ao plano v0.5.1 anterior

| Item | Plano v0.5.1 cirúrgico (SUPERSEDED) | Plano DADOS+visual (este) |
|------|--------------------------------------|---------------------------|
| Editor do template | openpyxl em script `aplica_v0.5.1.py` | Cowork via computer-use no Excel real |
| Mapeamento de campos | D5/D6 nas PRICE direto | DADOS!B4 (única) com PRICE referenciando |
| Tabela parcelas | IF+EDATE escritos via openpyxl | IF+EDATE digitados no Excel humano |
| Page setup | openpyxl ajusta `page_setup.*` | Excel UI ajusta com preview real |
| Risco de regressão visual | médio (openpyxl perde estilo) | baixo (XML preservado pelo Excel) |
| Reprodutibilidade | alta (script versionado) | baixa (registro só no commit do XLSX binário) |
| Auditoria das mudanças | git diff do script | screenshots + commit do XLSX |
| Bloco B (código) | extenso: mapeamento + log + format + smoke | reduzido: só log append + smoke + testes do dual-mode |

A perda de reprodutibilidade é o principal trade-off. Mitigação: **este handoff é o roteiro versionado**. Se o template precisar ser regenerado do zero, alguém segue passo 1-15 daqui no Excel.

---

## Apêndice — armadilhas técnicas (preservadas do _handoff_ anterior)

1. **Offset +1** entre PRICE 24X e as outras 3 abas — respeitado na tabela do passo 5.
2. **Limites das tabelas:** PRICE 24X até row 155 (após estender), 36x até 168, 48x até 180, 60x até 192.
3. **PRICE 48x estava em portrait no template** — passo 13 corrige.
4. **PRICE 60x D4 com sujeira `'30/102024'`** — passo 11 limpa.
5. **Tkinter no Python do brew quebra UI** — usar `.venv` do projeto (já configurado).
6. **OAuth Google Drive** no workspace `roseportaladvocacia.com.br` — `.env` gitignored, não tocar.
7. **Histórico em `12 Log.txt` agora é append** — vai pro Bloco B-residual.
8. **Dedup via `10 Cálculo*.xlsx`** na pasta cliente — flag `--force` pula confirmação.
9. **openpyxl pode perder cell styles** — não aplica ao caminho atual (Excel preserva XML 100%).
10. **Calculo.original.xlsx é o backup pré-migração** — passo 1, mantém. Não é versionado se já não estava.
