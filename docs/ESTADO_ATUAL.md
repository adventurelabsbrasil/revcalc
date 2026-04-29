# Estado atual — Calculadora de Ação Crefaz v0.6.0

> **Atualizado:** 2026-04-29
> **Audiência:** Founder (Rodrigo) e qualquer agente Cowork/CLI futuro retomando o projeto.
> **Antes de fazer qualquer coisa:** ler este arquivo + `README.md` (usuário) + `README_DEV.md` (dev). Os arquivos em `docs/_obsoletos/` são histórico, não fonte de verdade.

---

## TL;DR

- **v0.6.0 em testing** — DADOS+visual com aba única `CÁLCULO`, capturas PDF+PNG via LibreOffice headless, log append.
- **Cliente:** Rose Portal Advocacia (Roselaine). Crefaz só opera contratos até 24 parcelas — uma única aba visual basta.
- **MVP funcional ponta-a-ponta**, validado matematicamente com cliente fictício IVAN DOS SANTOS (24 parcelas) — recalc LibreOffice 220 fórmulas, zero erros.
- **Falta:** mover commits pra `main`, build `.exe` Windows no ASUS da Bruna, validação humana (Bruna Scopel + Advogada Bruna).

---

## Arquitetura DADOS+visual (cristalizada em v0.5.7→v0.6.0)

`templates/Calculo.xlsx` tem **2 abas**:

| Aba | Estado | Conteúdo |
|-----|--------|----------|
| `DADOS` | oculta (`sheet_state="hidden"`) | A2:A14 labels pt-BR; B2:B14 valores escritos pelo app (13 campos: título, datas, valores, taxas, parcelas) |
| `CÁLCULO` | visível | Layout completo (cabeçalho + 3 tabelas de parcelas + cálculos derivados); cells de input apontam pra `=DADOS!$B$X`; tabela de parcelas usa `=IF(C<=$I$15, EDATE($D$5, C-1), "")` |

`gerar_xlsx` em `planilha.py` detecta presença de `DADOS` automaticamente. Se existir, escreve só em `B2:B14`. Senão (modo legacy) escreve direto na PRICE — fallback de retrocompatibilidade.

**Renomeação importante (v0.6.0):** PRICE 24X → CÁLCULO; abas PRICE 36x/48x/60x **removidas** porque Crefaz não opera nessas faixas. `PRAZO_MAXIMO=24` em `config.py`. `aba_para_prazo()` retorna sempre `"CÁLCULO"`.

---

## Capturas PDF+PNG (item v0.6.0)

`src/calculadora_crefaz/capturas.py` — módulo novo:

- Recebe `xlsx_bytes`, salva em tempfile, chama `soffice --headless --convert-to pdf`.
- Rasteriza PDF página a página com `pypdfium2` em DPI 150.
- Devolve `CapturasGeradas(pdf_bytes, pngs=[CapturaPng(...)])`.

`pipeline.py` integra: após upload do XLSX, chama `gerar_capturas`, sobe `13 Print CÁLCULO.pdf` + `13 Print CÁLCULO.png` (1 PNG por página) na pasta da cliente. Se LibreOffice ausente, emite aviso e segue (não bloqueia o cálculo).

**Pré-requisito:** LibreOffice no PATH no Mac/Win onde o app roda. Sem ele, capturas não saem mas XLSX e log seguem normais.

---

## Estrutura de arquivos no Drive (após cálculo)

```
EMPRESTIMO DE ENERGIA/
└── 10. RIO GRANDE DO SUL/
    └── IVAN DOS SANTOS/
        ├── 09 Contrato Crefaz.pdf       ← input (cliente sobe)
        ├── 10 Cálculo IVAN DOS SANTOS.xlsx ← output app
        ├── 11 Series Temporais.pdf      ← input ou copiado do central
        ├── 12 Log.txt                    ← histórico de execuções (modo append)
        ├── 13 Print CÁLCULO.pdf          ← captura PDF unificado (v0.6.0)
        └── 13 Print CÁLCULO.png          ← captura PNG (1+ por página)
```

---

## Status do checklist 12 itens (snapshot 2026-04-29)

| # | Feature | Status |
|---|---------|--------|
| 1 | UX nome do cliente | ✅ |
| 2 | Login Google (OAuth + keyring) | ✅ |
| 3 | Calcular | ✅ |
| 4 | Log + erros/avisos na UI | ✅ |
| 5 | Cálculo Python → DADOS auto preenche visual | ✅ |
| 6 | Cálculo a partir de nome + contrato + BACEN | ✅ |
| 7 | Visualizar XLSX no Drive (Sheets/Excel) | ✅ |
| 8 | Print partes mencionadas salvas na pasta | ✅ (v0.6.0) |
| 9 | Print geral (PDF) salvo na pasta | ✅ (v0.6.0) |
| 10 | Log salvo na pasta (append) | ✅ |
| 11 | Avisos UI conclusão e erros | ✅ |
| 12 | Empacotamento Mac/Win | 🟡 (Win pyinstaller.spec pronto; Mac via `.command` em dev; build final pendente) |

---

## Capturas regionais — escopo definitivo (decidido 2026-04-29 noite)

Além do print geral (`13 Print CÁLCULO.png` + `13 Print CÁLCULO.pdf`), o app gera **6 prints regionais** da aba CÁLCULO + **2 trechos de PDF** já existentes na pasta:

### Da aba CÁLCULO (extraídos via mudança de print_area + soffice)

| # | Nome do PNG | Conteúdo (range XLSX a mapear) |
|---|-------------|-------------------------------|
| 1 | `13 Print 01 Dados do Contrato.png` | Quadro DADOS DO CONTRATO (header azul, ~13 linhas: Valor principal, Seguros, TAC, Registro, Avaliação, Outros, IOF, Valor financiado total, Qtd parcelas, Valor parcela cobrada, Taxa pactuada, Valor final) |
| 2 | `13 Print 02 Valores Recalculados.png` | VALORES RECALCULADOS (mesma estrutura com taxa BACEN) + Diferença cobrada a mais + Montante cobrado a mais |
| 3 | `13 Print 03 Conforme Pactuado.png` | Fórmula PMT pactuado (header azul, taxa contratual, parcela calculada) |
| 4 | `13 Print 04 Parcela Taxa Media.png` | PARCELA COM TAXA MÉDIA E EXPURGO DE ABUSIVIDADES (fórmula PMT com taxa BACEN) |
| 5 | `13 Print 05 Percentual + Indevidas.png` | 2 caixas pequenas lado a lado: PERCENTUAL DA TAXA COBRADADA SUPERIOR A MÉDIA + TOTAL NOMINAL DE COBRANÇAS INDEVIDAS |
| 6 | `13 Print 06 Saldo Recalculado.png` | SALDO RECALCULADO DESCONTANDO AS PARCELAS PAGAS (incluindo Valor da parcela atual em amarelo + sub-quadro Saldo controvertido) |

**Implementação:** pra cada região, copiar XLSX em memória → setar `ws.print_area = range` → `soffice --convert-to pdf` → `pypdfium2 render` → PNG. ~6 invocações soffice por cálculo (overhead aceitável: ~3-5s).

**Mapeamento dos ranges:** ainda a fazer — auditar o template e identificar limites de cada bloco por busca de células com os títulos. Resultado vira `REGIOES_CALCULO: dict[str, str]` em `config.py`.

### De PDFs existentes na pasta cliente

| # | Nome do PNG | Origem |
|---|-------------|--------|
| 7 | `13 Print 07 Item II do Contrato.png` | Página do `09 Contrato Crefaz.pdf` que contém "II.EMPRÉSTIMO CONCEDIDO" → "III.CUSTO EFETIVO TOTAL". Marcadores já existem em `parser_contrato.py` (`MARCADOR_ITEM_II_INICIO/FIM`). |
| 8 | `13 Print 08 Series BACEN.png` | Página do `11 Series Temporais.pdf` que contém "Séries selecionadas" no título. Procurar via pdfplumber, capturar a página inteira em PNG. |

**Implementação:** abrir PDF com pypdfium2 + identificar página por regex no texto extraído (pdfplumber) → renderizar essa página em PNG.

### Total na pasta da cliente após cálculo (v0.6.0 final)

```
09 Contrato Crefaz.pdf        ← input
10 Cálculo NOME.xlsx          ← output principal
11 Series Temporais.pdf       ← input ou copiado do central
12 Log.txt                     ← histórico append
13 Print CÁLCULO.pdf           ← print geral PDF unificado
13 Print CÁLCULO.png           ← print geral PNG (página inteira)
13 Print 01 Dados do Contrato.png
13 Print 02 Valores Recalculados.png
13 Print 03 Conforme Pactuado.png
13 Print 04 Parcela Taxa Media.png
13 Print 05 Percentual + Indevidas.png
13 Print 06 Saldo Recalculado.png
13 Print 07 Item II do Contrato.png
13 Print 08 Series BACEN.png
```

14 arquivos total (1 input contrato + 1 input BACEN + 1 XLSX + 1 log + 1 PDF + 1 PNG geral + 6 PNGs regionais XLSX + 2 PNGs de PDFs).

---

## Trabalho pendente antes da entrega à Bruna

### Crítico
1. **Mover arquivos novos pra `main`** (commits + push):
   - Template novo `templates/Calculo.xlsx` (DADOS oculta + CÁLCULO única + merges fix v0.6.0)
   - Snapshot `templates/Calculo.preDADOS.xlsx` (snapshot v0.5.6 cirúrgica)
   - Snapshot `templates/Calculo.4abas-DADOS.xlsx` (snapshot v0.5.7 com 4 PRICE)
   - Snapshot `templates/Calculo.original.xlsx` (snapshot v0.5.0)
   - `src/calculadora_crefaz/capturas.py` (módulo novo)
   - Modificações: `config.py`, `planilha.py`, `pipeline.py`, `log_writer.py`, `__init__.py` (versão 0.6.0)
   - Bump `pyproject.toml` (0.6.0 + deps `pypdfium2`, `Pillow`)
   - `scripts/migrar_para_dados.py` + `scripts/fix_extends_v0.6.0.py`
   - Docs: este arquivo + 2 READMEs na raiz; obsoletos em `docs/_obsoletos/`

2. **Tag `v0.6.0`** + push.

3. **Build Windows** no ASUS da Bruna: `pyinstaller pyinstaller.spec` → `dist/CalculadoraCrefaz.exe`.

### Validação humana
4. Bruna Scopel: rodar 1 cálculo real → conferir XLSX + Ctrl+P + PDF salvo na pasta.
5. Advogada Bruna (Rose): comparar números v0.5.0 vs v0.6.0 pra ≥ 2 clientes — devem ser idênticos.
6. Roselaine: ciência (não validação técnica — D5).

### Não-crítico
7. Build Mac `.app` quando tempo permitir.
8. Refatorar `aplica_v0.5.1.py` consolidando todos os patches (cirúrgica v0.5.x + DADOS+visual + fix_extends_v0.6.0) em **um** script idempotente.

---

## E2E IVAN DOS SANTOS — caso de teste de referência

Fixture mockada:
- Cédula: 3700123
- Prazo: 24 parcelas
- Valor principal: R$ 2.200,00; TAC: R$ 50; IOF: R$ 30; valor parcela: R$ 170,00
- Taxa pactuada: 18,99%/mês; Taxa BACEN ago/2025: 5,32%/mês
- 1º vencimento: 15/09/2025; último: 15/08/2027
- Hoje fictício: 29/04/2026 → 8 parcelas pagas

**Resultado esperado** (validado em `_e2e_ivan/`):
- XLSX 62KB, aba DADOS oculta com B2:B14 preenchidos, aba CÁLCULO com fórmulas resolvidas.
- 220 fórmulas, zero erros (recalc LibreOffice).
- Tabela CONFORME O CONTRATO: 24 datas + R$ 170 todos.
- Tabela RECALCULADAS: 24 datas + R$ 166,68 todos.
- Tabela VALORES PAGOS: 8 com valor R$ 170, 16 com "-" (formato número trata zero como "-").
- PDF 116KB, 1 página A4 paisagem. PNG 1754×1241 @150DPI ~330KB.
- Log com 2 execuções (separador `="*60`); 1ª inclui aviso BACEN copiado do repositório central.

Pasta `_e2e_ivan/` no projeto contém os artefatos pra inspeção visual.

---

## Decisões cristalizadas (não revisitar sem motivo forte)

- **D1 (revisada 2026-04-29):** 1 aba visual única (CÁLCULO), não 4 — Crefaz só opera 1-24 parcelas.
- **D2:** `planilha.py` preservado, ganha mapeamento DADOS adicional.
- **D3:** Zero identidade visual nova. Sem logo, sem fonte custom.
- **D4:** Conteúdo jurídico (6 seções) inalterado.
- **D5:** Validação técnica = Bruna Scopel + Advogada Bruna; Roselaine recebe ciência.
- **D6:** XLSX print-ready (paisagem A4 + fitToWidth=1 + fitToHeight=1).
- **D7 (v0.5.7):** DADOS+visual em duas camadas.
- **D8 (v0.6.0):** capturas via LibreOffice headless (não xlwings) — funciona Mac/Win sem Excel instalado.

---

## Histórico de versões (resumido)

| Versão | Data | Mudança |
|--------|------|---------|
| v0.5.0 | 2026-04-27 | MVP funcional inicial; 4 abas PRICE |
| v0.5.1-v0.5.5 | n/a | Saltos não documentados |
| v0.5.6 | 2026-04-28 | Patch cirúrgico template (extensão tabela 24X, IF+EDATE, page setup) |
| v0.5.7 | 2026-04-29 | DADOS+visual em 2 camadas; aba DADOS oculta + 4 PRICE |
| **v0.6.0** | **2026-04-29** | **1 aba CÁLCULO + capturas PDF+PNG via LibreOffice + fix extends rows 147-155** |
| v0.7.0 | planejado | GitHub Actions build .exe automático no tag push |
| v0.8.0 | planejado | `.app` Mac assinado + DMG |
| v0.9.0 | planejado | Notificação Telegram (`ceo_buzz_Bot`) |
| v1.0.0 | planejado | Code-signing Apple Developer ID |

---

## Onde está o quê (mapa rápido)

| Pergunta | Arquivo |
|----------|---------|
| Como rodar em dev? | `README_DEV.md` |
| Como usar no dia-a-dia? | `README.md` |
| Pipeline 13 passos? | `src/calculadora_crefaz/pipeline.py` |
| Mapeamento DADOS B2:B14? | `src/calculadora_crefaz/config.py` (CELULAS_DADOS) |
| Geração de capturas? | `src/calculadora_crefaz/capturas.py` |
| Patch das rows estendidas? | `scripts/fix_extends_v0.6.0.py` |
| Migração DADOS+visual original? | `scripts/migrar_para_dados.py` |
| Caso E2E referência? | `_e2e_ivan/` |
| Histórico de decisões antigas? | `docs/_obsoletos/` (não-canônico) |
