# Handoff — Planilha em duas camadas: `DADOS` + `PRICE` (visual / print)

**Objetivo:** separar (1) **fonte de dados** preenchida pelo app Python e (2) **layout visual** idêntico ao atual, pronto para **prints** e **PDF paisagem** do conteúdo completo (v0.6+ com xlwings/Excel).

**O código já suporta** a aba `DADOS`: se `templates/Calculo.xlsx` contiver uma aba com esse nome, `gerar_xlsx` **só escreve** em `DADOS` (mapa em `config.CELULAS_DADOS`) e **não** sobrescreve as células de entrada da PRICE — estas devem ser **fórmulas** `=DADOS!$B$n`. Se a aba `DADOS` **não** existir, o comportamento continua **legacy** (preenchimento direto na PRICE, como hoje).

---

## 1. Mapa da aba `DADOS` (contrato com o código)

| Campo lógico        | Célula | Tipo   |
|---------------------|--------|--------|
| título operação     | `B2`   | texto  |
| data emissão        | `B3`   | data   |
| 1º vencimento       | `B4`   | data   |
| último vencimento   | `B5`   | data   |
| valor principal     | `B6`   | número |
| TAC / tarifas       | `B7`   | número |
| IOF                 | `B8`   | número |
| qtd parcelas        | `B9`   | int    |
| valor prestação     | `B10`  | número |
| taxa pactuada       | `B11`  | decimal (0,1449) |
| taxa BACEN          | `B12`  | decimal |
| parcelas pagas      | `B13`  | int    |
| data do cálculo     | `B14`  | data   |

**Coluna A (recomendado):** rótulos em pt-BR (“Data de emissão”, “1º vencimento”, …) para leitura humana; o app **não** depende de A.

Se precisar mudar células, altere **`CELULAS_DADOS` em `config.py`** e o handoff juntos.

---

## 2. Trabalho manual no Excel (Claude Cowork / Bruna / designer)

1. **Duplicar** o `Calculo.xlsx` atual para `Calculo_v2_draft.xlsx` (backup do original).
2. Inserir aba **`DADOS`** no início (primeira aba do livro, opcional).
3. Preencher a coluna A com labels e a coluna B vazia nas células do mapa acima.
4. Em **cada aba PRICE** (24X, 36x, 48x, 60x), **substituir** o valor “cravado” nas células que hoje o Python preenche por **fórmulas**:
   - Ex.: se `C1` era título, usar `=DADOS!$B$2` (ajustar conforme offset da aba — hoje o código usa `celulas_para_aba`; para PRICE 24X, `C1` continua título → `=DADOS!$B$2`).
   - Repetir para `D3`, `D5`, `I7`, `I9`, `I13`, `I15`, `I16`, `I17`, `AP15`, `BL8`, etc., **apontando sempre para o mesmo endereço em `DADOS`**, independentemente da aba PRICE (assim as quatro PRICE ficam consistentes).
5. **Preservar** todas as **fórmulas já existentes** na grade de parcelas (colunas C/D/…), que dependem de `I15` e `D5` — depois do passo 4, `I15` deve ser `=DADOS!$B$9` (ou equivalente), para a tabela continuar a expandir até N parcelas.
6. **Área de impressão** e **paisagem:** copiar `page_setup`, `print_area`, margens da aba PRICE atual para não regressar no PDF.
7. **Testar** no Excel: alterar manualmente `DADOS!B9` (parcelas) e confirmar que a tabela de parcelas reage como no modelo antigo.
8. Quando estiver validado, substituir `templates/Calculo.xlsx` pelo novo ficheiro (ou renomear versões com tag git).

---

## 3. Saída do app (Drive)

Com `DADOS` presente, o ficheiro gerado terá **2 abas**: `DADOS` + a PRICE do prazo (ex.: `PRICE 24X`). As outras PRICE são removidas como hoje.

---

## 4. Prints / PDF completo (roadmap)

- **v0.5.x:** só geração XLSX; não há capturas PNG na pasta.
- **v0.6:** fluxo Windows + xlwings: imprimir/registar **aba visual** (e opcionalmente esconder `DADOS` na captura se preferirem só o “relatório”).
- PDF paisagem “conteúdo completo”: usar **área de impressão** já definida na PRICE ou export range xlwings → PDF.

---

## 5. Verificação rápida após migração

```bash
cd apps/clientes/02_rose/calculo-acao-crefaz
PYTHONPATH=src .venv/bin/pytest tests/test_planilha.py -q
```

Se os testes falharem: os asserts usam **células na PRICE** — após ligar fórmulas a `DADOS`, os valores **calculados** devem ser os mesmos; se não forem, há referência quebrada.

---

## 6. Prompt curto para colar no Cowork / Claude

```
No repo 01_ADVENTURE_LABS, projeto apps/clientes/02_rose/calculo-acao-crefaz.
Migrar templates/Calculo.xlsx para modelo de duas abas conforme docs/HANDOFF_PLANILHA_DADOS_VS_VISUAL.md: aba DADOS com mapa B2:B14 em config.CELULAS_DADOS; abas PRICE só com fórmulas apontando para DADOS; manter layout visual e print area paisagem.
Validar com pytest tests/test_planilha.py.
```
