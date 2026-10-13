# OAuth do RevCalc para Windows

## Estado validado

Em 13/10/2026, o login do RevCalc v0.9.14 foi validado no Windows da usuária.

- Projeto Google Cloud: `adventurelabs-revcalc-prod`
- Nome do projeto: `Adventure Labs - RevCalc`
- Cliente OAuth: `RevCalc Windows`
- Tipo: aplicativo para computador (Desktop)
- Público: interno, restrito ao Workspace da Adventure
- Conta de suporte: `contato@adventurelabs.com.br`
- Armazenamento local do token: Credential Manager do Windows, via `keyring`

## O que não deve ser versionado

Nunca versionar ou publicar:

- arquivo JSON baixado do Google Cloud;
- `GOOGLE_OAUTH_CLIENT_SECRET`;
- tokens de acesso ou refresh tokens;
- `.env` preenchido;
- capturas de tela que contenham credenciais.

O `.env.example` deve conter apenas nomes de variáveis e instruções, sem valores reais.

## Configuração da estação Windows

O instalador cria o `.env` na instalação local. Preencher as variáveis OAuth usando o client Desktop do projeto acima, por canal seguro:

```env
GOOGLE_OAUTH_CLIENT_ID=<client id do RevCalc Windows>
GOOGLE_OAUTH_CLIENT_SECRET=<client secret do RevCalc Windows>
```

Depois, executar:

```powershell
Set-Location "$env:LOCALAPPDATA\AdventureLabs\RevCalc\0.9.14"
powershell -ExecutionPolicy Bypass -File .\Executar-RevCalc.ps1
```

No primeiro uso, o navegador abre o login Google. O token é persistido no Credential Manager; não é necessário salvar `token.json` no projeto.

## Validação realizada

- Python 3.11.9 encontrado.
- LibreOffice encontrado.
- Ambiente virtual criado e dependências instaladas.
- Inicializador Windows corrigido para UTF-8.
- `.env` presente na instalação local.
- Login Google concluído com a conta da usuária.
- RevCalc em uso sem dependência operacional do Xeon ou da VPS.

## Manutenção

Se o cliente OAuth precisar ser substituído:

1. Criar um novo cliente Desktop no projeto `adventurelabs-revcalc-prod`.
2. Distribuir o JSON/valores somente por canal seguro.
3. Atualizar o `.env` local da estação.
4. Validar o login e a execução do RevCalc.
5. Revogar/excluir o cliente antigo somente depois da validação.

Em caso de comprometimento, excluir ou revogar imediatamente o cliente afetado e criar outro. Nunca registrar o secret em issues, PRs, README ou logs.
