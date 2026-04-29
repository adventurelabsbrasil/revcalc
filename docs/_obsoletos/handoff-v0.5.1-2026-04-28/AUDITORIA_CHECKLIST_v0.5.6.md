# Auditoria do checklist — Calculadora Crefaz v0.5.6

> Sessão Cowork 2026-04-29 (continuação). Auditoria honesta dos 12 itens contra o código real do `src/calculadora_crefaz/` + `pipeline.py` + UI + packaging.

## TL;DR

Versão atual = **v0.5.6** (`pyproject.toml`). README marca v0.5.0 (desatualizado). Saltos não documentados entre v0.5.0 → v0.5.6.

10 dos 12 itens do checklist ✅ plenos. 2 itens ausentes (8 e 9 — capturas PNG, gap deliberado roadmap v0.6). 1 item parcial (12 — Mac usuário-final pendente; NPM não se aplica).

**MVP está pronto pra Bruna baixar e testar.**

---

## Tabela completa

| # | Feature | Status | Implementação real | Gap / Recomendação |
|---|---------|--------|-------------------|--------------------|
| 1 | UX nome do cliente | ✅ pleno | `ui.py:112-122`: `ttk.Entry` com label, hint "mínimo 2 palavras", Enter→Calcular, validação `len(nome.split()) < 2` | nenhum |
| 2 | Fazer login | ✅ pleno | `auth.py` completo: OAuth desktop loopback, keyring nativo (Keychain Mac, Cred Manager Win), refresh automático, restrição a domínios `roseportaladvocacia.com.br` + `adventurelabs.com.br`, logout limpa keyring | nenhum |
| 3 | Calcular | ✅ pleno | `pipeline.executar()` em 13 passos numerados; `calculadora.parcelas_pagas()` + `decidir_aba()` | nenhum |
| 4 | Log de execução + erros/avisos na UI | ✅ pleno | ScrolledText preto com 4 tags coloridas (info/aviso/ok/erro), threading via `queue.Queue`; `messagebox.showerror` com título tipado por exceção; 11 classes em `exceptions.py` | nenhum |
| 5 | Cálculo Python → DADOS preenche visual | ✅ pleno (validado nesta sessão com LibreOffice recalc) | `planilha.gerar_xlsx` detecta aba DADOS e bifurca; 220 fórmulas, 0 erros com caso Adriano | nenhum |
| 6 | Cálculo a partir de nome + contrato + BACEN | ✅ pleno | `parser_contrato` extrai Item II (cédula, nome, datas, valores, prazo, taxas), reconcilia prazo via datas, valida soma; `parser_bacen` lê linha `mes/ano ANUAL MENSAL` | nenhum |
| 7 | Visualizar XLSX em Excel/Sheets (revisão Roselaine) | ✅ pleno | XLSX no Drive da Rose, dentro da pasta da cliente; Drive web abre como Sheets ou baixa XLSX; botão "Abrir pasta no Drive" na UI | nenhum |
| 8 | Print das partes mencionadas salvas na pasta | ❌ ausente | `log_writer.py:153-155` declara explicitamente "CAPTURAS / Não geradas nesta versão (v0.5.6). Disponível em v0.6." | **gap deliberado** roadmap v0.6 com xlwings + Excel local |
| 9 | Print geral salvo na pasta | ❌ ausente | Idem item 8 | idem; em v0.6, sugestão: 1 PNG por aba PRICE + 1 PNG geral, prefixo `13 Print *.png` |
| 10 | Log salvo na pasta | ✅ pleno (com modo append) | `pipeline.py:212-245` lê log anterior, concatena com separador `="*60`, sobe; aviso destacado quando BACEN veio do repositório central; status tipado (novo/sobrescrito/mantido/append) | nenhum |
| 11 | Avisos de conclusão e erros na UI | ✅ pleno | Linha verde "✓ Pronto" + botão pasta habilitado; erros viram messagebox com título tipado + linha vermelha; avisos amarelos; confirmação ao fechar mid-cálculo | nenhum |
| 12 | Empacotamento Mac/Win/NPM | 🟡 parcial | **Windows:** `pyinstaller.spec` ✅ pronto, gera `.exe` ~40MB. **Mac (dev):** `abrir-calculadora-crefaz.command` ✅. **Mac (usuário final):** ❌ sem `.app`/`.dmg`. **NPM:** ❌ não aplicável (Python, não Node) | NPM: descartar (categoria errada). Mac usuário-final: rodar `pyinstaller --onefile --windowed` em macOS gera `.app`; alternativa mais polida é `py2app` com `.dmg` |

---

## O que está faltando ser feito antes do "Bruna baixa e testa"

### Crítico (bloqueia Bruna)

1. **Mover arquivos novos pra `main`** (template DADOS+visual, snapshot preDADOS, script de migração, docs do _handoff/). Ver `RUNBOOK_HUMANO_v2_DADOS.md`.

2. **Bumpar versão no `__init__.py`** se a migração DADOS+visual entra como v0.5.7 (ou cristalizar v0.6 se decidir que é mudança maior). Recomendo **v0.5.7** — é patch arquitetural não-quebrante (legacy continua funcionando, dual-mode).

3. **Atualizar README** (que marca v0.5.0) — vai virar 2 READMEs, ver propostas abaixo.

4. **Build Windows** no ASUS da Bruna (`pyinstaller pyinstaller.spec` → `dist/CalculadoraCrefaz.exe`). Sem isso ela não tem como rodar.

### Não-crítico (pode ir em paralelo)

5. **Build Mac** pra você (Founder) testar localmente sem ativar venv toda vez:
   ```bash
   .venv/bin/pyinstaller --onefile --windowed --name CalculadoraCrefaz \
       --add-data "templates/Calculo.xlsx:templates" \
       src/calculadora_crefaz/__main__.py
   ```
   Gera `dist/CalculadoraCrefaz.app`. Arrasta pra Aplicações.

6. **Capturas PNG (itens 8 e 9)** — só se Bruna ou Roselaine pedirem explicitamente. Roadmap v0.6.

---

## Proposta — 2 READMEs separados

### README.md (raiz do projeto, pra usuário final)

Tom: leigo, sem jargão técnico, com workflow visual. Ver arquivo separado `README_USUARIO_PROPOSTA.md` neste handoff.

### README_DEV.md (raiz do projeto, pra desenvolvedor / Cowork futuras)

Tom: técnico, com setup de ambiente, build, testes, troubleshooting. Ver arquivo separado `README_DEV_PROPOSTA.md` neste handoff.

---

## Recomendação de versionamento

Sugestão pra próximo bump:

- **v0.5.7** — DADOS+visual (template migrado, dual-mode validado)
  - Bump no `__init__.py` + `pyproject.toml`
  - Tag pushada
  - Bruna baixa essa versão e testa
- **v0.6.0** — capturas PNG (item 8 e 9) com xlwings/Excel local
- **v0.7.0** — GitHub Actions build .exe automático no tag push (elimina ASUS manual)
- **v0.8.0** — `.app` Mac empacotado (`pyinstaller` + assinatura code-signed opcional)
- **v0.9.0** — Telegram outbound (`ceo_buzz_Bot`)
- **v1.0.0** — code-signing real + binário Mac assinado + onboarding pra outros escritórios

---

## Pendências documentais

- `README.md` reescrito (v0.5.7) → `README.md` para usuário + `README_DEV.md` para dev
- `docs/RETOMAR.md` atualizado — agora aponta pra HANDOFF_PLANILHA_DADOS_VS_VISUAL.md como ponto de entrada
- `docs/template-modifications-v0.5.1-FINAL.md` pode ser arquivado — substituído por HANDOFF_PLANILHA_DADOS_VS_VISUAL.md
- Atualizar Roadmap no novo README com versionamento sugerido acima
