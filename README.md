# Calculadora de Ação Crefaz

**Versão atual:** `v0.6.1` · **Cliente:** Rose Portal Advocacia  

Ferramenta desktop que automatiza o cálculo de revisão de contratos **Crefaz**: você informa o **nome da pasta da cliente no Google Drive**; o app localiza a pasta, lê o **contrato em PDF**, obtém a **taxa BACEN** do período correto, preenche a **planilha de cálculo** e gera os **prints (PDF + PNG)** na própria pasta — prontos para conferência jurídica.

**Docs adicionais (detalhes e edge cases):**

- Técnico / PyInstaller / estrutura do repo → [`README_DEV.md`](README_DEV.md)
- Fluxo pensado para quem só instala binário + kit Rose → [`cliente-kit/README_USUARIO_FINAL.md`](cliente-kit/README_USUARIO_FINAL.md)

[![Releases](https://img.shields.io/github/v/release/adventurelabsbrasil/revcalc?display_name=release)](https://github.com/adventurelabsbrasil/revcalc/releases)
[![Baixar ZIP](https://img.shields.io/badge/baixar-codigo_zip-blue)](https://github.com/adventurelabsbrasil/revcalc/archive/refs/heads/main.zip)

---

## O que o sistema faz (resumo)

1. Login **Google OAuth** (contas autorizadas na configuração do app).
2. Busca da pasta da cliente em `EMPRESTIMO DE ENERGIA/<UF>/<NOME>/` no Drive.
3. Leitura do **`09 Contrato Crefaz.pdf`**, parsing do Item II e dos dados financeiros.
4. Uso da taxa **BACEN** (PDF **`11 Series Temporais.pdf`** na pasta ou cópia do repositório central da Rose quando faltar).
5. Geração do **`10 Cálculo …xlsx`**, **`12 Log.txt`** (append) e arquivos **`13 Print …`** (planilha + blocos regionais + trechos dos PDFs).

**Tempo médio:** cerca de 30–60 segundos por execução (rede + tamanho do PDF).

### Fluxo visual

```mermaid
flowchart LR
    A([Nome da pasta no Drive]) --> B{Login Google}
    B -->|primeira vez| C[Autorizar no navegador]
    B -->|sessão OK| D[Localiza pasta …/UF/cliente]
    C --> D
    D --> E[Lê contrato PDF]
    E --> F[Resolve BACEN]
    F --> G[Gera planilha + capturas]
    G --> H[Escreve PDF/PNG/log na pasta]
```

**Sem LibreOffice instalado**, o app ainda gera **XLSX + log**, mas pode **omitir** as capturas `13 Print` até o LibreOffice ficar instalado e disponível ao processo (`soffice` no PATH no Windows/Linux).

---

## Como instalar (recomendado: terminal + código-fonte)

Use este fluxo quando quiser rodar **a mesma árvore que está na branch `main`**, sem depender de `.exe` na página de Releases.

### Pré-requisitos em qualquer sistema

| Item | Observação |
|------|------------|
| **Git** | Para `git clone`. |
| **Python 3.11+** | Check: `python --version` ou `py -3.11 --version`. |
| **LibreOffice** | Necessário para gerar **`13 Print`**. Sem ele, só XLSX + log. |

**Credenciais Google OAuth:** o app espera arquivo de cliente/credencial conforme o projeto (`cliente_secret.json` ou variáveis `.env`). O detalhe de nomes de arquivo e scopes está em **`README_DEV.md`** — não commitar secrets.

---

### Windows (CMD ou PowerShell)

Abra **CMD** ou **PowerShell** na pasta onde quer o projeto:

```bat
git clone https://github.com/adventurelabsbrasil/revcalc.git
cd revcalc

py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
pip install -e ".[dev]"
```

**(Opcional, recomendado para capturas)** — LibreOffice pelo `winget` (CMD **como Administrador**):

```bat
winget install --id TheDocumentFoundation.LibreOffice -e --source winget
```

Coloque **`soffice.exe`** no **PATH** (normalmente algo como  
`C:\Program Files\LibreOffice\program\`) ou o app pode não encontrar o conversor para PDF.

Rodar o app:

```bat
python -m calculadora_crefaz
```

**Gerar `.exe` localmente** (mesmo `pyinstaller.spec` do projeto):

```bat
pip install pyinstaller
pyinstaller pyinstaller.spec
```

O binário sai em **`dist\CalculadoraCrefaz.exe`**. Mais detalhes em [`README_DEV.md`](README_DEV.md).

---

### macOS / Linux (bash ou zsh)

```bash
git clone https://github.com/adventurelabsbrasil/revcalc.git
cd revcalc

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
```

**(macOS) LibreOffice:**

```bash
brew install --cask libreoffice
```

Rodar:

```bash
python -m calculadora_crefaz
```

---

### Sem Git: apenas ZIP da `main`

1. Baixe o ZIP: [`main.zip`](https://github.com/adventurelabsbrasil/revcalc/archive/refs/heads/main.zip) — extraia e entre na pasta `revcalc-main/`.
2. Execute os mesmos comandos **`venv`** + **`pip install -e ".[dev]"`** de cima dentro dessa pasta.

---

## Releases, `.exe` e kit Windows

A página [**Releases**](https://github.com/adventurelabsbrasil/revcalc/releases) pode trazer instaladores quando publicados. **Binário Windows pode não estar anexado** em toda versão — o caminho garantido até automatizarmos CI é **clone + venv acima**.

Alternativa já documentada para equipe Rose (script `instalar-e-testar`) está em **`cliente-kit/`** — ver [**`cliente-kit/README_USUARIO_FINAL.md`**](cliente-kit/README_USUARIO_FINAL.md).

---

## Como usar no dia a dia (após instalar)

1. Abrir o app (`python -m calculadora_crefaz` ou `.exe`).
2. **Entrar com Google** (primeira vez abre o navegador para autorização).
3. Digitar o **nome completo** da cliente **como aparece na pasta** no Drive (mínimo duas palavras).
4. **Calcular** — acompanhar o log na janela.
5. Conferir no Drive: **`10 …xlsx`**, **`12 Log.txt`**, **`13 Print …`** (quando LibreOffice disponível).

Estrutura típica de saída na pasta da cliente (`EMPRESTIMO DE ENERGIA/.../Nome/`):

```
├── 09 Contrato Crefaz.pdf
├── 10 Cálculo NOME.xlsx
├── 11 Series Temporais.pdf    (existente ou copiado pelo app)
├── 12 Log.txt
├── 13 Print CÁLCULO.pdf
├── 13 Print CÁLCULO.png
├── 13 Print 01 … 08 …        (capturas nomeadas pelo app)
└── …
```

---

## Mensagens comuns no log da UI

- **Sucesso:** `Pasta encontrada`, `Contrato lido`, `Pronto`.
- **Aviso:** BACEN copiado do repositório central; sobrescrever cálculo existente; capturas não geradas (LibreOffice ausente ou não detectado).

### Erros que interrompem o fluxo

| Sintoma rápido | O que conferir |
|----------------|----------------|
| Pasta não encontrada | Nome igual ao da pasta no Drive |
| Contrato não encontrado | Renomear para padrão com “Contrato Crefaz” no nome |
| BACEN não encontrado | Existência do PDF correspondente ao mês/ano esperado pela regra do app |
| Prazo não suportado | Template atual cobre até **24 parcelas** (Crefaz) |

Logout: botão **Sair** (limpa sessão local nesta máquina).

---

## Reportar problema

Envie nome da cliente, captura da janela com o log completo e data/hora. Evite editar manualmente o XLSX gerado para manter auditoria.

---

## Roadmap mencionado no produto

- **v0.7** — automatizar distribuição / build `.exe` em Releases (GitHub Actions)
- **v0.8** — pacote `.app` Mac mais polido
- **v0.9** — notificação pós-cálculo (ex.: Telegram), se política Rose permitir

---

© **2026** · **Adventure Labs** — Calculadora de Ação Crefaz · **v0.6.1**
