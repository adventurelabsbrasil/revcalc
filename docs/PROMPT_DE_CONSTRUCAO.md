# Calculadora de Ação Crefaz — Prompt de Construção

> Prompt acionável para Cowork, Claude Code CLI ou Cursor construir o sistema completo de cálculo automatizado de ação contra Crefaz para a cliente Rose Portal Advocacia.
>
> Calibrado em **2026-04-27** após auditoria da planilha-base, do Drive `EMPRESTIMO DE ENERGIA` e amostragem real de 1 contrato (Adriano Luis Calistro Lourenco) e 1 PDF BACEN (02-2024.pdf).

---

## Recomendação de arquitetura (leia antes de copiar o prompt)

### O que descartei e por quê

| Opção | Avaliação |
|-------|-----------|
| Substituir planilha por sistema 100% web/Supabase | **Descartada agora.** A Rose precisa do XLSX final imprimível em A4 paisagem para protocolar. Trocar formato neste momento gera atrito desnecessário com o escritório no meio de uma relação já sob stress. Mantemos planilha como artefato de saída. |
| Skill Cowork pura | **Descartada como ponta única.** O Cowork é seu, não do escritório. Time da Rose precisa rodar isso no dia a dia — solução tem que viver no monorepo Adventure e ser invocável por humanos da Rose, não só por você via chat. |
| Google Apps Script direto na planilha | **Descartado.** Limitações fortes pra OCR de PDF, manipulação de imagens, integração com BACEN. Funciona pra MVPs simples mas trava cedo. |

### Recomendação: 2 fases

**Fase 1 — MVP Python CLI no monorepo (entrega em ~1 dia)**
- Localização: `apps/clientes/02_rose/calculo-acao-crefaz/`
- Uso: `python -m calculo_acao "Nome Completo do Cliente"`
- Saída: XLSX preenchido na pasta do cliente no Drive + log local + entrada no Supabase para histórico/dedup.
- Mantém o template `Cálculo.xlsx` 100% intacto — apenas duplica, preenche campos, embute screenshots e respeita o `print_area` original.
- **Já entrega valor real ao escritório no dia 1.**

**Fase 2 — UI web no admin existente (após validar Fase 1)**
- Path: `apps/clientes/02_rose/roseportaladvocacia/app/calculadora/page.tsx`
- Form web simples (nome + dropdown estado + botão "Calcular") chamando o módulo Python via API route Next.js.
- Histórico em Supabase já populado pela Fase 1, exibido como tabela.
- Bloqueio de reprocessamento por número de cédula.
- Time da Rose acessa pelo navegador via login Workspace.

**Phase 1 é onde concentrar o esforço inicial.** Phase 2 é evolução natural quando o fluxo manual estiver dominado.

### Por que Python e não TypeScript

- `pdfplumber` (extração de texto de PDF) é mais confiável que `pdf-parse` em Node.
- `pdf2image` (renderização de página de PDF para imagem) tem cobertura completa em Python.
- `openpyxl` permite preservar fórmulas, page setup e embutir imagens com âncora precisa em células específicas — coisa que ExcelJS faz com restrições.
- Stack é executável tanto no monorepo (script standalone) quanto invocável via Next.js API route na Fase 2 (subprocess Python ou reescrita parcial).

---

## Prompt para colar em Cowork / Claude Code / Cursor

> A partir daqui é o **prompt de construção** propriamente dito. Cole tudo abaixo no agente que vai escrever o código.

```
Você vai construir um sistema de cálculo automatizado de ação contra Crefaz para a Rose Portal Advocacia, dentro do monorepo Adventure Labs (`/Users/ribasrodrigo91/Documents/GitHub/01_ADVENTURE_LABS`).

## Contexto

A Rose move ações de revisão contratual contra a Crefaz (empréstimos com taxa de juros abusiva). Hoje o cálculo é manual e demorado: o time abre o contrato (PDF), digita os dados em uma planilha Excel de 4 abas, busca a taxa BACEN do mês/ano correspondente em outro PDF, calcula manualmente quantas parcelas o cliente já pagou, e tira prints de regiões específicas para anexar ao protocolo. O objetivo é automatizar todo esse fluxo, mantendo a planilha XLSX como output final imprimível em A4 paisagem.

## Estrutura existente que você deve usar

- Pasta-mãe no Drive: `EMPRESTIMO DE ENERGIA` (ID `1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN`), owner `contato@roseportaladvocacia.com.br`, compartilhada com `contato@adventurelabs.com.br`.

- **A pasta de cada cliente pode estar em 2 níveis** dentro da pasta-mãe:
  - **Nível 1 (estilo antigo):** direto na raiz, ex: `EMPRESTIMO DE ENERGIA/ADRIANO LUIS CALISTRO LOURENCO/`.
  - **Nível 2 (estilo novo):** dentro de subpasta de estado, ex: `EMPRESTIMO DE ENERGIA/10. RIO GRANDE DO SUL/MARLÍ SUELÍ BERGER DAMBRÓSIO/`. As subpastas de estado seguem o padrão `{NN}. {NOME DO ESTADO}` (ex: `09. PERNAMBUCO`, `10. RIO GRANDE DO SUL`, `11. BAHIA`, `12. RIO GRANDE DO NORTE`, `13. SÃO PAULO`, `14. RIO DE JANEIRO`, `15. CEARÁ`, `16. MATO GROSSO`).

  **Algoritmo de busca:** procurar o nome do cliente primeiro na raiz; se não achar, varrer todas as subpastas com prefixo `\d{2}\.\s+` e buscar dentro delas. Tolerância a trailing space e acentos.

- **Dentro de cada pasta de cliente** o PDF do contrato Crefaz pode aparecer com 3 padrões de nome:
  - `{NOME COMPLETO EM MAIÚSCULAS}.pdf` — ex: `ADRIANO LUIS CALISTRO LOURENCO.pdf` (estilo antigo)
  - `{NN} Contrato Crefaz.pdf` — ex: `09 Contrato Crefaz.pdf` (estilo novo, numerado)
  - `Contrato Crefaz.pdf` (sem numeração, raro)

  **Regex sugerida (case-insensitive, accent-insensitive):**
  ```
  ^(?:\d{2}\s+)?contrato\s+crefaz.*\.pdf$
  OR
  ^{NOME_NORMALIZADO}\.pdf$
  ```

  Outros documentos da pasta (procuração, CNH, declarações, extratos, CTPS, contrato de honorários, CPF, comprovante endereço, pesquisa IR) **não devem ser tocados**.

- **Pasta de modelos/BACEN:** `03. MODELOS/Série do Bacen/` (ID `1w8aWxOURJewINVPlyGKlitEE-EpStWUe`) com 70+ PDFs no padrão `MM-YYYY.pdf` (ex: `09-2025.pdf`, `02-2026.pdf`). Cada PDF é a captura do SGS BCB com as séries 20742 (taxa anual) e 25464 (taxa mensal). **Ignorar arquivos com prefixo `Cópia de`** (são duplicados acidentais).

- **Template da planilha:** `apps/clientes/02_rose/calculo-acao-crefaz/templates/Calculo.xlsx` (você vai copiar pra cá o `Cálculo.xlsx` que está em `_uploads/` do Cowork — antes de começar, mover/copiar pra esse path).

- **Convenção de numeração de arquivos na pasta da cliente** (observada em pastas processadas, ex: Marlí):
  - `01` — Procuração
  - `02` — Declaração de Necessidade
  - `03` — ID
  - `04` — Comprovante de endereço
  - `05` — Extrato (benefício / mensal)
  - `06` — Declaração de Isenção do IRPF
  - `07` — CPF
  - `08` — Pesquisa IR
  - `09` — Contrato Crefaz
  - `10` — Cálculo (XLSX gerado por este sistema) ← **a confirmar com Rodrigo**
  - `11` — Séries Temporais (PDF BACEN copiado pela rotina) ← **confirmado**

  Esta convenção define o nome dos artefatos de saída (passo 14 e 15 abaixo).

## Estrutura da planilha-template (não alterar layout, fórmulas nem page setup)

4 abas, uma por faixa de prazo:
- `PRICE 24X` — para contratos com 1 a 24 parcelas. Layout: paisagem A3, scale 83%, print_area `C1:CC155`.
- `PRICE 36x` — 25 a 36 parcelas. Layout: paisagem A4, scale 60%, print_area `C2:CC156`.
- `PRICE 48x` — 37 a 48 parcelas. Layout: **portrait A4** atualmente (scale 52%) — ATENÇÃO: o usuário pediu folha paisagem imprimível. Investigar com ele se quer corrigir esta aba para paisagem.
- `PRICE 60x` — 49 a 60 parcelas. Layout: paisagem A4, scale 75%, print_area `C2:CC156`.

**Mapeamento campo planilha → campo do contrato Crefaz** (refere-se à aba `PRICE 24X` como base; offset de +1 linha nas demais abas):

| Célula | Campo da planilha | Origem no contrato |
|--------|-------------------|---------------------|
| C1 | Título "CÁLCULOS DA OPERAÇÃO Nº {nº cédula} - CLIENTE: {NOME} x BANCO CREFAZ" | Cabeçalho contrato + Item I.EMITENTE Nome |
| D3 | Data da pactuação | Item II "Data de Emissão" |
| I7 | Valor principal financiado | Item II "Valor Nominal" |
| I8 | Seguros | (em geral 0; se contrato não trouxer, deixar 0) |
| I9 | TAC | Item II "Tarifas" |
| I10 | Registro | (em geral 0) |
| I11 | Avaliação | (em geral 0) |
| I12 | Outros | (em geral 0) |
| I13 | IOF | Item II "Tributos/IOF" |
| I15 | Quantidade de parcelas | Item II "Prazo" |
| I16 | Valor da parcela cobrada | Item II "Valor da Prestação" |
| I17 | Taxa pactuada | Item II **"Taxa de Juros Mensal"** (5ª linha do bloco II — NÃO usar a "Taxa de Juros Anual" que é a 7ª linha) |
| AP15 | Taxa média BACEN | Campo 25464 do PDF BACEN do mês/ano do **1º Vencimento** (não da Data de Emissão). Confirmado pelo caso Marlí: emissão 29/12/2025, 1º vencimento 02/02/2026, BACEN usado é `02-2026.pdf` (taxa 6,47%). |
| BL8 | Quantidade de parcelas pagas | Cálculo: meses_entre(hoje, "1º Vencimento" do Item II), com floor; nunca maior que I15 |

**Outros campos importantes na planilha (apenas para verificar consistência, não preencher):**
- AP7 = `=I7` (cópia do valor principal limpa)
- AP13 = `=I13` (cópia IOF)
- AP14 = `=SUM(AP7:AZ13)` (valor financiado ajustado, sem TAC e seguros)
- AP16 = parcela recalculada com taxa média (cálculo PRICE)
- AP18 = diferença cobrada por parcela
- AP19 = montante cobrado a mais total
- BL10 = total pago = BL8 * BL9
- BL11 = saldo devedor atualizado
- AE30 = `=H30/AI30-100%` (percentual taxa superior à média)

## Fluxo do programa (CLI Python)

Comando alvo: `python -m calculo_acao "Adriano Luis Calistro Lourenco"` (ou flag `--from-stdin` aceitando JSON via pipe).

### Pipeline

1. **Validar entrada.** Nome com pelo menos 2 palavras. Normalizar acentos para matching no Drive (mas preservar acentos para output).

2. **Autenticar no Drive.** Service account com escopo Drive readonly + write na pasta da cliente. Carregar credenciais de `INFISICAL_SECRET_GDRIVE_ROSE_SA_JSON` ou de `~/.config/gdrive-adventure-rose/sa.json`. **Nunca commitar credenciais.**

3. **Localizar pasta do cliente (busca em 2 níveis).**
   - **Nível 1 — raiz:** buscar `title` igual ao nome (case-insensitive, sem acentos, com tolerância a espaços extras) com `parentId = '1OciPZU1-C54kRk7C8QWyIGUb8od7mWcN'`.
   - **Nível 2 — subpastas de estado:** se Nível 1 não achou, listar todas as subpastas que começam com `\d{2}\.\s+` (regex) dentro da raiz; para cada uma, buscar a pasta do cliente. Pode acontecer que o nome do cliente esteja em ambos os níveis — nesse caso, alertar como ambiguidade (raro mas possível).
   - Caso a pasta apareça com **trailing space** no `title` (vimos isso em várias clientes), o match deve ser tolerante (`title.strip().casefold() == nome_normalizado.casefold()`).
   - Se 0 resultados em ambos os níveis → erro `"PASTA NÃO ENCONTRADA: nenhuma pasta com nome '{nome}' em EMPRESTIMO DE ENERGIA (verificadas a raiz e {N} subpastas de estado)"`. Sugerir 3 pastas mais próximas por similaridade (Levenshtein/rapidfuzz) para ajudar a corrigir digitação.
   - Se >1 resultado em níveis distintos ou no mesmo → erro `"PASTA AMBÍGUA"` listando os matches com path completo (ex: `EMPRESTIMO DE ENERGIA/10. RIO GRANDE DO SUL/{cliente}/`).

4. **Localizar contrato Crefaz dentro da pasta do cliente.**
   - Critério: arquivo `application/pdf` cujo `title` (sem `.pdf`) bate em pelo menos um dos padrões:
     - **Padrão antigo:** `title` (sem extensão) é EXATAMENTE igual ao nome do cliente (case-insensitive, sem acentos). Ex: `ADRIANO LUIS CALISTRO LOURENCO.pdf`.
     - **Padrão novo numerado:** regex `^\d{2}\s+contrato\s+crefaz.*\.pdf$` (case-insensitive). Ex: `09 Contrato Crefaz.pdf`.
     - **Padrão simples:** regex `^contrato\s+crefaz.*\.pdf$` (case-insensitive). Ex: `Contrato Crefaz.pdf`.
   - **Excluir explicitamente** PDFs que casem com qualquer um dos prefixos abaixo (são docs auxiliares, NUNCA é o contrato Crefaz mesmo que tenha "Contrato" no nome):
     - `01 Procuração`, `02 CNH`, `02 Declaração`, `03 Declaração`, `03 ID`, `04 Comprovante`, `05 Extrato`, `06 Declaração`, `07 CPF`, `08 Pesquisa`, `10 Cálculo`, `10 Calculo`, `11 Series`, `11 Séries`, `12 series`, `Contrato Honorários`, `Contrato honorários`, `Contrato de Honorários`, `Declaração de Isenção`, `Declaração isenção`, `Situação CPF`, `Kit Procuração`.
   - Se 0 resultados → erro `"CONTRATO CREFAZ NÃO ENCONTRADO em '{path da pasta}'. Padrões tentados: {NOME}.pdf, NN Contrato Crefaz.pdf, Contrato Crefaz.pdf"`.
   - **Se 2 ou mais contratos para a mesma pessoa → BLOQUEIO obrigatório**, conforme regra do escritório. Mensagem: `"BLOQUEIO: foram encontrados {N} contratos Crefaz nesta pasta. Não é possível processar automaticamente. Contratos: {lista de nomes}. Resolva manualmente ou especifique qual processar com flag --contrato '{nome do arquivo}'"`.

5. **Baixar e extrair texto do contrato.** Usar `pdfplumber`. Salvar PDF temporariamente em `apps/clientes/02_rose/calculo-acao-crefaz/cache/contratos/{nome_normalizado}/{nome_arquivo}`.

6. **Parser do Item II.EMPRÉSTIMO CONCEDIDO.**
   - Localizar bloco entre `II.EMPRÉSTIMO CONCEDIDO:` e `III.CUSTO EFETIVO TOTAL` (variações: `III - CUSTO EFETIVO TOTAL`, `III.LIBERAÇÃO`).
   - Regex para cada campo (testar com tolerância a espaços e quebras de linha):
     - `Data de Emissão:\s*(\d{2}/\d{2}/\d{4})`
     - `Prazo:\s*(\d+)`
     - `1º Vencimento:\s*(\d{2}/\d{2}/\d{4})`
     - `Último Vencimento:\s*(\d{2}/\d{2}/\d{4})`
     - `Valor Nominal:\s*R\$\s*([\d.,]+)`
     - `Valor do Empréstimo:\s*R\$\s*([\d.,]+)`
     - `Valor Total Contratado:\s*R\$\s*([\d.,]+)`
     - `Valor da Prestação:\s*R\$\s*([\d.,]+)`
     - `Taxa de Juros Mensal:\s*([\d,]+)%`
     - `Taxa de Juros Anual:\s*([\d,]+)%` (apenas para validação, NÃO usar como taxa pactuada)
     - `Tributos/IOF:\s*R\$\s*([\d.,]+)`
     - `Tarifas:\s*R\$\s*([\d.,]+)`
   - Localizar nº da cédula no cabeçalho: `CÉDULA DE CRÉDITO BANCÁRIO N\.º\s*(\d+)`.
   - Localizar nome do emitente: dentro do bloco `I.EMITENTE`, padrão `Nome:\s*(.+?)\s+CPF`.
   - **Validar:** se Valor Nominal + Tributos/IOF não bater com Valor do Empréstimo (com tolerância de R$ 1,00), avisar inconsistência. Não bloquear, apenas warning.

7. **Calcular parcelas pagas.**
   - `parcelas_pagas = max(0, min(prazo, número_de_meses_entre(hoje, primeiro_vencimento)))`
   - Onde `meses_entre(d1, d0) = (d1.year - d0.year) * 12 + (d1.month - d0.month) + (1 se d1.day >= d0.day else 0)`. Validar com 2-3 casos de borda.

8. **Localizar PDF BACEN.**
   - Pasta `03. MODELOS/Série do Bacen` (ID `1w8aWxOURJewINVPlyGKlitEE-EpStWUe`).
   - **Mês/ano alvo: o do `1º Vencimento` do contrato (NÃO da Data de Emissão).** Confirmado pelo caso real da Marlí: emissão 29/12/2025, 1º vencimento 02/02/2026 → BACEN usado é `02-2026.pdf` (taxa 6,47%).
   - Arquivo: `{MM}-{YYYY}.pdf` baseado em `primeiro_vencimento.month` e `primeiro_vencimento.year`.
   - Exemplo Adriano: 1º vencimento 27/10/2025 → arquivo `10-2025.pdf`.
   - Exemplo Marlí: 1º vencimento 02/02/2026 → arquivo `02-2026.pdf`.
   - Se não existir → erro `"BACEN NÃO ENCONTRADO: PDF '{MM}-{YYYY}.pdf' não está em Série do Bacen. Verificar se a equipe da Rose (provavelmente Bruna) já fez upload do mês de referência (mês do 1º vencimento). Lembrete: o BACEN só fica disponível no SGS-BCB algumas semanas após o fim do mês de referência."`.
   - **Ignorar arquivos com prefixo `Cópia de`** na pasta — são duplicados acidentais.

9. **Extrair taxa do BACEN.** Texto do PDF tem padrão:
   ```
   Data mês/AAAA  20742 % a.a.  25464 % a.m.
   {mês}/{ano}    {valor_anual}  {valor_mensal}
   ```
   Extrair `valor_mensal` (campo 25464). Formato brasileiro com vírgula decimal — converter `5,58` para `0.0558`.
   Regex: `(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)/\d{4}\s+([\d,]+)\s+([\d,]+)` — pegar grupo 2.

10. **Decidir aba do template.**
    - prazo ≤ 24 → `PRICE 24X`
    - 25 ≤ prazo ≤ 36 → `PRICE 36x`
    - 37 ≤ prazo ≤ 48 → `PRICE 48x`
    - 49 ≤ prazo ≤ 60 → `PRICE 60x`
    - prazo > 60 ou inválido → erro `"PRAZO FORA DO TEMPLATE: planilha não cobre {prazo} parcelas"`.

11. **Gerar XLSX preenchido.**
    - `openpyxl.load_workbook("templates/Calculo.xlsx")`
    - Selecionar a aba certa. **Apagar as outras 3 abas** (queremos uma única aba na planilha de saída — confirmar com Rodrigo).
    - Preencher células conforme mapeamento. Preservar formato (datas, percentuais, moeda).
    - **Não tocar** em fórmulas, formatação, page setup, print_area, scale, orientation.
    - Verificar que `ws.page_setup.orientation == 'landscape'` em todas as abas exceto PRICE 48x (esta tem que confirmar com usuário). Se for emitido em PRICE 48x, **forçar landscape** com aviso no log.

12. **Renderizar e capturar screenshots.**

    Você precisa de 6 imagens, na ordem que o usuário especificou:

    | # | O que captura | Como capturar |
    |---|---------------|----------------|
    | 1 | Item II.EMPRÉSTIMO CONCEDIDO do contrato Crefaz | `pdf2image.convert_from_path()` da página do contrato que contém o bloco; recortar com `Pillow` na região (calcular bbox via `pdfplumber.page.search()` para localizar a string "II.EMPRÉSTIMO CONCEDIDO" e estender ~600px abaixo). |
    | 2 | Séries temporais selecionadas — do BACEN | Renderizar a primeira página do PDF BACEN inteira (é uma página só, screenshot direto). |
    | 3 | Quadros "PERCENTUAL DA TAXA SUPERIOR À MÉDIA" + "TOTAL NOMINAL DE COBRANÇAS INDEVIDAS" | Capturar da própria planilha após preenchimento. Usar `libreoffice --headless --convert-to png` ou `subprocess` com `unoconv`/`headless-libreoffice` para renderizar a aba e recortar a região (linhas 29-30 colunas A_:Ae aproximadamente). |
    | 4 | Tabelinha VALORES RECALCULADOS | Mesma técnica do print 3, recorte das linhas 6-19 colunas AD:AZ. |
    | 5 | Tabelinha PARCELA COM TAXA MÉDIA E EXPURGO DE ABUSIVIDADES | Recorte das linhas 25-40 colunas AD:AZ. |
    | 6 | Idêntico ao print 4 (per requisito do usuário — duplicado intencionalmente) | Reusa o mesmo arquivo do print 4. |

    Estratégia de renderização da planilha sem descaracterizar:
    - Salvar XLSX preenchido em `cache/{cliente}/{cedula}_preview.xlsx`
    - `subprocess.run(["libreoffice", "--headless", "--calc", "--convert-to", "pdf", caminho_xlsx])` — gera PDF da aba (mais consistente que PNG direto).
    - Converter PDF gerado em imagens com pdf2image.
    - Recortar regiões com Pillow usando bbox calculado a partir do conhecimento do print_area.

13. **Embutir screenshots na planilha final.**
    - O usuário pediu que os prints fiquem na planilha final, em página imprimível.
    - **Decisão de design:** criar uma região "Anexos visuais" no final da aba (abaixo do print_area atual) com cabeçalho "ANEXOS — PRINTS DE COMPROVAÇÃO". As 6 imagens entram lá em sequência, dimensionadas para caberem na largura da página A4 paisagem.
    - Estender o `print_area` para incluir essa região (ex: de `C1:CC155` para `C1:CC{155+altura_anexos}`).
    - Configurar quebra de página entre o cálculo e os anexos (`ws.row_breaks.append(...)`).
    - Imagens via `from openpyxl.drawing.image import Image; ws.add_image(img, "C160")` (ajustar célula).
    - **Garantir que cada print tenha legenda em célula acima:** "Print 1 — Item II do contrato", "Print 2 — Séries Temporais BACEN", etc.

14. **Salvar XLSX final + copiar BACEN para a pasta da cliente.**

    **(a) XLSX preenchido:**
    - Path local: `apps/clientes/02_rose/calculo-acao-crefaz/outputs/CALCULO_{NOME}_{NUMERO_CEDULA}_{YYYY-MM-DD}.xlsx`
    - Nome canônico para upload no Drive: **`10 Cálculo {NOME}.xlsx`** (seguindo a convenção de numeração observada na pasta da Marlí: 09=Contrato, 10=Cálculo, 11=Séries Temporais). **Confirmar com Rodrigo se este é o nome certo antes de codar; pode ser `10 Cálculo Recálculo.xlsx` ou variante.**
    - Upload para a pasta da cliente no Drive (mesma pasta de onde veio o contrato).
    - **Validar tamanho máximo** (esperado < 10 MB; alertar se passar).

    **(b) PDF BACEN copiado para a pasta da cliente:**
    - Baixar o PDF BACEN escolhido (passo 8) da pasta `Série do Bacen`.
    - **Renomear** para `11 Series Temporais.pdf` (sem acento em "Series" — é o padrão observado na pasta da Marlí; **confirmar grafia com Rodrigo**, pode ser `11 Séries Temporais.pdf` em alguns casos).
    - Upload para a pasta da cliente no Drive.
    - Se já existir um `11 Series Temporais.pdf` na pasta, sobrescrever **apenas com flag `--force`**; sem flag, alertar e parar.

    **(c) Idempotência:**
    - Antes de fazer upload, comparar SHA-256 do PDF BACEN local vs. o que já existe no Drive (se existir). Se igual, pular o upload e apenas registrar no log.

15. **Registrar no Supabase (tabela `adv_rose_calculos_crefaz`).**
    - Schema sugerido:
      ```sql
      CREATE TABLE adv_rose_calculos_crefaz (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        nome_cliente text NOT NULL,
        cpf_cliente text,
        numero_cedula text NOT NULL UNIQUE,
        data_emissao date NOT NULL,
        prazo int NOT NULL,
        valor_nominal numeric(12,2) NOT NULL,
        taxa_juros_mensal numeric(8,5) NOT NULL,
        taxa_media_bacen numeric(8,5) NOT NULL,
        parcelas_pagas int NOT NULL,
        aba_template text NOT NULL,
        xlsx_drive_id text,
        xlsx_drive_url text,
        contrato_drive_id text NOT NULL,
        bacen_pdf_id text NOT NULL,
        created_at timestamptz DEFAULT now(),
        created_by text NOT NULL,
        contrato_hash text NOT NULL,
        observacoes text
      );
      CREATE INDEX idx_adv_rose_calculos_nome ON adv_rose_calculos_crefaz USING gin (to_tsvector('portuguese', nome_cliente));
      ```
    - **Bloqueio de duplicidade:** antes de gerar, consultar `numero_cedula`. Se já existir, retornar erro `"CÁLCULO JÁ EXISTE: cédula nº {x} já foi processada em {data}, link: {drive_url}"` com flag `--force` para sobrescrever.

16. **Output do CLI.**
    - Modo verbose por padrão (cada passo logado).
    - Modo `--quiet` para uso programático (apenas JSON de resposta no stdout).
    - JSON de resposta:
      ```json
      {
        "status": "ok|erro|bloqueio",
        "cliente": "...",
        "cedula": "...",
        "xlsx_local": "/path/to/CALCULO_*.xlsx",
        "xlsx_drive_url": "https://...",
        "supabase_id": "uuid",
        "warnings": [],
        "duracao_segundos": 12.3
      }
      ```

## Estrutura de pastas a criar

```
apps/clientes/02_rose/calculo-acao-crefaz/
├── README.md                               # documentação operacional
├── pyproject.toml                          # python project (poetry ou pip-tools)
├── requirements.txt                        # versões pinadas
├── calculo_acao/
│   ├── __init__.py
│   ├── __main__.py                         # entry point CLI
│   ├── cli.py                              # parser argparse
│   ├── drive.py                            # Google Drive client + busca pasta/contrato/BACEN
│   ├── parser_contrato.py                  # extração do Item II
│   ├── parser_bacen.py                     # extração campo 25464
│   ├── calculadora.py                      # cálculo de parcelas pagas, decisão de aba
│   ├── planilha.py                         # carregamento, preenchimento, print_area
│   ├── prints.py                           # captura de screenshots (contrato + BACEN + planilha)
│   ├── supabase_client.py                  # registro e dedup
│   ├── config.py                           # constantes (IDs Drive, paths)
│   └── exceptions.py                       # PastaNaoEncontrada, ContratoAmbiguo, BloqueioDuplicidade etc
├── tests/
│   ├── fixtures/
│   │   ├── contrato_adriano.pdf            # contrato real (gitignored)
│   │   ├── bacen_09_2025.pdf               # BACEN real (gitignored)
│   │   └── Calculo_template.xlsx           # cópia do template
│   ├── test_parser_contrato.py
│   ├── test_parser_bacen.py
│   ├── test_calculadora.py
│   └── test_pipeline_e2e.py                # smoke test com mock do Drive
├── templates/
│   └── Calculo.xlsx                        # template original (versionado)
├── cache/                                  # gitignored — PDFs baixados, intermediários
├── outputs/                                # gitignored — XLSX gerados localmente
└── PROMPT_DE_CONSTRUCAO.md                 # este arquivo
```

`.gitignore` deve cobrir `cache/`, `outputs/`, `tests/fixtures/*.pdf`.

## Stack obrigatória

- Python 3.11+ (compatível com 3.12).
- `pdfplumber` — extração de texto e bbox de PDF.
- `pdf2image` — renderização de página de PDF para PIL Image (depende de poppler instalado no sistema).
- `Pillow` — manipulação de imagens (recorte, redimensionamento).
- `openpyxl` — manipulação de XLSX preservando fórmulas e page setup.
- `google-api-python-client` + `google-auth` — Drive API.
- `supabase-py` — registro e dedup.
- `python-dateutil` — cálculos de meses entre datas.
- `unidecode` — normalização de acentos para matching.
- `rapidfuzz` — sugestão de pastas próximas em caso de erro.
- LibreOffice headless ou similar — renderização da planilha para imagem (instalar como dependência de sistema, documentar no README).

## Critérios de aceite (testes obrigatórios)

### Smoke E2E nº 1 — Adriano (estilo antigo, pasta na raiz, contrato com nome do cliente)

`python -m calculo_acao "Adriano Luis Calistro Lourenco"` deve gerar XLSX com:
- C1 contendo `"CÁLCULOS DA OPERAÇÃO Nº 3867296 - CLIENTE: ADRIANO LUIS CALISTRO LOURENCO x BANCO CREFAZ"`
- D3 = 22/09/2025
- I7 = 1000.00
- I9 = 0.00 (Tarifas)
- I13 = 25.10 (IOF)
- I15 = 12
- I16 = 226.79
- I17 = 0.1877 (18,77% / 100)
- AP15 = taxa BACEN de **outubro/2025** (mês do 1º vencimento 27/10/2025) — buscar valor real do `10-2025.pdf`
- BL8 = parcelas pagas calculadas (com data de hoje, considerando 1º vencimento 27/10/2025)
- 6 imagens embutidas após o print_area

Localização da pasta: `EMPRESTIMO DE ENERGIA/ADRIANO LUIS CALISTRO LOURENCO/` (raiz).
Contrato: `ADRIANO LUIS CALISTRO LOURENCO.pdf` (padrão antigo).
Aba selecionada: `PRICE 24X` (12 parcelas).

### Smoke E2E nº 2 — Marlí (estilo novo, pasta dentro de estado, contrato numerado)

`python -m calculo_acao "Marli Sueli Berger Dambrosio"` deve gerar XLSX com:
- C1 contendo `"CÁLCULOS DA OPERAÇÃO Nº 4095068 - CLIENTE: MARLI SUELI BERGER DAMBROSIO x BANCO CREFAZ"`
- D3 = 29/12/2025
- I7 = 3500.00
- I9 = 0.00
- I13 = 104.99
- I15 = 18
- I16 = 585.53
- I17 = 0.1449 (14,49% / 100)
- AP15 = **0.0647** (taxa BACEN fev/2026, mês do 1º vencimento 02/02/2026 — confirmado lendo o `11 Series Temporais.pdf` real da pasta dela)
- BL8 = parcelas pagas calculadas
- 6 imagens embutidas

Localização da pasta: `EMPRESTIMO DE ENERGIA/10. RIO GRANDE DO SUL/MARLÍ SUELÍ BERGER DAMBRÓSIO/` (Nível 2).
Contrato: `09 Contrato Crefaz.pdf` (padrão novo numerado).
Aba selecionada: `PRICE 24X` (18 parcelas, ≤ 24).

**Output esperado na pasta da cliente após processamento:**
- `10 Cálculo MARLI SUELI BERGER DAMBROSIO.xlsx` (novo arquivo)
- `11 Series Temporais.pdf` (já existe, validar que SHA-256 bate com `02-2026.pdf` da Série do Bacen — não sobrescrever).

### Outros testes obrigatórios

3. **Bloqueio duplicidade:** rodar 2x seguidas o mesmo nome → segunda execução retorna erro com link da primeira (consulta Supabase por `numero_cedula`).
4. **Pasta ambígua:** simular nome encontrado em 2 níveis (raiz + estado) → erro listando os 2 paths.
5. **Pasta apenas em estado:** verificar que a busca em Nível 2 funciona (caso Marlí).
6. **Contrato múltiplo:** simular pasta com 2 PDFs que casem com algum dos 3 padrões → BLOQUEIO obrigatório.
7. **BACEN ausente:** apagar o PDF do mês do 1º vencimento temporariamente → erro claro com mensagem mencionando equipe da Rose.
8. **Prazo fora do template:** contrato com 72 parcelas → erro.
9. **XLSX final imprimível em A4 paisagem:** validar via `libreoffice --convert-to pdf` e checar `paperSize == 9` + `orientation == 'landscape'`.
10. **PDF BACEN copiado para a pasta da cliente** com nome `11 Series Temporais.pdf` (validar idempotência por SHA-256).
11. **Nomes com acentos** (caso Marlí: `MARLÍ SUELÍ BERGER DAMBRÓSIO`) — input do usuário pode ou não ter acentos, matching tem que funcionar nos dois casos via `unidecode`.

## Restrições críticas (não negociáveis)

- **NUNCA descaracterizar a planilha.** Manter as fórmulas, formatação condicional, page setup e print_area do template original. Apenas adicionar a região de anexos no final.
- **Página final imprimível em A4 paisagem.** Validar que `paperSize == 9` e `orientation == 'landscape'` no XLSX gerado.
- **Nenhum PII em log/Supabase além do necessário.** CPF salvo apenas como hash SHA-256, não em texto puro. Endereço, telefone, dados bancários do cliente NUNCA salvar em Supabase nem em log estruturado.
- **Service account com escopo mínimo.** Drive readonly + write apenas dentro de `EMPRESTIMO DE ENERGIA`.
- **Credenciais via Infisical/env, nunca hardcoded.** Documentar variáveis necessárias no README.
- **Idempotência:** rodar 2x no mesmo cliente sem `--force` deve sempre retornar o mesmo XLSX (do primeiro run).

## Investigações abertas que você deve confirmar com Rodrigo antes de codar

1. **Aba PRICE 48x está em portrait no template.** É bug do template ou intencional? (Provavelmente bug — pedir confirmação.)
2. **Apagar abas não usadas no XLSX final** (ex: gerar só PRICE 24X quando o caso for 12 parcelas) ou manter todas as 4 abas com a "ativa" preenchida e as outras zeradas? Recomendação: manter só a aba usada, mais limpo para protocolo.
3. **Onde fica a credencial do service account Drive?** (Sugerir Infisical com chave `GDRIVE_ROSE_SA_JSON`.)
4. **Quem tem permissão de escrita na pasta-mãe `EMPRESTIMO DE ENERGIA`?** O escritório (`contato@roseportaladvocacia.com.br`) é o owner; precisamos de uma service account adicionada com permissão de editor para conseguir fazer upload de volta.
5. **Tabela Supabase `adv_rose_calculos_crefaz` em qual projeto?** (Provavelmente o mesmo do `roseportaladvocacia` admin atual — confirmar.)
6. **Linha 5 do item II é "Taxa de Juros Mensal" e linha 7 é "Taxa de Juros Anual" — confirmar com Rodrigo se a regra é sempre essa contagem ou se é "taxa mensal" como rótulo.** (Recomendação: usar rótulo, mais robusto.)
7. **Convenção de numeração dos arquivos na pasta da cliente.** A pasta da Marlí mostra `09 Contrato Crefaz.pdf` e `11 Series Temporais.pdf` — sugere que `10 Cálculo {NOME}.xlsx` seria o nome canônico do XLSX gerado. Confirmar com Rodrigo (e idealmente com a Bruna/Roselaine) se essa é a convenção definitiva ou variante. Em particular: **(a)** se "Series" é sem acento ou "Séries" com acento; **(b)** se o número 10 é exclusivo do Cálculo ou pode ser usado para outros docs; **(c)** se há um número 12 reservado (talvez petição inicial?).
8. **A regra de "BACEN do mês do 1º vencimento" é sempre essa, ou em algum caso usa-se BACEN do mês da Data de Emissão?** Inferi a regra do caso Marlí (1º venc 02/02/2026 → BACEN `02-2026`). Validar com a Bruna/Roselaine que esse é o critério jurídico correto antes de codar.
9. **Pastas de cliente em mais de 2 níveis?** Verificamos raiz e subpastas de estado. Mas pode haver casos com 3+ níveis (ex: estado/cidade/cliente)? Confirmar com a equipe da Rose.

## Ordem de implementação sugerida

1. Setup do projeto (pyproject, deps, estrutura).
2. `parser_contrato.py` com testes — validar com o PDF do Adriano.
3. `parser_bacen.py` com testes — validar com 02-2024.pdf e 09-2025.pdf.
4. `calculadora.py` (parcelas pagas + decisão de aba) com testes de borda.
5. `drive.py` mockado primeiro, depois ligar com service account real.
6. `planilha.py` — carregamento e preenchimento sem prints; validar XLSX visualmente.
7. `prints.py` — captura das 6 imagens; validar visualmente.
8. Embedding de imagens na planilha + ajuste de print_area.
9. `supabase_client.py` + dedup.
10. CLI integrado + smoke E2E.
11. README operacional.

## Saída do agente que executar este prompt

Ao final, o agente deve me entregar:
- Código completo no path acima.
- README com instruções de setup (instalar poppler, libreoffice, configurar service account, configurar Supabase, rodar testes, executar CLI).
- Nota com as 6 investigações abertas respondidas (ou marcadas como pendentes para Rodrigo).
- Saída do smoke test E2E real (com Adriano).
- Lista de TODOs para Fase 2 (UI web).
```

---

## Notas para Rodrigo (não vai no prompt)

### O que mudei em relação ao seu pedido inicial

1. **Você sugeriu "talvez Python ou Supabase".** Recomendei **ambos**: Python para a extração+geração e Supabase para histórico+dedup. Decisão pragmática, fácil de evoluir.

2. **Você disse "talvez não precise mais de planilha".** Mantive a planilha porque é a peça que vai pro protocolo. **A planilha é o produto final.** A engenharia fica embaixo dela. Quando o time da Rose abrir o XLSX, vai parecer planilha do jeito que sempre foi — só já preenchido e com prints embutidos.

3. **Você falou em "sistema completo e bonito".** A Fase 2 (UI web no admin) entrega isso. Mas Fase 1 já gera o XLSX final correto — o time da Rose pode já usar enquanto a interface web é construída.

### Pontos de atenção técnica

- **A pasta `EMPRESTIMO DE ENERGIA`** é owned pelo `contato@roseportaladvocacia.com.br`, não por nós. Para o sistema fazer upload de volta, precisaremos pedir à Roselaine/Clayton para adicionar uma service account específica (sugiro criar uma `rose-calculadora@adventure-{projeto}.iam.gserviceaccount.com`) com permissão de **Editor**. Sem isso, Fase 1 só consegue baixar e gerar localmente — você teria que fazer o upload manual.

- **PDF BACEN do mês corrente nem sempre está disponível** (vem do SGS BCB no início do mês seguinte). Se o cálculo for sobre contrato emitido neste mês, o BACEN só estará disponível 4-6 semanas depois. Tratar com mensagem clara.

- **CPF e dados bancários do cliente** aparecem no contrato. O sistema vai ler isso pra extração, mas **NÃO** salva em Supabase nem em log. Apenas o número da cédula e nome ficam estruturados — o resto fica só no XLSX final que vai pra pasta da cliente.

- **A planilha tem 4 abas hoje.** Faz sentido a saída final ter só 1 aba (a do prazo certo). Mas isso é decisão sua — confirmei como pergunta aberta no prompt.

### Sobre o tempo de implementação

Fase 1 completa, com testes e smoke E2E rodando, é trabalho de **1 a 2 dias** num agente focado (Cursor/Claude Code com bom contexto). A parte mais delicada é a captura dos screenshots da planilha sem descaracterizar — isso pode levar mais tempo se o agente não tiver experiência com `libreoffice --headless`.

### Próximos passos sugeridos

1. Você revisa este prompt e responde as 6 investigações abertas (especialmente a da service account Drive).
2. Move o `Cálculo.xlsx` que está nos uploads para `apps/clientes/02_rose/calculo-acao-crefaz/templates/Calculo.xlsx` (eu não fiz isso ainda — esperando seu OK pra criar a estrutura definitiva).
3. Joga o prompt no Cursor com Claude Sonnet 4.6 ou no Claude Code CLI dentro do monorepo.
4. Quando Fase 1 estiver rodando, a gente conversa sobre Fase 2 (UI web).

---

**Versão deste documento:** 0.2.0 — 2026-04-27 (segunda revisão, após auditoria da pasta da Marlí Sueli Berger Dambrosio)
**Autor:** Jessica (Account Manager Rose) + agente Adventure
**Atualização sugerida:** após resposta das 9 investigações abertas.

## Changelog

### 0.2.0 — 2026-04-27
- **CORREÇÃO CRÍTICA:** BACEN passa a ser buscado pelo mês/ano do **1º Vencimento** do contrato, não da Data de Emissão (validado com pasta real da Marlí: emissão 29/12/2025, 1º venc 02/02/2026, BACEN usado é `02-2026.pdf`).
- Adicionada busca de pasta em 2 níveis (raiz + subpastas de estado).
- Adicionados 3 padrões de nome para o contrato Crefaz (nome cliente / `NN Contrato Crefaz` / `Contrato Crefaz`).
- Adicionada cópia do PDF BACEN para a pasta da cliente como `11 Series Temporais.pdf`.
- Adicionado segundo smoke E2E (Marlí) cobrindo o caminho novo (estado + numerado).
- Adicionada convenção de numeração observada (09=Contrato, 10=Cálculo, 11=Séries Temporais).
- 3 investigações abertas adicionais (numeração, regra BACEN, profundidade de pastas).

### 0.1.0 — 2026-04-27
- Versão inicial. Mapeamento completo da planilha (4 abas), fluxo principal de 16 passos, captura de 6 screenshots, registro Supabase, critérios de aceite e arquitetura sugerida em 2 fases.
