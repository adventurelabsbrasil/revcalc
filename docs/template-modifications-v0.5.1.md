# Modificações no template `Calculo.xlsx` — v0.5.1

> **Audiência:** Bruna (executa no Excel do ASUS) + agente CLI (faz as mudanças de código)
> **Versão:** v0.5.1
> **Data:** 2026-04-28
> **Status:** plano fechado, aguardando execução

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

Já documentado em sessão anterior: PRICE 48x está em **portrait**, todas as outras em **landscape**. Código atual força landscape com warning, mas vale corrigir no template direto pra evitar warning desnecessário.

---

## Plano de execução

### Bloco A — Trabalho no Excel (Bruna ou Founder com Excel)

**Pré-requisito:** abrir `templates/Calculo.xlsx` no Excel do ASUS. **Não usar Numbers** (pode quebrar formatação de fórmulas e cell styles que o openpyxl precisa preservar).

#### A1. PRICE 24X — adicionar célula "Data do 1º Vencimento"

1. Ir pra aba `PRICE 24X`
2. Em `C5`, escrever: **`Data do 1º vencimento:`**
3. Em `D5`, deixar vazio (será preenchido pelo sistema). Aplicar formato de data BR: clique direito → Formatar células → Personalizado → digitar `dd/mm/yyyy`
4. Copiar a formatação visual de `C3` (mesma fonte, alinhamento, cor de fundo) pra `C5`
5. Copiar a formatação visual de `D3` pra `D5`

#### A2. PRICE 36x/48x/60x — adicionar célula "Data do 1º Vencimento"

Repetir o mesmo procedimento de A1 nas 3 abas, mas usando linha 6:

1. Em `C6`, escrever: **`Data do 1º vencimento:`**
2. Em `D6`, vazio com formato `dd/mm/yyyy`
3. Replicar formatação visual de `C4`/`D4` da própria aba

#### A3. PRICE 24X — estender tabela de 15 pra 24 linhas

1. Selecionar as **rows 132 a 146 inteiras** (a tabela completa)
2. Copiar (Ctrl+C)
3. Selecionar `C147` e colar (Ctrl+V) — Excel deve auto-ajustar fórmulas relativas
4. **Editar manualmente a coluna C**:
   - `C147 = 16`
   - `C148 = 17`
   - `C149 = 18`
   - `C150 = 19`
   - `C151 = 20`
   - `C152 = 21`
   - `C153 = 22`
   - `C154 = 23`
   - `C155 = 24`
5. Idem coluna `AD147:AD155` (mesma sequência 16-24)
6. Idem coluna `BE147:BE155` (mesma sequência 16-24)

> **Verificar após colar:** clicar em `N147` deve mostrar `=N146`, `N148` deve mostrar `=N147`, etc. Se Excel mantiver as referências absolutas erradas, ajustar manualmente.

#### A4. PRICE 24X — substituir datas hardcoded pela fórmula EDATE

Substituir os valores de `D132:D146` por fórmulas referenciando a nova `D5`. **Incluir IF condicional pra ocultar parcelas além do prazo (`I15`):**

| Célula | Fórmula |
|--------|---------|
| `D132` | `=IF(C132<=$I$15, $D$5, "")` |
| `D133` | `=IF(C133<=$I$15, EDATE($D$5, C133-1), "")` |
| `D134` | `=IF(C134<=$I$15, EDATE($D$5, C134-1), "")` |
| ... | (continua a fórmula até `D155`) |
| `D155` | `=IF(C155<=$I$15, EDATE($D$5, C155-1), "")` |

> **Por que `EDATE($D$5, C-1)` e não `EDATE(D anterior, 1)`:** se uma célula intermediária retorna `""` (vazio), `EDATE("", 1)` quebra. Calculando sempre a partir de `D5`, mantém a chain robusta.

#### A5. PRICE 36x/48x/60x — preencher coluna D vazia

Preencher `D133` até a última linha de cada aba com fórmula análoga, **referenciando `D6` em vez de `D5`**:

| Aba | Fórmulas |
|-----|----------|
| PRICE 36x | `D133 = =IF(C133<=$I$16, $D$6, "")` ... até `D168` |
| PRICE 48x | `D133 = =IF(C133<=$I$16, $D$6, "")` ... até `D180` |
| PRICE 60x | `D133 = =IF(C133<=$I$16, $D$6, "")` ... até `D192` |

> **Atenção ao offset +1:** nas outras abas, "Quantidade de parcelas" está em `I16` (não `I15`). Isso é o offset +1 já documentado.

Para `D134` em diante:
- `D134 = =IF(C134<=$I$16, EDATE($D$6, C134-1), "")`
- ... até a última linha da aba.

#### A6. Adicionar IF condicional na coluna N (Parcela cobrada)

Para que a coluna "Parcela cobrada" também oculte linhas além do prazo:

**PRICE 24X** (rows 132-155):
- `N132 = =IF(C132<=$I$15, $I$16, "")`
- `N133 = =IF(C133<=$I$15, $I$16, "")`
- ... (mesma fórmula em todas, referenciando `I16`)

**PRICE 36x/48x/60x:**
- `N133 = =IF(C133<=$I$16, $I$17, "")`
- ... (referenciando `I17` por causa do offset +1)

#### A7. Trocar number_format de TODAS as datas pra `dd/mm/yyyy`

Aplicar formato `dd/mm/yyyy` em:

**PRICE 24X:**
- `D3`, `D4`, `D5` (cabeçalho)
- `D132:D155` (coluna Vencimento)
- `AE132:AE155` (coluna Vencimento da tabela "Recalculadas")
- `BF132:BF155` (coluna Vencimento da tabela "Valores Pagos")

**PRICE 36x:**
- `D4`, `D5`, `D6`
- `D133:D168`, `AE133:AE168`, `BF133:BF168`

**PRICE 48x:**
- `D4`, `D5`, `D6`
- `D133:D180`, `AE133:AE180`, `BF133:BF180`

**PRICE 60x:**
- `D4`, `D5`, `D6`
- `D133:D192`, `AE133:AE192`, `BF133:BF192`

> **Atalho no Excel:** selecionar tudo, Ctrl+1, Personalizado, digitar `dd/mm/yyyy`, OK.

#### A8. PRICE 48x — corrigir page setup

1. Aba `PRICE 48x` → Layout da Página
2. Orientação: **Paisagem**
3. Tamanho: **A4** (paperSize 9, igual às outras)

#### A9. Limpar dado bagunçado em PRICE 60x

Em `D4` da aba `PRICE 60x` está a string `'30/102024'` (resíduo de um cliente antigo, com erro de digitação). Apagar — vai ser preenchido pelo sistema.

#### A10. Salvar e validar

1. Salvar como `Calculo.xlsx` (mesmo nome, sobrescreve)
2. Fechar e reabrir no Excel pra confirmar que não há fórmulas quebradas (`#REF!`, `#NAME?`, etc)
3. Manter backup do template original em `templates/Calculo.original.xlsx`

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

Mesmo com o template já corrigido, aplicar `number_format = "dd/mm/yyyy"` ao escrever em todas as células de data via openpyxl. Se Bruna esquecer de salvar o template com o formato certo, o código corrige.

```python
cell = sh[coord]
cell.value = data_value
if tipo == "date":
    cell.number_format = "dd/mm/yyyy"
```

#### B3. NÃO escrever na coluna D da tabela de parcelas

A coluna D da tabela (D132 em diante) agora é **fórmula**, não input. O sistema **não deve tocar** nessas células. Confirmar que `MAPEAMENTO_*` só inclui células de cabeçalho e inputs, não a tabela de parcelas.

#### B4. Atualizar `log_writer.py` — append em vez de sobrescrever

Mudança aprovada por Rodrigo: cada execução adiciona bloco novo no final do `12 Log.txt` em vez de sobrescrever.

```python
def escrever_log(path, dados, ...):
    novo_bloco = render_bloco(dados)  # já existe
    
    # NOVO: ler conteúdo existente (se houver) e prepender
    if path.existe():
        conteudo_anterior = path.ler()
        conteudo_final = conteudo_anterior + "\n\n" + "="*60 + "\n\n" + novo_bloco
    else:
        conteudo_final = novo_bloco
    
    path.escrever(conteudo_final)
```

Cada bloco já tem cabeçalho com timestamp e usuário — fica claro qual é qual.

#### B5. Atualizar testes

Adicionar asserts no `test_planilha.py` que validem:
- Nova célula `D5` (24X) ou `D6` (outras) tem o valor de `primeiro_vencimento`
- Number format das datas é `dd/mm/yyyy`
- Coluna D132+ permanece como **fórmula** (não foi sobrescrita)
- Cabeçalho da tabela de parcelas permanece em C131
- Adriano (12) não exibe linhas 13-24 com valor (a fórmula `IF` retorna `""`)
- Marlí (18) exibe linhas 1-18 com valor e 19-24 vazias

Adicionar teste no `test_log_writer.py` que valide o comportamento de append.

#### B6. Re-rodar smoke E2E

1. Smoke Adriano: validar que XLSX final mostra exatamente 12 parcelas com datas começando em 27/10/2025 e datas em formato BR
2. Smoke Marlí: validar 18 parcelas com datas começando em 02/02/2026 em formato BR
3. Validar no Excel real (via Bruna ou no Mac via LibreOffice/Numbers só pra abrir, não editar)

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

### Caso hipotético — contrato 30 parcelas (cairia em PRICE 36x)

| Célula | Valor esperado |
|--------|---------------|
| `D6` | data do 1º vencimento |
| `I16` | 30 (quantidade — offset +1) |
| `D133` | 1ª parcela = =IF(1<=30, $D$6, "") |
| `D162` | 30ª parcela = =IF(30<=30, EDATE($D$6, 29), "") |
| `D163` | 31ª (não existe) = =IF(31<=30, ..., "") → vazio ✓ |
| `D168` | 36ª = vazio ✓ |

---

## Checklist final de validação (depois das modificações)

Ordem sugerida:

- [ ] Bruna executou Bloco A (A1 a A10) no Excel
- [ ] Template versionado: original como backup, novo como `Calculo.xlsx`
- [ ] Agente CLI executou Bloco B (B1 a B5)
- [ ] Smoke Adriano passou: tabela com 12 linhas, datas em BR, 1ª venc 27/10/2025
- [ ] Smoke Marlí passou: tabela com 18 linhas, datas em BR, 1ª venc 02/02/2026
- [ ] Bruna validou os 2 XLSX finais no Excel real (visual, impressão)
- [ ] Log do Adriano + Marlí mostra append funcionando se rodar 2x
- [ ] Commit + tag `v0.5.1`

---

## Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| Excel não preserva fórmulas relativas ao colar | Validação manual do A3 — clicar em algumas células coladas pra conferir |
| Fórmula `EDATE` retorna número (serial date) em vez de data formatada | Aplicar `dd/mm/yyyy` na célula explicitamente (Bloco A7) |
| Bruna usa Numbers ou LibreOffice em vez de Excel | Reforçar pré-requisito — só Excel preserva 100% das features |
| Fórmula `IF(..., "")` pode causar problema em soma `=SUM(N132:N155)` se exigir número | Usar `=IFERROR(SUM(N132:N155), 0)` em qualquer célula que somar a tabela |
| Substituir Calculo.xlsx pode quebrar testes que comparam contra hash do template | Commit separado pra template + atualizar fixtures de teste se houver |
| openpyxl não consegue escrever fórmula `EDATE` | Não vai precisar — fórmulas EDATE moram no template, código só preenche `D5`/`D6` |

---

## Pendências fora deste escopo (vão pra v0.6+)

- **Audit visual**: paleta de cores pra distinguir input de fórmula, hierarquia visual de seções, label "PERCENTUAL DA TAXA COBRADADA SUPERIOR A MÉDIA" → "Excesso sobre média BACEN".
- **Branding Adventure Labs**: rodapé Tkinter, log.txt, XLSX, README.
- **GH Actions Win-only**: build automático do .exe a cada tag.
- **Capturas xlwings**: dependem de Excel local (Bruna).

---

## Apêndice: comando de verificação pós-template

Depois que Bruna entregar o template modificado, rodar localmente pra validar fórmulas:

```bash
cd apps/clientes/02_rose/calculo-acao-crefaz
PYTHONPATH=src .venv/bin/python -c "
from openpyxl import load_workbook
wb = load_workbook('templates/Calculo.xlsx')
sh = wb['PRICE 24X']
print('D5:', sh['D5'].value, '|', sh['D5'].number_format)
print('D132:', sh['D132'].value, '|', sh['D132'].number_format)
print('D155:', sh['D155'].value, '|', sh['D155'].number_format)
print('C155:', sh['C155'].value)
print('N132:', sh['N132'].value)
print('N155:', sh['N155'].value)
"
```

Saída esperada:

```
D5: None | dd/mm/yyyy
D132: =IF(C132<=$I$15, $D$5, "") | dd/mm/yyyy
D155: =IF(C155<=$I$15, EDATE($D$5, C155-1), "") | dd/mm/yyyy
C155: 24
N132: =IF(C132<=$I$15, $I$16, "")
N155: =IF(C155<=$I$15, $I$16, "")
```
