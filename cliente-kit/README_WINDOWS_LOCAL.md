# RevCalc v0.9.14 — instalação local no Windows

Este kit instala o RevCalc localmente. O processamento não depende do `revcalc-api`, do Xeon ou da Vercel. O Google Drive continua sendo usado para ler contratos e gravar resultados.

## Instalar

1. Abra PowerShell nesta pasta. O instalador tenta instalar Python 3.11 automaticamente via `winget` se ele não estiver disponível.
2. Execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-RevCalc.ps1
```

3. Preencha o `.env` criado em `%LOCALAPPDATA%\AdventureLabs\RevCalc\0.9.14` com as credenciais Google fornecidas pela Adventure.
4. Execute `Executar-RevCalc.ps1` na pasta instalada.

O instalador cria um ambiente virtual e instala automaticamente todas as dependências Python do projeto. Para instalar também o LibreOffice e habilitar as capturas PDF/PNG:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-RevCalc.ps1 -InstallLibreOffice
```

## Atualizar

Quando uma nova tag `vX.Y.Z` for publicada, execute `cliente-kit\Atualizar-RevCalc.ps1` a partir da instalação local. Ele consulta o mirror, pede confirmação, preserva o `.env` e atualiza o código e as dependências.

LibreOffice é opcional; sem ele o cálculo/XLSX funciona, mas capturas PDF/PNG podem não ser geradas.

Nenhum segredo, token ou dado de cliente deve ser colocado neste repositório.
