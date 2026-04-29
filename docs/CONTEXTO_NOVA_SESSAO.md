# Contexto para abrir nova sessão Cowork — Calculadora Crefaz

> **Como usar:** copie o bloco entre `### COLAR NA NOVA SESSÃO ###` e `### FIM ###` como **primeira mensagem** quando abrir uma nova sessão Cowork dedicada à Calculadora Crefaz. Isso passa o contexto mínimo pra eu saber de onde a gente partiu sem precisar replicar a discussão de design.

---

### COLAR NA NOVA SESSÃO ###

Estamos no projeto **Calculadora de Ação Crefaz** para o escritório Rose Portal Advocacia. Você foi briefado em outra sessão Cowork dedicada à conta Rose (Account Manager Jessica) — agora abrimos esta sessão separada pra acompanhar a implementação técnica do sistema.

## O que é o sistema

Ferramenta desktop para o escritório Rose Portal Advocacia automatizar o cálculo de ações de revisão contratual contra a Crefaz (taxa de juros abusiva em empréstimos consignados em conta de energia). Recebe o nome do cliente, lê o contrato Crefaz no Drive, extrai dados, busca taxa BACEN, preenche planilha modelo e devolve XLSX preenchido + log na pasta do cliente.

## Estado atual

Após 5 rodadas de discussão de arquitetura, fechamos um **MVP enxuto pra rodar em 1 dia** (escopo cortado vs. versão completa).

**Stack do MVP (v0.5.0):**
- CLI Python 3.11 + UI Tkinter mínima (stdlib)
- Auth OAuth Workspace desktop flow (loopback + PKCE)
- `pdfplumber` (parse contrato), `openpyxl` (preenche XLSX), `google-api-python-client` (Drive)
- Empacotamento via PyInstaller `--onefile` Windows
- Histórico em `12 Log.txt` na pasta da cliente (sem Supabase)

**Cortes vs. versão completa (ficam para iterações futuras):**
- Capturas pixel-perfect via xlwings + Excel → v0.6 (Bruna testa no ASUS)
- Notificação Telegram outbound → v0.7
- GitHub Actions Windows-only → v0.8
- Mac binary → v0.9
- Code signing → v1.0
- Histórico Supabase → v1.1
- Contratos quitados → v2.0

## Localização dos artefatos

Tudo dentro de `apps/clientes/02_rose/calculo-acao-crefaz/`:

- `PROMPT_PARA_COLAR.md` (v0.5.0) — prompt acionável pra colar no Cursor/Claude Code, define todo o sistema.
- `PROMPT_DE_CONSTRUCAO.md` (v0.2.0) — doc de design completo que originou o prompt; útil pra consultar decisões de arquitetura.
- `templates/Calculo.xlsx` — template da planilha (pendente de mover do upload do Cowork).
- `CONTEXTO_NOVA_SESSAO.md` — este arquivo.

Contexto de conta da Rose mais amplo:
- `apps/core/admin/agents/skills/jessica-conta-rose/SKILL.md` — Account Manager dedicada à conta Rose.
- `clients/02_rose/CONTEXTO_WHATSAPP_ROSE_2026-04.md` — síntese operacional da relação.
- `apps/core/admin/agents/skills/jessica-conta-rose/references/DRIVE_INDICE.md` — mapa do Drive Rose.

## Decisões já fechadas (não revisitar)

1. **Stack:** Python + Tkinter + PyInstaller (decidido após considerar pywebview, Tauri, Electron, Google Chat bot, Telegram bot, app web Next.js).
2. **Renderização de prints:** xlwings + Excel local em modo invisível (decidido após considerar libreoffice, weasyprint, Google Sheets API). Mas **fora do MVP de hoje** (v0.6).
3. **Auth:** OAuth Workspace desktop flow individual de cada usuário (sem service account, sem domain delegation).
4. **Histórico:** `12 Log.txt` na pasta da cliente (sem Supabase no MVP).
5. **Matching de contrato:** apenas `NN Contrato Crefaz.pdf` ou `Contrato Crefaz.pdf` (fluxo humano renomeia antes; padrão antigo fora).
6. **BACEN:** prioridade dupla — pasta da cliente primeiro, fallback `Série do Bacen/MM-YYYY.pdf`. **Mês de referência é o do 1º Vencimento, não da Data de Emissão.**
7. **Pasta da cliente:** busca em 2 níveis (raiz + subpastas de estado).

## Setups pendentes antes do agente começar

1. Mover `Cálculo.xlsx` (que está em `_uploads/` da sessão Cowork anterior) para `apps/clientes/02_rose/calculo-acao-crefaz/templates/Calculo.xlsx`, **renomeando para `Calculo.xlsx` sem acento**.
2. Criar OAuth Client ID Desktop no Google Cloud Console (tipo "Desktop app", tela "Interna" restringindo ao Workspace Rose). Salvar `client_id` em `.env` local.

## Próximas ações imediatas

- **Você (Rodrigo):** completa os 2 setups acima e cola `PROMPT_PARA_COLAR.md` no Cursor com Sonnet 4.6.
- **Eu (nesta sessão):** acompanho o agente, valido outputs, dou apoio operacional, mantenho registro do progresso.

## Smoke tests de validação

Dois clientes-fixture já mapeados pra testar:

**Adriano Luis Calistro Lourenco** (caso legado, pasta na raiz `EMPRESTIMO DE ENERGIA/`):
- Cédula 3867296, emissão 22/09/2025, prazo 12, valor R$ 1.000, taxa 18,77%, IOF R$ 25,10
- 1º vencimento 27/10/2025 → BACEN `10-2025`
- Aba esperada: `PRICE 24X`

**Marlí Suelí Berger Dambrósio** (caso atual, dentro de `10. RIO GRANDE DO SUL/`):
- Cédula 4095068, emissão 29/12/2025, prazo 18, valor R$ 3.500, taxa 14,49%, IOF R$ 104,99
- 1º vencimento 02/02/2026 → BACEN `02-2026` (taxa 6,47% / `0.0647`)
- Pasta dela já tem `11 Series Temporais.pdf` — sistema deve usar esse, não copiar do Série do Bacen.
- Aba esperada: `PRICE 24X` (18 ≤ 24)

## Como me chamar nesta sessão

Tudo relacionado à implementação técnica da Calculadora Crefaz (código, deploy, testes, ajustes do prompt, validação de outputs do agente). Não me confunda com a Jessica — ela é a Account Manager da conta Rose como um todo (relacionamento, calibração de mensagens, status comercial). Nesta sessão sou eu, agente Adventure dedicado à entrega da ferramenta técnica.

Comece me perguntando o que precisar — código gerado pelo agente, validação de smoke test, dúvida operacional sobre OAuth, qualquer coisa.

### FIM ###

---

## Notas pra você (não vai pra nova sessão)

### Quando abrir a nova sessão

Cole o bloco acima como **primeira mensagem** na nova sessão Cowork. Eu vou ler o `PROMPT_PARA_COLAR.md` e o `PROMPT_DE_CONSTRUCAO.md` automaticamente quando precisar.

### Como nomear a nova sessão Cowork

Sugestões:
- "Calculadora Crefaz · implementação"
- "Crefaz MVP · acompanhamento"
- "Rose Crefaz · v0.5"

### Esta sessão atual

Mantém viva pra:
- Evolução da skill `jessica-conta-rose` (Account Manager).
- Próximas atualizações da síntese WhatsApp Rose.
- Outras coordenações relacionais com a conta Rose (preparação de reunião, calibração de mensagem pra Roselaine, etc).
- Não pra falar de código da Calculadora — isso é da nova sessão.

### Fluxo recomendado

1. Você abre Cowork novo agora, cola o bloco acima, eu confirmo que entendi.
2. Você completa os 2 setups (mover xlsx + criar OAuth Client ID).
3. Você abre Cursor com Sonnet 4.6 no monorepo, cola `PROMPT_PARA_COLAR.md`.
4. Cursor codifica o sistema; nova sessão Cowork acompanha.
5. Quando o agente do Cursor terminar, validamos juntos na nova sessão Cowork.
