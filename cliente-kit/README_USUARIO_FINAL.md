# Calculadora Crefaz - Guia de Instalacao e Teste (Usuario Final Rose)

Este guia e para o funcionario da Rose que vai instalar e usar a Calculadora Crefaz.

## 0) Onde baixar

- Repositorio: [https://github.com/adventurelabsbrasil/revcalc](https://github.com/adventurelabsbrasil/revcalc)
- ZIP do projeto: [https://github.com/adventurelabsbrasil/revcalc/archive/refs/heads/main.zip](https://github.com/adventurelabsbrasil/revcalc/archive/refs/heads/main.zip)
- Releases (instaladores quando publicados): [https://github.com/adventurelabsbrasil/revcalc/releases](https://github.com/adventurelabsbrasil/revcalc/releases)

Se a pagina de Releases ainda estiver vazia, baixe o ZIP (`main.zip`) e use os arquivos do kit.

## 1) Arquivos que voce deve receber

- `CalculadoraCrefaz.exe` (Windows)
- `CalculadoraCrefaz.app` (macOS)
- `windows/instalar-e-testar.cmd`
- `macos/instalar-e-testar.command`

## 2) Requisitos

- Internet ativa
- Conta Google da Rose (`@roseportaladvocacia.com.br`) ou conta autorizada (`@adventurelabs.com.br`)
- Pasta da cliente no Drive com `09 Contrato Crefaz.pdf`
- LibreOffice instalado (necessario para gerar os arquivos de print PDF/PNG)

## 3) Windows - instalacao

### Instalacao automatica

1. Clique com botao direito em `windows/instalar-e-testar.cmd`
2. Execute como administrador
3. Aguarde instalar o LibreOffice e abrir o app

### Instalacao manual

No CMD (administrador):

```bat
winget install --id TheDocumentFoundation.LibreOffice -e --source winget
```

Depois abra `CalculadoraCrefaz.exe`.

## 4) macOS - instalacao

### Instalacao automatica

1. Dê duplo clique em `macos/instalar-e-testar.command`
2. Aguarde instalar o LibreOffice e abrir o app

### Instalacao manual

No Terminal:

```bash
brew install --cask libreoffice
```

Depois abra `CalculadoraCrefaz.app`.
Na primeira vez: botao direito -> Abrir -> Abrir mesmo assim.

## 5) Como testar apos instalar

1. Abra a Calculadora Crefaz
2. Clique em "Entrar com Google"
3. Digite o nome completo da cliente
4. Clique em "Calcular"
5. Confira no Drive da cliente:
   - `10 Calculo NOME.xlsx`
   - `12 Log.txt`
   - `13 Print ...` (PDF e PNGs)

## 6) Problemas comuns

- "Pasta nao encontrada": nome da cliente digitado diferente do Drive
- "Contrato nao encontrado": arquivo precisa estar como `09 Contrato Crefaz.pdf`
- "Capturas nao geradas": LibreOffice nao instalado/detectado

## 7) Suporte

Se der erro, envie para o suporte:

- nome da cliente
- print da tela com o log
- data e hora do ocorrido
