# RevCalc — Calculadora de Revisão de Contratos

**Versão do código:** `v0.9.15` (publicação da release e perfil Desktop pendentes).

O RevCalc lê contratos em PDF no Google Drive, aplica a série BACEN do período correto e gera a planilha de revisão e seus artefatos de conferência. O nome RevCalc significa **Calculadora de Revisão de Contratos**.

## Como escolher o modo de uso

| Necessidade | Caminho recomendado |
| --- | --- |
| Uso normal | Aplicação web: [revcalc.adventurelabs.com.br](https://revcalc.adventurelabs.com.br) |
| Contingência sem depender do servidor | [Kit local para Windows](cliente-kit/README_WINDOWS_LOCAL.md) |
| Desenvolvimento ou diagnóstico | Clone do repositório + ambiente virtual, conforme abaixo |

O modo local processa os cálculos na máquina do usuário. Ele não depende do Xeon, da Vercel ou do backend remoto. O Google Drive continua sendo usado para ler contratos e gravar resultados.

## Aplicação web

- Frontend: [revcalc.adventurelabs.com.br](https://revcalc.adventurelabs.com.br)
- API: `https://revcalc-api.adventurelabs.com.br`
- Login: Google OAuth
- Processamento: engine Python no backend remoto

O backend remoto é a infraestrutura da aplicação web. Se ele estiver indisponível, use o kit local do Windows para manter a operação.

### Fluxo web

1. Entre com Google.
2. Informe o nome completo da pasta no Drive, exatamente como aparece lá.
3. Adicione mais nomes se quiser processar uma fila de pastas.
4. Execute o cálculo e acompanhe o status.
5. Confira os arquivos gerados na pasta correspondente.

## Instalação local no Windows

O caminho recomendado para contingência é o instalador PowerShell. Ele instala Python 3.11 quando necessário, cria o ambiente virtual e instala as dependências.

1. Abra o [kit Windows](cliente-kit/README_WINDOWS_LOCAL.md).
2. Receba da Adventure o kit configurado com os scripts e `revcalc-desktop.json`.
3. Abra o PowerShell nessa pasta.
4. Execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-RevCalc.ps1 -InstallLibreOffice
```

5. Inicie o programa e clique em **Entrar com Google**; não é necessário editar `.env`:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\AdventureLabs\RevCalc\Executar-RevCalc.ps1"
```

O LibreOffice é opcional para o cálculo, mas recomendado para gerar capturas PDF/PNG.

O procedimento completo está em [`cliente-kit/README_WINDOWS_LOCAL.md`](cliente-kit/README_WINDOWS_LOCAL.md).
O instalador por download exige a tag v0.9.15 publicada; a release anterior não
contém o novo fluxo. Provisionamento e critérios de liberação:
[`docs/DESKTOP_OAUTH.md`](docs/DESKTOP_OAUTH.md).

## Resultados gerados

Na pasta do contrato, o RevCalc pode gerar:

- `Calculo.xlsx` — planilha-fonte do cálculo ativo;
- `Calculo quitado.xlsx` — planilha do fluxo quitado;
- PDFs do cálculo e da série BACEN;
- `imag.01.png` — recorte do bloco principal do contrato;
- `imag.02.png` — recorte do bloco de parcelas;
- log da execução.

O cálculo existente não é sobrescrito automaticamente. Para refazer, remova o arquivo de cálculo correspondente no Drive e execute novamente.

O sistema também pode processar contratos quitados em subpastas diretas e vários nomes em uma única fila.

## Regras de entrada

- O contrato deve estar em PDF e ter “contrato” no nome do arquivo.
- Documentos auxiliares, procurações, cálculos e cópias são ignorados.
- A numeração inicial do contrato, quando presente, é usada para ordenar os arquivos derivados.
- A série BACEN é escolhida pelo mês e ano do primeiro vencimento.

## Desenvolvimento local

Pré-requisitos:

- Git;
- Python 3.11 ou superior;
- LibreOffice, se for necessário gerar PDF/PNG.

```bash
git clone https://github.com/adventurelabsbrasil/revcalc.git
cd revcalc
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
```

No Windows, use `.venv\Scripts\activate` no lugar de `source .venv/bin/activate`.

Para executar o engine de desenvolvimento:

```bash
python -m calculadora_crefaz
```

Para executar os testes:

```bash
pytest
```

Para gerar o executável localmente:

```bash
pip install pyinstaller
pyinstaller pyinstaller.spec
```

Detalhes de desenvolvimento e estrutura estão em [`README_DEV.md`](README_DEV.md).

## Configuração e segurança

- Não coloque tokens, credenciais Google, chaves Supabase ou dados de clientes no repositório.
- Use `.env` apenas localmente; o arquivo está no `.gitignore`.
- O feedback da aplicação, quando habilitado, é enviado ao backend e não abre issue pública automaticamente.
- Antes de publicar alterações, execute o `privacy-scan` do CI e revise o diff.

## Links

- [Kit Windows](cliente-kit/README_WINDOWS_LOCAL.md)
- [Documentação de desenvolvimento](README_DEV.md)
- [Releases](https://github.com/adventurelabsbrasil/revcalc/releases)
- [Issues](https://github.com/adventurelabsbrasil/revcalc/issues)

© 2026 Adventure Labs — RevCalc v0.9.15
