# RevCalc v0.9.14 — instalação local no Windows

Este kit instala o RevCalc localmente. O processamento não depende do `revcalc-api`, do Xeon ou da Vercel. O Google Drive continua sendo usado para ler contratos e gravar resultados.

## Instalar

1. Instale Python 3.11+ e marque **Add python.exe to PATH**.
2. Abra PowerShell nesta pasta.
3. Execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-RevCalc.ps1
```

4. Preencha o `.env` criado em `%LOCALAPPDATA%\AdventureLabs\RevCalc\0.9.14` com as credenciais Google fornecidas pela Adventure.
5. Execute `Executar-RevCalc.ps1` na pasta instalada.

## Atualizar

Quando uma nova tag `vX.Y.Z` for publicada, execute `Atualizar-RevCalc.ps1`. Ele consulta o mirror, pede confirmação, preserva o `.env` e atualiza o código e as dependências.

LibreOffice é opcional; sem ele o cálculo/XLSX funciona, mas capturas PDF/PNG podem não ser geradas.

Nenhum segredo, token ou dado de cliente deve ser colocado neste repositório.
