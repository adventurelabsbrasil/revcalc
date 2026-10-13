# RevCalc v0.9.15 — instalação local no Windows

Estas instruções correspondem à versão proposta v0.9.15. O instalador por download
só poderá ser usado depois da publicação da tag correspondente e do provisionamento
do perfil OAuth Desktop. A release v0.9.14 não contém estas correções.

O kit deve chegar pronto da Adventure: scripts PowerShell e
`revcalc-desktop.json` com a configuração da operação. A pessoa que usa o
aplicativo não precisa editar `.env` nem fornecer Client Secret.

## Instalar e entrar

1. Abra o PowerShell na pasta do kit.
2. Execute:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-RevCalc.ps1
```

3. Execute o lançador em:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\AdventureLabs\RevCalc\Executar-RevCalc.ps1"
```

4. Clique em **Entrar com Google**, escolha a conta autorizada e conceda as
   permissões do Drive. Volte ao aplicativo para verificar o resultado do acesso.

O instalador prepara Python 3.11 e as dependências. Para instalar também LibreOffice:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-RevCalc.ps1 -InstallLibreOffice
```

O cálculo/XLSX funciona sem LibreOffice; capturas PDF/PNG precisam dele.
O processamento ocorre no Windows e acessa o Google diretamente, sem precisar
do backend RevCalc, Xeon ou Vercel. Internet e Google Drive continuam necessários.

Para testar antes da publicação, a Adventure pode fornecer um ZIP local e usar
`-ArchivePath "C:\caminho\RevCalc-v0.9.15-proposta.zip" -ProfilePath "C:\caminho\revcalc-desktop.json"`.
O ZIP deve conter a pasta `revcalc-0.9.15`; o perfil OAuth precisa estar provisionado.

## Reinstalar, migrar e atualizar

Reexecutar o instalador preserva configuração e credenciais. Instalações antigas
sob pastas de versão são detectadas; seu `.env` é preservado e migrado, sem ser
copiado para TEMP. Para uma instalação antiga em outro local, o administrador
pode usar `-ExistingRoot "C:\caminho\RevCalc"`.

A configuração persistente fica em
`%LOCALAPPDATA%\AdventureLabs\RevCalc\config`; os tokens continuam exclusivamente
no Windows Credential Manager via keyring. Um perfil já existente não é sobrescrito.
Cada instalação usa uma nova pasta em `versions`, mantendo a anterior.

Execute `cliente-kit\Atualizar-RevCalc.ps1` da instalação ativa para procurar uma
nova tag estável. A atualização pede confirmação e só ativa a versão candidata
depois das verificações. Se falhar, use o lançador normalmente: a versão anterior
continua ativa. Arquivos personalizados permanecem na pasta antiga.

## Problemas de acesso

- Perfil ausente/inválido: peça à Adventure o kit configurado. Não coloque segredo
  da aplicação web na máquina.
- Conta não autorizada: use a conta indicada pela administração da operação.
- Permissão no Drive: peça acesso às pastas necessárias; login não concede acesso
  automaticamente.
- Consentimento negado ou tempo esgotado: clique em Entrar com Google novamente.
- Credential Manager indisponível: restaure o serviço de credenciais do Windows;
  o aplicativo não grava tokens em arquivos.
- Troca do Client ID: pode exigir um novo login. Reinstalar por si só não exige
  apagar tokens.

Configuração Google Cloud, migração técnica e testes:
[Desktop OAuth](../docs/DESKTOP_OAUTH.md).
