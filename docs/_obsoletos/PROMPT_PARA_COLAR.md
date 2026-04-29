# Prompt para colar no Claude Code CLI / Cursor

> **Versão 0.5.0** — calibrado em **2026-04-27** após 5 rodadas de discussão.
>
> **MVP enxuto pra rodar HOJE.** Escopo cortado vs. v0.4: sem Supabase, sem Telegram, sem capturas (xlwings), sem pywebview/HTML+Tailwind, sem briefcase, sem GitHub Actions multi-plataforma.
>
> **Stack final do MVP:** CLI Python + UI Tkinter mínima + PyInstaller single `.exe` Windows + log.txt na pasta da cliente como histórico portável.
>
> **Como usar:** abra o terminal dentro do monorepo `/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS`, inicie Claude Code CLI (`claude`) ou Cursor com Sonnet 4.6, e cole tudo entre `### INÍCIO DO PROMPT ###` e `### FIM DO PROMPT ###`.

---

### INÍCIO DO PROMPT ###

Você vai construir o **MVP da Calculadora de Ação Crefaz** para a Rose Portal Advocacia, dentro do monorepo Adventure Labs (`apps/clientes/02_rose/calculo-acao-crefaz/`). É um app desktop **Windows-first** (Bruna usa ASUS) com UI Tkinter mínima, distribuído como **único `.exe` standalone**.

**Prazo: o agente deve entregar a Fase 1 (CLI + UI mínima + smoke E2E sem capturas) hoje, em 1 sessão de trabalho focado.** Capturas de prints da planilha (que exigem Excel + xlwings) ficam para a v0.6 — Bruna testa a v0.6 no ASUS quando estiver pronta.

## O que o sistema faz (escopo MVP)

Recebe nome do cliente → encontra a pasta no Drive → lê o contrato Crefaz em PDF → extrai dados do Item II → calcula parcelas pagas → busca taxa BACEN do **mês da data de emissão** (Item II) → preenche a planilha de cálculo modelo via openpyxl → salva o XLSX preenchido na pasta da cliente no Drive → escreve um log.txt naquela pasta como registro do que foi feito.

**Fora do escopo desta versão:**
- Capturas/prints da planilha (xlwings + Excel) — TODO v0.6.
- Notificação Telegram — TODO v0.7.
- Supabase para histórico/dedup — substituído por arquivo `12 Log.txt` na própria pasta da cliente; dedup por verificação se `10 Cálculo*.xlsx` já existe.
- pywebview/HTML/Tailwind/Alpine — substituído por janela Tkinter mínima.
- briefcase + multi-platform — substituído por PyInstaller `--onefile` para Windows. Mac pode ser adicionado depois via GitHub Actions.

## Premissas já fechadas (não perguntar — decisões finais)

1. **Stack:** Python 3.11+. UI **Tkinter** (stdlib, sem deps externas). Bibliotecas obrigatórias: `pdfplumber`, `openpyxl`, `google-api-python-client`, `google-auth-oauthlib`, `keyring`, `python-dateutil`, `unidecode`, `rapidfuzz`, `httpx`. Sem xlwings, sem pdf2image, sem Pillow, sem FastAPI, sem pywebview.

2. **Distribuição:** PyInstaller `--onefile --windowed` empacota tudo em um único `.exe` Windows (~40MB). Mac roda direto via `python -m calculadora_crefaz` (Founder dev no Mac sem Excel não vai gerar capturas mesmo). Cross-build pra Windows: ou rodar PyInstaller no ASUS da Bruna, ou GitHub Actions com runner `windows-latest` (ver passo 17 da ordem de implementação).

3. **Autenticação:** OAuth desktop flow do Google Workspace (loopback redirect com PKCE, sem client_secret). Restringir a `roseportaladvocacia.com.br` e `adventurelabs.com.br`. Token em keychain via `keyring`.

4. **Histórico e dedup:** o registro de cada cálculo vive na própria pasta da cliente como arquivo `12 Log.txt` (formato no passo 13 abaixo). Dedup via verificação de existência de `10 Cálculo*.xlsx` na pasta antes de processar.

5. **Localização do código:** `apps/clientes/02_rose/calculo-acao-crefaz/`.

6. **Template:** `apps/clientes/02_rose/calculo-acao-crefaz/templates/Calculo.xlsx`.

7. **Matching simplificado.** Contrato sempre nomeado pela equipe Rose como `NN Contrato Crefaz.pdf` ou `Contrato Crefaz.pdf` antes de processar.

8. **Pastas em 2 níveis:** maioria em `EMPRESTIMO DE ENERGIA/{NN. ESTADO}/{CLIENTE}/`; legado em `EMPRESTIMO DE ENERGIA/{CLIENTE}/`.

9. **Apenas contratos ativos.** Quitados ficam para uma Fase 3 separada.

## Estrutura no Drive

- **Pasta-mãe:** `EMPRESTIMO DE ENERGIA` — ID `1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN`.
- **Subpastas de estado:** regex `^\d{2}\.\s+` (ex: `10. RIO GRANDE DO SUL`).
- **Pasta BACEN:** `EMPRESTIMO DE ENERGIA/03. MODELOS/Série do Bacen/` — ID `1w8aWxOURJewINVPlyGKlitEE-EpStWUe`. Padrão `MM-YYYY.pdf`.
- **Convenção de numeração na pasta da cliente:** `01` Procuração, `02` Declaração/CNH, `03` ID/Declaração, `04` Comprovante, `05` Extrato, `06` Declaração IRPF, `07` CPF, `08` Pesquisa IR, **`09` Contrato Crefaz** (input), **`10` Cálculo {NOME}.xlsx** (output), **`11` Series Temporais.pdf** (BACEN copiado pelo sistema), **`12` Log.txt** (histórico do processamento).

## Mapeamento campo planilha → contrato

Aba `PRICE 24X` como referência (outras 3 abas têm offset +1 linha, tratar via configuração):

| Célula | Campo | Origem |
|--------|-------|--------|
| C1 | Título | `CÁLCULOS DA OPERAÇÃO Nº {cédula} - CLIENTE: {NOME} x BANCO CREFAZ` |
| D3 | Data pactuação | Item II "Data de Emissão" |
| I7 | Valor principal | Item II "Valor Nominal" |
| I9 | TAC | Item II "Tarifas" |
| I13 | IOF | Item II "Tributos/IOF" |
| I15 | Quantidade parcelas | Item II "Prazo" |
| I16 | Valor parcela | Item II "Valor da Prestação" |
| I17 | Taxa pactuada | Item II **"Taxa de Juros Mensal"** (5ª linha, NÃO a anual). `18,77%` → `0.1877` |
| AP15 | Taxa BACEN | Campo 25464 do PDF do **mês do 1º Vencimento**. `5,58` → `0.0558` |
| BL8 | Parcelas pagas | `max(0, min(prazo, meses_entre(hoje, 1º_vencimento)))` |

Demais campos (I8, I10, I11, I12) deixar `0` se não vierem no contrato.

## Pipeline (12 passos)

### 1. Validar entrada
Nome com 2+ palavras. Normalizar via `unidecode` para matching, preservar original para output.

### 2. Autenticar OAuth Workspace
Loopback redirect PKCE em porta randômica `localhost`. Scope `https://www.googleapis.com/auth/drive`. Token em `keyring` (`service="calculadora-crefaz"`, `username="oauth-tokens-{email}"`). Validar que email termina em `@roseportaladvocacia.com.br` ou `@adventurelabs.com.br`. Refresh automático via `refresh_token`.

### 3. Localizar pasta do cliente (busca em 2 níveis)
- Nível 1 (raiz): `parentId = '1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN'`. Match com `unidecode + casefold + strip`.
- Nível 2 (estados): listar subpastas regex `^\d{2}\.\s+`, buscar dentro de cada.
- 0 resultados → erro com 3 sugestões via `rapidfuzz`.
- >1 resultado → erro listando paths.

### 4. **Verificar dedup antes de processar**
Listar arquivos da pasta. Se existe arquivo cujo nome casa `^10\s+C[áa]lculo.*\.xlsx$`, perguntar ao usuário (na UI: dialog `messagebox.askyesno`; no CLI: prompt) `"Cálculo já existe (criado em {data_modificacao}). Sobrescrever? [s/N]"`. Se não confirmar, abortar com status `"BLOQUEIO_DEDUP"`. Flag `--force` pula a pergunta.

### 5. Localizar contrato Crefaz
Padrões aceitos (case-insensitive):
1. `^\d{2}\s+contrato\s+crefaz.*\.pdf$`
2. `^contrato\s+crefaz.*\.pdf$`

Excluir prefixos auxiliares: `01 Procuração`, `02 CNH`, `02 Declaração`, `03 Declaração`, `03 ID`, `04 Comprovante`, `05 Extrato`, `06 Declaração`, `07 CPF`, `08 Pesquisa`, `10 Cálculo`, `10 Calculo`, `11 Series`, `11 Séries`, `12 Log`, `Contrato Honorários`, `Contrato honorários`, `Contrato de Honorários`, `Declaração de Isenção`, `Declaração isenção`, `Situação CPF`, `Kit Procuração`.

- 0 resultados → erro pedindo rename.
- ≥2 → BLOQUEIO; flag `--contrato '{nome}'` força.

### 6. Baixar contrato e parsear Item II
`pdfplumber` extrai texto. Bloco entre `II.EMPRÉSTIMO CONCEDIDO:` e `III.CUSTO EFETIVO TOTAL`. Regex (tolerância a espaços/quebras):

```
Data de Emissão:\s*(\d{2}/\d{2}/\d{4})
Prazo:\s*(\d+)
1º Vencimento:\s*(\d{2}/\d{2}/\d{4})
Último Vencimento:\s*(\d{2}/\d{2}/\d{4})
Valor Nominal:\s*R\$\s*([\d.,]+)
Valor do Empréstimo:\s*R\$\s*([\d.,]+)
Valor Total Contratado:\s*R\$\s*([\d.,]+)
Valor da Prestação:\s*R\$\s*([\d.,]+)
Taxa de Juros Mensal:\s*([\d,]+)%
Taxa de Juros Anual:\s*([\d,]+)%
Tributos/IOF:\s*R\$\s*([\d.,]+)
Tarifas:\s*R\$\s*([\d.,]+)
```

Cabeçalho: `CÉDULA DE CRÉDITO BANCÁRIO N\.º\s*(\d+)`.
Item I.EMITENTE Nome: `Nome:\s*(.+?)\s+CPF`.

Validação: warning se `Valor Nominal + Tributos/IOF + Tarifas ≠ Valor do Empréstimo` (tolerância R$ 1,00).

### 7. Calcular parcelas pagas
```python
def meses_entre(d_atual, d_origem):
    return (d_atual.year - d_origem.year) * 12 \
         + (d_atual.month - d_origem.month) \
         + (1 if d_atual.day >= d_origem.day else 0)

parcelas_pagas = max(0, min(prazo, meses_entre(date.today(), primeiro_vencimento)))
```

### 8. Localizar BACEN — prioridade dupla
- **Prioridade 1:** `11 Series Temporais.pdf` ou `11 Séries Temporais.pdf` na pasta da cliente. `bacen_origem = "pasta_cliente"`.
- **Prioridade 2:** `{MM}-{YYYY}.pdf` na pasta `Série do Bacen` (mês do **1º Vencimento**). `bacen_origem = "serie_do_bacen"`.
- Não encontrado → erro mencionando equipe da Rose.
- Ignorar `Cópia de *.pdf`.

### 9. Extrair taxa do BACEN
Padrão do PDF: `{mês}/{ano}    {valor_anual}    {valor_mensal}`.
Regex: `(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)/\d{4}\s+([\d,]+)\s+([\d,]+)` → grupo 2. Converter `5,58` → `0.0558`.

### 10. Decidir aba do template
| Prazo | Aba |
|-------|-----|
| 1–24 | `PRICE 24X` |
| 25–36 | `PRICE 36x` |
| 37–48 | `PRICE 48x` |
| 49–60 | `PRICE 60x` |
| >60 | erro `"PRAZO FORA DO TEMPLATE"` |

### 11. Gerar XLSX preenchido
`openpyxl.load_workbook("templates/Calculo.xlsx")`. Selecionar aba certa, **apagar as outras 3**. Preencher células conforme mapeamento. **Não tocar** em fórmulas, formatação, page setup, print_area. Validar `orientation == 'landscape'`. Se for `PRICE 48x` em portrait, **forçar landscape** com warning no log.

**No MVP não embute capturas no XLSX** (TODO v0.6).

### 12. Salvar XLSX e BACEN na pasta da cliente
- **XLSX:** upload como `10 Cálculo {NOME}.xlsx` (substituir nome do cliente em maiúsculas, ASCII via unidecode). Sobrescrever se já existe (já tratamos dedup no passo 4).
- **BACEN:** se `bacen_origem == "serie_do_bacen"` (não estava na pasta), fazer upload como `11 Series Temporais.pdf`. Senão, não fazer nada.

### 13. Escrever `12 Log.txt` na pasta da cliente

Conteúdo:

```
Calculadora de Ação Crefaz — MVP v0.5.0
=========================================

Processado em: 2026-04-28 14:32:11 BRT
Por: bruna@roseportaladvocacia.com.br

CLIENTE
-------
Nome: Marli Sueli Berger Dambrosio
Pasta no Drive: EMPRESTIMO DE ENERGIA/10. RIO GRANDE DO SUL/MARLÍ.../

CONTRATO LIDO
-------------
Arquivo: 09 Contrato Crefaz.pdf
Número da cédula: 4095068

Item II extraído:
- Data de Emissão: 29/12/2025
- Prazo: 18 parcelas
- 1º Vencimento: 02/02/2026
- Último Vencimento: 02/07/2027
- Valor Nominal: R$ 3.500,00
- Valor da Prestação: R$ 585,53
- Taxa de Juros Mensal: 14,49%
- Tributos/IOF: R$ 104,99
- Tarifas: R$ 0,00

CÁLCULO
-------
Parcelas pagas até hoje: 3
Aba do template: PRICE 24X

BACEN
-----
Origem: pasta_cliente (já estava em 11 Series Temporais.pdf)
Mês de referência: 02/2026
Taxa 25464: 6,47%

DIVERGÊNCIA
-----------
Taxa pactuada: 14,49%
Taxa BACEN: 6,47%
Excesso: +124% (taxa pactuada / taxa BACEN - 1)

ARQUIVOS GERADOS NESTA EXECUÇÃO
-------------------------------
- 10 Cálculo MARLI SUELI BERGER DAMBROSIO.xlsx (novo / sobrescrito)
- 11 Series Temporais.pdf (já existia, mantido)
- 12 Log.txt (este arquivo)

CAPTURAS DE PRINT
-----------------
Não geradas nesta versão (v0.5.0). Disponível em v0.6.

STATUS: SUCESSO
```

Upload como `12 Log.txt` (sobrescrever se existir — log mais recente é o que vale).

## UI — Tkinter mínima

Janela única, ~600×400px, redimensionável. **Estilo:**

```
┌─ Calculadora Crefaz ────────────────── ─ □ ✕ ┐
│                                              │
│  Logado: bruna@roseportaladvocacia.com.br    │
│  [Sair]                                      │
│                                              │
│  Nome do cliente:                            │
│  ┌──────────────────────────────────────┐    │
│  │ Marli Sueli Berger Dambrosio         │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  [ Calcular ]   [ Forçar (sobrescrever) ]    │
│                                              │
│  ──────────────────────────────────────────  │
│                                              │
│  Log:                                        │
│  ┌──────────────────────────────────────┐    │
│  │ [14:32:01] Pasta encontrada          │    │
│  │ [14:32:02] Contrato lido (4095068)   │    │
│  │ [14:32:03] Item II extraído          │    │
│  │ [14:32:03] BACEN 02-2026 já na pasta │    │
│  │ [14:32:11] XLSX salvo no Drive       │    │
│  │ [14:32:13] Log escrito               │    │
│  │                                      │    │
│  │ ✓ Pronto.                            │    │
│  │ Pasta: drive.google.com/drive/...    │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  [ Abrir pasta no Drive ]                    │
│                                              │
└──────────────────────────────────────────────┘
```

**Componentes Tkinter:**
- `tk.Tk()` — janela principal.
- `tk.Label` para "Logado" e "Nome do cliente".
- `tk.Entry` para input do nome.
- `tk.Button` para Calcular / Forçar / Sair / Abrir pasta no Drive.
- `tk.Text` (com scroll) para o log streaming.
- Tema: configurar com `tk.ttk.Style().theme_use("clam")` para visual mais moderno; cores escuras opcionais via `widget.configure(bg="#1a1a1a", fg="#e6e6e6")`.

**Streaming do log:** o pipeline roda em thread separada (`threading.Thread`) para não bloquear UI. A thread escreve mensagens em `queue.Queue`; o main loop do Tkinter consome da fila a cada 100ms via `root.after(100, drain_queue)`.

**Primeiro acesso (sem token salvo):** ao abrir, se `keyring` não tem token, mostrar tela de login com botão "Entrar com Google Workspace". Botão chama o flow OAuth (abre browser), aguarda callback, salva token, troca para tela principal.

## Estrutura de pastas

```
apps/clientes/02_rose/calculo-acao-crefaz/
├── README.md                       # uso, download, troubleshoot
├── pyproject.toml                  # poetry, deps
├── requirements.txt                # versões pinadas (alternativa)
├── pyinstaller.spec                # config do bundler
├── .gitignore                      # cache, dist, build
├── src/
│   └── calculadora_crefaz/
│       ├── __init__.py
│       ├── __main__.py             # entry point: sobe Tkinter
│       ├── ui.py                   # janela Tkinter + threading
│       ├── auth.py                 # OAuth desktop flow + keyring
│       ├── drive.py                # Drive API: busca, download, upload
│       ├── parser_contrato.py
│       ├── parser_bacen.py
│       ├── calculadora.py          # parcelas pagas + decisão de aba
│       ├── planilha.py             # openpyxl preenchimento
│       ├── log_writer.py           # gera 12 Log.txt
│       ├── config.py               # IDs, paths, regex constantes
│       └── exceptions.py
├── templates/
│   └── Calculo.xlsx                # versionado
├── tests/
│   ├── fixtures/                   # gitignored (PDFs reais)
│   ├── test_parser_contrato.py
│   ├── test_parser_bacen.py
│   ├── test_calculadora.py
│   └── test_drive_busca.py         # mocks
└── scripts/
    ├── dev_run.sh                  # python -m calculadora_crefaz
    └── build_exe.sh                # pyinstaller --onefile (rodar no Windows)
```

`.gitignore`: `dist/`, `build/`, `*.spec~`, `tests/fixtures/*.pdf`, `tests/fixtures/*.xlsx`, `~/.calculadora-crefaz/`, `__pycache__/`.

## OAuth Workspace — detalhes operacionais

Cliente OAuth tipo "Desktop app" no Google Cloud Console. Configuração:
- Authorized redirect URIs: `http://localhost` (porta randômica do loopback).
- Tela de consentimento: "Interno" (restringe ao Workspace Rose automaticamente).
- Scope: apenas `https://www.googleapis.com/auth/drive`.
- `client_id` é embarcado no executável (público, sem secret).
- PKCE com `code_challenge` SHA-256.

Variável de ambiente `GOOGLE_OAUTH_CLIENT_ID` lida em build time. Default fallback para dev: `.env` na raiz do projeto.

## Empacotamento e distribuição

### Build local Windows (no ASUS da Bruna ou Founder com VM)

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed \
    --name "CalculadoraCrefaz" \
    --add-data "templates/Calculo.xlsx;templates" \
    --icon="src/calculadora_crefaz/resources/icon.ico" \
    src/calculadora_crefaz/__main__.py
```

Output: `dist/CalculadoraCrefaz.exe` (~40MB single file).

### Distribuição

Por enquanto: copiar o `.exe` direto pra pasta compartilhada do Workspace ou via WhatsApp/Drive da Adventure. Bruna baixa, dá duplo-clique, primeira vez precisa "Mais informações > Executar mesmo assim" no SmartScreen.

**TODO Fase 1.5:** GitHub Actions Windows-only com upload pra Releases (apenas .exe Windows, sem matriz multi-plataforma). Workflow simples:

```yaml
on:
  push:
    tags: ["v*"]
jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller --onefile --windowed ...
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/CalculadoraCrefaz.exe
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Critérios de aceite

### Smoke E2E nº 1 — Adriano

`python -m calculadora_crefaz` → digitar `"Adriano Luis Calistro Lourenco"` → Calcular.

XLSX gerado deve ter:
- C1 = `"CÁLCULOS DA OPERAÇÃO Nº 3867296 - CLIENTE: ADRIANO LUIS CALISTRO LOURENCO x BANCO CREFAZ"`
- D3 = 22/09/2025
- I7 = 1000.00, I9 = 0.00, I13 = 25.10, I15 = 12, I16 = 226.79, I17 = 0.1877
- AP15 = taxa BACEN de **outubro/2025** (1º venc 27/10/2025)
- BL8 = parcelas pagas calculadas com `date.today()`
- Apenas 1 aba (`PRICE 24X`)

Pasta: `EMPRESTIMO DE ENERGIA/ADRIANO LUIS CALISTRO LOURENCO/`. **Pasta deve ter contrato renomeado para `09 Contrato Crefaz.pdf` antes** (premissa 7).

### Smoke E2E nº 2 — Marlí

`python -m calculadora_crefaz` → digitar `"Marli Sueli Berger Dambrosio"` → Calcular.

XLSX gerado deve ter:
- C1 = `"CÁLCULOS DA OPERAÇÃO Nº 4095068 - CLIENTE: MARLI SUELI BERGER DAMBROSIO x BANCO CREFAZ"`
- D3 = 29/12/2025
- I7 = 3500.00, I9 = 0.00, I13 = 104.99, I15 = 18, I16 = 585.53, I17 = 0.1449
- AP15 = **0.0647** (BACEN fev/2026)
- BL8 = parcelas pagas
- Apenas 1 aba (`PRICE 24X`)

Pasta: `EMPRESTIMO DE ENERGIA/10. RIO GRANDE DO SUL/MARLÍ SUELÍ BERGER DAMBRÓSIO/`. Contrato `09 Contrato Crefaz.pdf`. **Pasta já tem `11 Series Temporais.pdf` — sistema deve usar este (`bacen_origem = "pasta_cliente"`) e NÃO copiar do Série do Bacen.**

### Outros testes obrigatórios

- **Dedup:** rodar 2x → segunda execução pergunta antes de sobrescrever (ou aceita `--force`).
- **Pasta ambígua:** simular cliente em raiz e em estado → erro listando paths.
- **Contrato múltiplo:** pasta com 2 PDFs match → BLOQUEIO.
- **Contrato ausente / não renomeado:** erro pedindo rename.
- **BACEN ausente nos 2 locais:** erro mencionando equipe da Rose.
- **BACEN só na pasta cliente:** funciona sem tocar Série do Bacen.
- **BACEN só em Série do Bacen:** copia para pasta cliente.
- **Prazo > 60:** erro.
- **Login com domínio errado:** bloqueado.
- **OAuth refresh:** após expirar, renova via refresh_token sem pedir login de novo.
- **Logout:** botão "Sair" deleta token do keychain.
- **Log.txt:** validar conteúdo bate com o cálculo realizado.
- **Nomes com acentos:** input com ou sem acento encontra a mesma pasta.

## Restrições críticas

1. **Não descaracterizar a planilha.** Manter fórmulas, formatação, page setup, print_area do template.
2. **Página final imprimível em A4 paisagem.** Validar `paperSize == 9` e `orientation == 'landscape'`.
3. **Nenhum PII bruto em log.txt** além do que já vem do contrato (nome, cédula). Não incluir CPF, telefone, dados bancários.
4. **OAuth com escopo mínimo** (`https://www.googleapis.com/auth/drive`).
5. **Idempotência:** rodar 2x sem `--force` retorna o mesmo XLSX da primeira execução (após confirmação).
6. **Não tocar pastas de outros clientes.**

## Ordem de implementação (1 dia)

**Manhã (4h):**
1. Setup do projeto (`pyproject.toml`, estrutura, README inicial, `.gitignore`).
2. `config.py` + `exceptions.py` — constantes e exceptions tipadas.
3. `parser_contrato.py` + testes — validar com PDFs do Adriano e Marlí.
4. `parser_bacen.py` + testes — validar com `02-2026.pdf` e `10-2025.pdf`.
5. `calculadora.py` + testes de borda.

**Tarde (4h):**
6. `auth.py` — OAuth desktop flow + keyring + restrição de domínio.
7. `drive.py` — busca em 2 níveis, download, upload, dedup check.
8. `planilha.py` — carregamento e preenchimento; validar XLSX.
9. `log_writer.py` — gera `12 Log.txt`.
10. `ui.py` — janela Tkinter + threading + queue para log streaming.
11. `__main__.py` — bootstrap.

**Validação final:**
12. Smoke E2E real com Adriano e Marlí.
13. Empacotamento `pyinstaller --onefile` (rodar no Windows do Founder ou GitHub Actions).
14. README final com tabela de download e instruções.

Cada etapa = commit isolado com testes correspondentes (quando aplicável).

## TODOs explícitos para próximas versões

- **v0.6 — Capturas de prints da planilha:** adicionar `xlwings` + Microsoft Excel local. Gerar `Captura_01.png` a `Captura_06.png` (Item II contrato + página BACEN + 4 quadros da planilha). Embedar no XLSX final + salvar soltos na pasta. Bruna testa no ASUS dela.
- **v0.7 — Notificação Telegram:** webhook outbound para `ceo_buzz_Bot` (chat 1069502175) ao final de cada cálculo.
- **v0.8 — GitHub Actions Windows-only** com Release automático a cada tag.
- **v0.9 — Mac binary** via segundo job do CI (`macos-latest`).
- **v1.0 — Code signing** (Apple Developer ID + Microsoft Authenticode) se Founder decidir investir.
- **v1.1 — Histórico estruturado:** opcional, integrar com Supabase Rose existente (`https://ypyuzjczokfrvtndnoem.supabase.co`).
- **v2.0 — Contratos quitados:** escopo similar mas com lógica de saldo zerado e cálculo retrospectivo.

## Saída esperada

Ao final do dia, deve estar entregue:

- Código completo no path `apps/clientes/02_rose/calculo-acao-crefaz/`.
- README com tabela de uso (mesmo que distribuição final só venha em v0.8).
- Testes unitários cobrindo parsers, calculadora.
- Smoke E2E real rodando com Adriano e Marlí no Mac do Founder (sem capturas — TODO v0.6).
- Build local `.exe` Windows funcional (se possível hoje; senão, instruções pra Bruna empacotar no ASUS).
- Lista de TODOs claramente marcados nas próximas versões.

Antes de começar, confirme:
- `Cálculo.xlsx` está em `templates/Calculo.xlsx`.
- `.env` local com `GOOGLE_OAUTH_CLIENT_ID` válido.
- Acesso ao Drive da Rose autorizado (pasta `EMPRESTIMO DE ENERGIA` visível pelo email Workspace).

Comece pelo passo 1 da ordem de implementação. Não pule etapas. Foque em entregar funcional hoje, sem capturas.

### FIM DO PROMPT ###

---

## Notas para Rodrigo (não vai pro CLI)

### Antes de colar o prompt

**1. Mover o `Cálculo.xlsx`** que está em `_uploads/` do Cowork para `apps/clientes/02_rose/calculo-acao-crefaz/templates/Calculo.xlsx`. Sem isso, o agente não tem template.

**2. OAuth Client ID:** criar no Google Cloud com a conta `roselaine@roseportaladvocacia.com.br` ou na conta Adventure. Tipo "Desktop app". Tela de consentimento "Interno". Anotar `client_id` e salvar em `.env`. Posso te guiar agora se quiser — é ~5 minutos.

**3. (Opcional)** verificar se há sessão Workspace ativa na sua conta `contato@adventurelabs.com.br` ou se você precisa logar com `roselaine@` para criar o OAuth — se quiser usar a conta da Rose pra reforçar percepção de "interno deles".

### Como colar

```bash
cd /Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS
claude
```

Depois cola tudo entre `### INÍCIO DO PROMPT ###` e `### FIM DO PROMPT ###`.

### O que mudou da v0.4 → v0.5

| Tema | v0.4 | v0.5 (MVP de hoje) |
|------|------|--------------------|
| UI | pywebview + FastAPI + HTML/Tailwind/Alpine | **Tkinter mínimo** (stdlib) |
| Capturas | xlwings + Excel local (pixel-perfect) | **Skip — TODO v0.6** |
| Histórico | Tabela Supabase + dedup | **`12 Log.txt` na própria pasta** |
| Notificação | Telegram outbound | **Removido — TODO v0.7** |
| Packaging | briefcase multi-platform | **PyInstaller `--onefile` Windows** |
| CI | GitHub Actions matriz Mac/Win/Linux | **Manual ou GH Actions Win-only futuro** |
| Dedup | Supabase consulta `numero_cedula` | **Verificar `10 Cálculo*.xlsx` na pasta** |
| Tempo | 5 dias | **1 dia** |
| Bundle | ~70MB | **~40MB** |

### Cuidados que você deve ter HOJE

**Você não tem Excel no Mac.** Quando rodar `python -m calculadora_crefaz` no seu Mac vai funcionar **TUDO menos as capturas** — mas como cortei capturas pro MVP, não tem problema. Você gera XLSX e log. A Bruna, ao abrir o XLSX no Excel dela, vê os dados preenchidos corretamente. As capturas vêm na v0.6.

**Smoke E2E sem capturas vai produzir um XLSX "incompleto" pro padrão final.** Vale conversar com a Roselaine assim: "primeira versão calcula tudo corretamente; capturas dos prints da planilha vêm na próxima versão de amanhã/dia seguinte". Validar dados antes de validar prints é caminho saudável.

**Bruna pode empacotar o `.exe` no ASUS dela:**
1. Você manda código pra ela via Drive ou WhatsApp.
2. Ela instala Python 3.11 (uma vez), `pip install -r requirements.txt pyinstaller`.
3. Roda `pyinstaller --onefile ...`.
4. Tem o `.exe` pronto.
5. Daí em diante, atualizações = você manda código novo, ela repete passo 3.

Ou: você cria o GitHub Actions Windows-only depois (v0.8), e ela só baixa o `.exe` do Releases.

### Tempo realista

Agente em Cursor com Sonnet 4.6 + sua supervisão deve fechar em **6-8h de trabalho focado**. Se travar em algum ponto operacional (OAuth Client ID não criado, template fora do lugar, etc), perde tempo desnecessário. Reservar 1h pra esses tropeços.

### Versão e changelog

**0.5.0** — 2026-04-27 (MVP de hoje, escopo cortado)
**0.4.0** — 2026-04-27 (versão completa com pywebview + xlwings + Supabase + Telegram)
**0.3.0** — 2026-04-27 (matching simplificado + BACEN dupla prioridade + capturas como arquivos)
**0.2.0** — 2026-04-27 (correção BACEN do 1º vencimento + busca em 2 níveis)
**0.1.0** — 2026-04-27 (versão inicial)
