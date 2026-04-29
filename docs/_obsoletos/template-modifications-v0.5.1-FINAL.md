# Modificações no template `Calculo.xlsx` — v0.5.1 (FINAL)

> **Audiência:** Agente Cowork/CLI (executa Bloco A via openpyxl e Bloco B no código) + Bruna Scopel + Advogada Bruna (validam)
> **Versão:** v0.5.1 (patch cirúrgico, **não** v0.6 refactor)
> **Data:** 2026-04-28 (decisões fechadas em sessão Cowork de 2026-04-28)
> **Status:** plano fechado, todas as 5 decisões D1-D5 + D6 fechadas
> **Substitui:** `template-redesign-brief.md` (v0.6 abandonada por desnecessária)

## Decisões fechadas (cristalizadas em 2026-04-28)

| ID | Decisão | Resultado |
|----|---------|-----------|
| **D1** | Estrutura de abas | **A — Manter 4 abas** (24X / 36x / 48x / 60x) |
| **D2** | Mexer em `planilha.py` | **A — Preservado**, só ganha mapeamento adicional + defesa em profundidade |
| **D3** | Identidade visual | Sem ID nova, sem logo, sem fonte custom, zero cosmético — manter look atual |
| **D4** | Conteúdo jurídico | Manter as 6 seções exatas |
| **D5** | Validação final | **Bruna Scopel + Advogada Bruna (funcionária da Rose) validam** (substitui Roselaine como gate técnico) |
| **D6** | Print/save final | **XLSX print-ready** — page setup uniforme, A4 paisagem em todas, print area, fit-to-page. Bruna abre + Ctrl+P → PDF pronto |
| **Executor** | Quem modifica o template | Agente Cowork via **openpyxl** (não Bruna manualmente no Excel) |

Princípio operacional: **MVP é rigor estrutural nos dados, não redesign visual.**

## Por que essas modificações

Os smokes E2E da v0.5.0 passaram nos campos do **cabeçalho** (cédula, valor, taxa, parcelas, etc), mas não validaram a **tabela "PARCELAS CONFORME O CONTRATO"**. Quando Rodrigo abriu os XLSX gerados, encontrou:

| Bug | Sintoma | Cliente afetado |
|-----|---------|-----------------|
| Tabela com nº fixo de linhas | Adriano (12 parcelas) viu 15 linhas; Marlí (18) viu 15 | Todos com prazo ≠ 15 |
| Datas em formato US (`m/d/yyyy`) | `9/22/2025` em vez de `22/09/2025` | Todos |
| Datas dos vencimentos do cliente errado | Adriano com 1ª parcela em `23/08/2025` (era da Jaqueline) | Todos que usam PRICE 24X |
| Coluna de Vencimento vazia | Quando o sistema escolhe PRICE 36x/48x/60x, a coluna sai em branco | Contratos > 24 parcelas |

A causa-raiz é que o template foi montado a partir do XLSX de um cliente real (Jaqueline da Silva Brum, 12 parcelas, 700 reais) e nunca parametrizado pra ler do contrato. Os dados da Jaqueline ficaram impressos como valores hardcoded e contaminam todo cliente que usa a aba `PRICE 24X`.

## Diagnóstico técnico

### Estrutura atual da PRICE 24X (problema)

A tabela "PARCELAS CONFORME O CONTRATO" começa em `C131` (cabeçalho) e os dados vão de **row 132 até row 146** — apenas **15 linhas**:

| Coluna | Conteúdo atual | Problema |
|--------|---------------|----------|
| `C132:C146` | Números 1 a 15 (hardcoded) | Falta parcelas 16-24 |
| `D132:D146` | Datas hardcoded da Jaqueline (23/08/2025 a 23/10/2026) | Aparecem em qualquer cliente que rode na 24X |
| `D147:D155` | Vazias, sem formatação | Pra contratos de 16-24 parcelas, ficam totalmente em branco |
| `N132` | `=I16` (Valor da parcela) | OK, mas precisa IF condicional pra ocultar quando > prazo |
| `N133:N146` | `=N132`, `=N133`, ... | Idem |

### Estrutura atual das outras 3 abas

PRICE 36x (rows 133-168), 48x (133-180), 60x (133-192) **têm o número correto** de linhas, MAS:

| Coluna | Conteúdo atual | Problema |
|--------|---------------|----------|
| `D133:D[fim]` | Vazias com formato `mm-dd-yy` | Coluna Vencimento sai em branco no XLSX final |
| `N133` | `=I17` (offset +1 confirmado) | OK, mas falta IF condicional |
| `AE133:AE[fim]` | `=D133`, `=D134`, ... (replicam a coluna D) | OK — quando D for preenchida, AE acompanha |
| `BF133:BF[fim]` | `=AE133`, `=AE134`, ... | OK — idem |

### Cabeçalho (rows 1-7)

Confirmado: **linha 5 (PRICE 24X) e linha 6 (outras 3 abas) estão LIVRES** — sem dados, sem mesclagens. Pode acomodar a nova célula "Data do 1º Vencimento" sem mover nada e sem quebrar referências.

| Aba | Posição da célula nova |
|-----|----------------------|
| PRICE 24X | `C5` (label) + `D5` (valor) |
| PRICE 36x | `C6` (label) + `D6` (valor) |
| PRICE 48x | `C6` (label) + `D6` (valor) |
| PRICE 60x | `C6` (label) + `D6` (valor) |

### Number format (formato de data)

Auditoria revelou **124 células com formato US** (`mm-dd-yy`) em todo o template. Maioria está fora da `print_area`, mas as que entram na impressão:

- `D3, D4` (PRICE 24X — Data pactuação, Data cálculo)
- `D4, D5` (outras abas — Data pactuação, Data cálculo)
- `D132:D146` (PRICE 24X — coluna Vencimento)
- `D133:D168/D180/D192` (outras abas — coluna Vencimento)
- `AE` e `BF` correspondentes (replicam D)

Todas precisam virar **`dd/mm/yyyy`**.

### PRICE 48x — page setup

Já documentado em sessão anterior: PRICE 48x está em **portrait**, todas as outras em **landscape**. Código atual força landscape com warning, mas vale corrigir no template direto pra evitar warning desnecessário. **D6 amplia esse ponto:** todas as 4 abas precisam ter page setup uniforme (A4 paisagem, print area, fit-to-page).

---

## Plano de execução

### Bloco A — Modificações no template (executadas via openpyxl pelo agente Cowork)

> **Mudança em relação à versão anterior do plano:** o agente Cowork executa via openpyxl no Mac do Founder, sem depender da Bruna abrir o Excel manualmente. Risco de openpyxl perder formatações sutis é tolerável dado D3=zero cosmético. Reproduzível: vira script em `scripts/aplica_v0.5.1.py`.

#### A1. PRICE 24X — adicionar célula "Data do 1º Vencimento"

```python
sh = wb["PRICE 24X"]
sh["C5"] = "Data do 1º vencimento:"
# D5 fica vazia (será preenchida pelo sistema em runtime)
sh["D5"].number_format = "dd/mm/yyyy"
# Replicar formatação visual de C3/D3
copy_cell_style(sh["C3"], sh["C5"])
copy_cell_style(sh["D3"], sh["D5"])
```

#### A2. PRICE 36x/48x/60x — adicionar célula "Data do 1º Vencimento"

Repetir A1 nas 3 abas, mas usando **linha 6** e replicando a formatação de `C4`/`D4`:

```python
for nome_aba in ["PRICE 36x", "PRICE 48x", "PRICE 60x"]:
    sh = wb[nome_aba]
    sh["C6"] = "Data do 1º vencimento:"
    sh["D6"].number_format = "dd/mm/yyyy"
    copy_cell_style(sh["C4"], sh["C6"])
    copy_cell_style(sh["D4"], sh["D6"])
```

#### A3. PRICE 24X — estender tabela de 15 pra 24 linhas

Copiar formatação das rows 132-146 pras rows 147-155 (estender pra 24 parcelas máximo):

```python
sh = wb["PRICE 24X"]
for new_row in range(147, 156):  # 147 até 155 = parcelas 16 a 24
    src_row = 132 + (new_row - 147) % 15  # cycle through formatting
    for col in ["C", "D", "N", "AE", "BF"]:  # ajustar pra cobrir todas as colunas relevantes
        copy_cell_style(sh[f"{col}132"], sh[f"{col}{new_row}"])
    # Coluna C: número da parcela
    sh[f"C{new_row}"] = new_row - 131  # 16, 17, ..., 24
    # Coluna AE e BF: replicam D
    sh[f"AE{new_row}"] = f"=D{new_row}"
    sh[f"BF{new_row}"] = f"=AE{new_row}"
```

> **Crítico:** validar manualmente após execução que `C147=16`, `C155=24` e que `AE` e `BF` replicam `D`.

#### A4. PRICE 24X — substituir datas hardcoded pela fórmula EDATE

Substituir os valores de `D132:D155` por fórmulas referenciando a nova `D5`. **IF condicional pra ocultar parcelas além do prazo (`I15`):**

```python
sh = wb["PRICE 24X"]
sh["D132"] = '=IF(C132<=$I$15, $D$5, "")'
for row in range(133, 156):  # 133 até 155
    sh[f"D{row}"] = f'=IF(C{row}<=$I$15, EDATE($D$5, C{row}-1), "")'
```

> **Por que `EDATE($D$5, C-1)` e não `EDATE(D anterior, 1)`:** se uma célula intermediária retorna `""` (vazio), `EDATE("", 1)` quebra. Calculando sempre a partir de `D5`, mantém a chain robusta.

#### A5. PRICE 36x/48x/60x — preencher coluna D vazia

```python
limites = {
    "PRICE 36x": 168,
    "PRICE 48x": 180,
    "PRICE 60x": 192,
}
for nome_aba, fim in limites.items():
    sh = wb[nome_aba]
    sh["D133"] = '=IF(C133<=$I$16, $D$6, "")'
    for row in range(134, fim + 1):
        sh[f"D{row}"] = f'=IF(C{row}<=$I$16, EDATE($D$6, C{row}-1), "")'
```

> **Atenção ao offset +1:** nas outras abas, "Quantidade de parcelas" está em `I16` (não `I15`). Esse é o offset +1 documentado em `.claude/memory/calculo-acao-crefaz.md`.

#### A6. Adicionar IF condicional na coluna N (Parcela cobrada)

**PRICE 24X** (rows 132-155):
```python
sh = wb["PRICE 24X"]
for row in range(132, 156):
    sh[f"N{row}"] = f'=IF(C{row}<=$I$15, $I$16, "")'
```

**PRICE 36x/48x/60x:**
```python
for nome_aba, fim in limites.items():
    sh = wb[nome_aba]
    for row in range(133, fim + 1):
        sh[f"N{row}"] = f'=IF(C{row}<=$I$16, $I$17, "")'
```

#### A7. Trocar number_format de TODAS as datas pra `dd/mm/yyyy`

```python
celulas_data = {
    "PRICE 24X": ["D3", "D4", "D5"] + [f"D{r}" for r in range(132, 156)] + [f"AE{r}" for r in range(132, 156)] + [f"BF{r}" for r in range(132, 156)],
    "PRICE 36x": ["D4", "D5", "D6"] + [f"D{r}" for r in range(133, 169)] + [f"AE{r}" for r in range(133, 169)] + [f"BF{r}" for r in range(133, 169)],
    "PRICE 48x": ["D4", "D5", "D6"] + [f"D{r}" for r in range(133, 181)] + [f"AE{r}" for r in range(133, 181)] + [f"BF{r}" for r in range(133, 181)],
    "PRICE 60x": ["D4", "D5", "D6"] + [f"D{r}" for r in range(133, 193)] + [f"AE{r}" for r in range(133, 193)] + [f"BF{r}" for r in range(133, 193)],
}
for nome_aba, celulas in celulas_data.items():
    sh = wb[nome_aba]
    for ref in celulas:
        sh[ref].number_format = "dd/mm/yyyy"
```

#### A8. PRICE 48x — corrigir page setup pra paisagem A4

```python
sh = wb["PRICE 48x"]
sh.page_setup.orientation = sh.ORIENTATION_LANDSCAPE
sh.page_setup.paperSize = sh.PAPERSIZE_A4  # paperSize 9
```

#### A9. Limpar dado bagunçado em PRICE 60x

Em `D4` da aba `PRICE 60x` está a string `'30/102024'` (resíduo de um cliente antigo, com erro de digitação). Apagar:

```python
wb["PRICE 60x"]["D4"] = None
```

#### A10. Salvar template e backup

```python
import shutil
src = Path("templates/Calculo.xlsx")
backup = Path("templates/Calculo.original.xlsx")
if not backup.exists():
    shutil.copy(src, backup)
wb.save(src)
```

#### A11. Page setup uniforme — print-ready (NOVO, decisão D6)

Garantir que **abrir + Ctrl+P** entrega PDF correto sem ajuste manual:

```python
for nome_aba in ["PRICE 24X", "PRICE 36x", "PRICE 48x", "PRICE 60x"]:
    sh = wb[nome_aba]
    # Orientação e tamanho
    sh.page_setup.orientation = sh.ORIENTATION_LANDSCAPE
    sh.page_setup.paperSize = sh.PAPERSIZE_A4
    # Fit to page width = 1, page height = automático (não corta)
    sh.page_setup.fitToWidth = 1
    sh.page_setup.fitToHeight = 0  # 0 = auto
    sh.sheet_properties.pageSetUpPr.fitToPage = True
    # Margens compatíveis com ABNT (cm convertido pra polegada)
    sh.page_margins.left = 0.7 / 2.54
    sh.page_margins.right = 0.7 / 2.54
    sh.page_margins.top = 0.7 / 2.54
    sh.page_margins.bottom = 0.7 / 2.54
    sh.page_margins.header = 0.3 / 2.54
    sh.page_margins.footer = 0.3 / 2.54
    # Print area: confere se já existe ou define usada
    if not sh.print_area:
        # Definir manualmente conforme estrutura conhecida — ajustar por aba
        # ex: sh.print_area = "A1:BO200"
        pass  # validar caso a caso, ver A11.1 abaixo
    # Cabeçalho/rodapé de impressão (opcional — pode incluir cliente + página)
    sh.oddHeader.center.text = "&\"Calibri,Bold\"&14Cálculo de Ação Crefaz"
    sh.oddFooter.right.text = "Página &P de &N"
```

**A11.1 — Print areas a definir:**

Examinar visualmente cada aba e setar `print_area` cobrindo só a região "publicável":
- **PRICE 24X** — provavelmente `A1:BO155` (até última row da tabela + colunas BL/BO da seção "Valores Pagos")
- **PRICE 36x** — `A1:BO168`
- **PRICE 48x** — `A1:BO180`
- **PRICE 60x** — `A1:BO192`

Confirmar com inspeção via `wb["PRICE 24X"].print_area` antes de sobrescrever.

#### A12. Validação pós-execução

```python
from openpyxl import load_workbook
wb = load_workbook("templates/Calculo.xlsx")
sh = wb["PRICE 24X"]
print("D5:", sh["D5"].value, "|", sh["D5"].number_format)
print("D132:", sh["D132"].value, "|", sh["D132"].number_format)
print("D155:", sh["D155"].value, "|", sh["D155"].number_format)
print("C155:", sh["C155"].value)
print("N132:", sh["N132"].value)
print("Page orientation:", sh.page_setup.orientation)
print("Fit to width:", sh.page_setup.fitToWidth)
```

Saída esperada:

```
D5: None | dd/mm/yyyy
D132: =IF(C132<=$I$15, $D$5, "") | dd/mm/yyyy
D155: =IF(C155<=$I$15, EDATE($D$5, C155-1), "") | dd/mm/yyyy
C155: 24
N132: =IF(C132<=$I$15, $I$16, "")
Page orientation: landscape
Fit to width: 1
```

---

### Bloco B — Trabalho no código (agente CLI, sessão v0.5.1)

#### B1. Atualizar `src/calculadora_crefaz/planilha.py`

Adicionar mapeamento da nova célula `D5` (PRICE 24X) ou `D6` (outras abas) com `dados.primeiro_vencimento`.

```python
# pseudo-código — adaptar à estrutura real do planilha.py
MAPEAMENTO_PRICE_24X = {
    # ... existentes ...
    "D5": ("primeiro_vencimento", "date"),  # NOVO
}

MAPEAMENTO_OUTRAS_ABAS = {  # offset +1
    # ... existentes ...
    "D6": ("primeiro_vencimento", "date"),  # NOVO
}
```

Garantir que `dados.primeiro_vencimento` está exposto na dataclass `DadosPlanilha` (provavelmente já está — vem do `parser_contrato.py`).

#### B2. Defesa em profundidade — number_format

Mesmo com o template já corrigido, aplicar `number_format = "dd/mm/yyyy"` ao escrever em todas as células de data via openpyxl:

```python
cell = sh[coord]
cell.value = data_value
if tipo == "date":
    cell.number_format = "dd/mm/yyyy"
```

#### B3. NÃO escrever na coluna D da tabela de parcelas

A coluna D da tabela (D132 em diante) agora é **fórmula**, não input. O sistema **não deve tocar** nessas células. Confirmar que `MAPEAMENTO_*` só inclui células de cabeçalho e inputs, não a tabela de parcelas.

#### B4. Atualizar `log_writer.py` — append em vez de sobrescrever

Mudança aprovada por Rodrigo (decisão cristalizada anterior): cada execução adiciona bloco novo no final do `12 Log.txt` em vez de sobrescrever.

```python
def escrever_log(path, dados, ...):
    novo_bloco = render_bloco(dados)  # já existe

    if path.existe():
        conteudo_anterior = path.ler()
        conteudo_final = conteudo_anterior + "\n\n" + "="*60 + "\n\n" + novo_bloco
    else:
        conteudo_final = novo_bloco

    path.escrever(conteudo_final)
```

#### B5. Atualizar testes

Adicionar asserts no `test_planilha.py` que validem:
- Nova célula `D5` (24X) ou `D6` (outras) tem o valor de `primeiro_vencimento`
- Number format das datas é `dd/mm/yyyy`
- Coluna D132+ permanece como **fórmula** (não foi sobrescrita)
- Cabeçalho da tabela de parcelas permanece em C131
- Adriano (12) não exibe linhas 13-24 com valor (a fórmula `IF` retorna `""`)
- Marlí (18) exibe linhas 1-18 com valor e 19-24 vazias
- **NOVO**: Page setup das 4 abas é landscape A4 com fitToWidth=1 (D6)

Adicionar teste no `test_log_writer.py` que valide o comportamento de append.

#### B6. Re-rodar smoke E2E original

1. Smoke Adriano: validar que XLSX final mostra exatamente 12 parcelas com datas começando em 27/10/2025 e datas em formato BR
2. Smoke Marlí: validar 18 parcelas com datas começando em 02/02/2026 em formato BR
3. Validar no Excel real (via Bruna Scopel ou Mac via LibreOffice/Numbers só pra abrir, não editar)

#### B7. Smoke caso 30 parcelas — exercitar PRICE 36x (NOVO)

O bug das colunas Vencimento vazias era específico de PRICE 36x/48x/60x. B6 só cobre PRICE 24X (Adriano e Marlí). Adicionar **caso hipotético de 30 parcelas** que cai em PRICE 36x:

- Mock contrato com `quantidade_parcelas=30`, primeiro vencimento `01/05/2026`, valor parcela `R$ 500,00`
- Rodar pipeline, validar XLSX final:
  - Aba escolhida: PRICE 36x ✓
  - `D6 = 01/05/2026` (formato BR) ✓
  - Coluna D133 a D162 preenchida com EDATE crescente ✓
  - D163 a D168 = `""` (vazias) ✓
  - Coluna N133 a N162 = `R$ 500,00`, N163 a N168 = `""` ✓
  - Page setup: landscape, fitToWidth=1 ✓

Pode ser teste mockado em `tests/e2e/test_caso_30_parcelas.py` sem depender de PDF real.

---

## Validação cruzada (smoke mental do plano)

### Caso Adriano (12 parcelas, 1º venc 27/10/2025, prazo PRICE 24X)

| Célula | Valor esperado |
|--------|---------------|
| `D3` | 22/09/2025 (Data pactuação, formato BR) |
| `D4` | 28/04/2026 (TODAY()) |
| `D5` | **27/10/2025** (NOVO — 1º Vencimento) |
| `I15` | 12 |
| `I16` | 226,79 |
| `I17` | 18,77% |
| `D132` | =IF(1<=12, $D$5, "") → 27/10/2025 |
| `D133` | =IF(2<=12, EDATE($D$5, 1), "") → 27/11/2025 |
| `D143` | =IF(12<=12, EDATE($D$5, 11), "") → 27/09/2026 |
| `D144` | =IF(13<=12, ..., "") → **vazio** ✓ |
| `D155` | =IF(24<=12, ..., "") → **vazio** ✓ |
| `N132:N143` | 226,79 (12 valores) |
| `N144:N155` | "" vazio (parcelas além do prazo) |

### Caso Marlí (18 parcelas, 1º venc 02/02/2026, prazo PRICE 24X)

| Célula | Valor esperado |
|--------|---------------|
| `D5` | 02/02/2026 |
| `I15` | 18 |
| `D132` | =IF(1<=18, $D$5, "") → 02/02/2026 |
| `D149` | =IF(18<=18, EDATE($D$5, 17), "") → 02/07/2027 |
| `D150` | =IF(19<=18, ..., "") → **vazio** ✓ |
| `N132:N149` | 585,53 (18 valores) |
| `N150:N155` | "" vazio |

### Caso hipotético — 30 parcelas (cai em PRICE 36x) — NOVO B7

| Célula | Valor esperado |
|--------|---------------|
| `D6` | 01/05/2026 (data do 1º vencimento) |
| `I16` | 30 (quantidade — offset +1) |
| `D133` | =IF(1<=30, $D$6, "") → 01/05/2026 |
| `D162` | =IF(30<=30, EDATE($D$6, 29), "") → 01/10/2028 |
| `D163` | =IF(31<=30, ..., "") → **vazio** ✓ |
| `D168` | =IF(36<=30, ..., "") → **vazio** ✓ |
| Page orientation | landscape |
| fitToWidth | 1 |

---

## Checklist final de validação

Ordem sugerida:

- [ ] Agente Cowork executou Bloco A (A1 a A12) via openpyxl
- [ ] Template versionado: `templates/Calculo.original.xlsx` (backup), `templates/Calculo.xlsx` (novo)
- [ ] Agente CLI executou Bloco B (B1 a B7)
- [ ] Smoke Adriano passou: tabela com 12 linhas, datas em BR, 1ª venc 27/10/2025
- [ ] Smoke Marlí passou: tabela com 18 linhas, datas em BR, 1ª venc 02/02/2026
- [ ] **NOVO B7** — Smoke 30 parcelas passou: PRICE 36x, D133-D162 preenchidas, D163-D168 vazias
- [ ] **NOVO D6** — Page setup uniforme nas 4 abas confirmado (landscape, A4, fitToWidth=1)
- [ ] **Bruna Scopel** abriu XLSX no Excel real e conferiu visual + Ctrl+P → PDF correto
- [ ] **Advogada Bruna (funcionária da Rose)** validou cálculos célula a célula contra v0.5.0
- [ ] Log do Adriano + Marlí mostra append funcionando se rodar 2x
- [ ] Commit + tag `v0.5.1`

---

## Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| openpyxl perder cell styles sutis (bordas, sombreado condicional) | D3=zero cosmético tolera. Se aparecer divergência crítica, snapshot visual antes/depois com LibreOffice headless. |
| Fórmula `EDATE` retorna número (serial date) em vez de data formatada | Aplicar `dd/mm/yyyy` na célula explicitamente (Bloco A7) |
| Fórmula `IF(..., "")` pode causar problema em soma `=SUM(N132:N155)` se exigir número | Usar `=IFERROR(SUM(N132:N155), 0)` em qualquer célula que somar a tabela |
| Substituir Calculo.xlsx pode quebrar testes que comparam contra hash do template | Commit separado pra template + atualizar fixtures de teste se houver |
| openpyxl não consegue escrever fórmula `EDATE` | Não vai precisar — fórmulas EDATE moram no template, código só preenche `D5`/`D6` |
| Print area mal definida corta seção do XLSX no Ctrl+P | Validar manualmente A11.1 abaixo. Definir A11 caso a caso por aba via inspeção. |
| Advogada Bruna identifica problema jurídico que demanda mudança de seção | Fora do escopo v0.5.1. Vira v0.6 ou v0.7 com novo brief. |

---

## Pendências fora deste escopo (vão pra v0.6+)

- **Refactor 1 aba dinâmica** — colapsar 4 abas em 1 aba até 60 parcelas (foi a recomendação inicial do Cowork pra D1, descartada em favor da agilidade. Pode voltar à pauta se manutenibilidade virar dor)
- **Audit visual completo** — paleta de cores pra distinguir input de fórmula, hierarquia visual de seções, label "PERCENTUAL DA TAXA COBRADADA SUPERIOR A MÉDIA" → "Excesso sobre média BACEN"
- **Branding Adventure Labs** — rodapé Tkinter, log.txt, XLSX, README
- **GH Actions Win-only** — build automático do .exe a cada tag (v0.7)
- **Capturas xlwings + Excel local** — automação de PNG/PDF (v0.8)
- **Larguras/alturas inconsistentes entre abas** — padronização visual (v0.6 futura, se necessário)
- **Roselaine valida estrutura jurídica das 6 seções** — fora do gate técnico v0.5.1, vira tarefa relacional separada

---

## Apêndice — Origem das decisões

Sessão Cowork de 2026-04-28 fechou em telegrama:

- **D1 = A** (4 abas) — manter; refactor 1 aba dinâmica fica pra v0.6 futura se necessário
- **D2 = A** (planilha.py preservado) — só mapeamento adicional + defesa em profundidade
- **D3** (sem ID visual) — "agilidade e rigor nos dados"; sem cosmético, sem logo, sem fonte custom
- **D4 = A** (manter as 6 seções jurídicas exatas) — refactor não toca conteúdo
- **D5 = Bruna Scopel + Advogada Bruna validam** — substituem Roselaine como gate técnico
- **D6** (NOVO — print-ready XLSX) — page setup uniforme, fit-to-page; Ctrl+P → PDF pronto
- **Executor** — Agente Cowork via openpyxl, **não** Bruna manualmente no Excel
