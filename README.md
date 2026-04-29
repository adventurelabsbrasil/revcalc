# Calculadora de Ação Crefaz

> Ferramenta interna da **Rose Portal Advocacia** que automatiza o cálculo de ações de revisão de contratos Crefaz. Você digita o nome da cliente, o app encontra a pasta no Drive, lê o contrato em PDF, busca a taxa BACEN do mês certo e gera a planilha de cálculo + capturas direto na pasta — pronta pra revisão.

> **Versão atual:** v0.6.0 (2026-04-29). Documentação técnica em [`README_DEV.md`](README_DEV.md).
> Entrega para usuário final (funcionário da Rose): [`cliente-kit/README_USUARIO_FINAL.md`](cliente-kit/README_USUARIO_FINAL.md).

---

## Como funciona

```mermaid
flowchart LR
    A([Você digita o nome<br/>da cliente]) --> B{Login Google}
    B -->|primeira vez| C[Abre o navegador<br/>pra autorizar]
    B -->|já logado| D
    C --> D[App procura a pasta<br/>da cliente no Drive]
    D --> E[Lê o PDF do<br/>09 Contrato Crefaz]
    E --> F[Lê a taxa BACEN<br/>do mês de emissão]
    F --> G[Calcula parcelas pagas<br/>e excesso da taxa]
    G --> H[Gera 10 Cálculo.xlsx<br/>+ 8 prints PNG + 1 PDF]
    H --> I[Atualiza 12 Log.txt<br/>com histórico append]
    I --> J([Roselaine revisa<br/>direto no Drive])
```

**Tempo médio:** 30 a 60 segundos por cálculo (depende da rede e do tamanho do contrato).

---

## Antes de começar

### O que você precisa

- **Conta de email da Rose** (`@roseportaladvocacia.com.br`) — login via Google
- **Pasta da cliente já preparada no Drive**, dentro de `EMPRESTIMO DE ENERGIA/<estado>/<NOME DA CLIENTE>/`, contendo:
  - `09 Contrato Crefaz.pdf` (ou variação reconhecida)
  - *(opcional)* `11 Series Temporais.pdf` — se não estiver, o app busca automaticamente no repositório central da Rose e copia pra cá
- **Internet ativa**

### Se for a primeira vez

Bruna Scopel envia o instalador (`CalculadoraCrefaz.exe` no Windows ou `CalculadoraCrefaz.app` no Mac). Salvar na Área de Trabalho ou pasta de aplicativos.

---

## Como usar — passo a passo

### 1. Abrir o app

Clique duas vezes em `CalculadoraCrefaz` na sua Área de Trabalho.

### 2. Entrar com Google

Na primeira execução: clique em **"Entrar com Google"**. Vai abrir o navegador pra você autorizar com seu email da Rose. Depois disso, fica salvo no seu computador.

> O app **só aceita** emails dos domínios `@roseportaladvocacia.com.br` e `@adventurelabs.com.br`.

### 3. Digitar o nome da cliente

Use o **nome completo**, exatamente como está na pasta do Drive (mínimo duas palavras). Exemplos:

- ✅ `IVAN DOS SANTOS`
- ✅ `Adriano Silva`
- ❌ `Ivan` (faltou sobrenome)
- ❌ `cliente teste` (não existe no Drive)

Se você digitar errado, o app sugere nomes parecidos.

### 4. Apertar "Calcular" (ou Enter)

A janela mostra cada passo em tempo real:

```
[14:32:01] Buscando pasta da cliente no Drive...
[14:32:02] Pasta encontrada: EMPRESTIMO DE ENERGIA/10. RIO GRANDE DO SUL/IVAN DOS SANTOS
[14:32:02] Localizando contrato Crefaz...
[14:32:03] Contrato encontrado: 09 Contrato Crefaz.pdf
[14:32:04] Contrato lido: cédula 3700123, prazo 24, taxa 18.99%
[14:32:04] Parcelas pagas até hoje: 8 | aba: CÁLCULO
[14:32:05] BACEN já na pasta da cliente: 11 Series Temporais.pdf
[14:32:06] Taxa BACEN para 08/2025: 5.32%
[14:32:07] Gerando planilha preenchida...
[14:32:08] Subindo 10 Cálculo IVAN DOS SANTOS.xlsx...
[14:32:10] Gerando capturas (PDF + 1 PNG)...
[14:32:13] Capturas regionais (6 blocos)...
[14:32:18] Capturas concluídas: 11 arquivos.
[14:32:20] ✓ Pronto.
```

### 5. Conferir no Drive

Clique em **"Abrir pasta no Drive"**. Você vai encontrar:

```
EMPRESTIMO DE ENERGIA/<estado>/<NOME DA CLIENTE>/
├── 09 Contrato Crefaz.pdf       (você subiu)
├── 10 Cálculo NOME.xlsx          (gerado pelo app — abre como Sheets)
├── 11 Series Temporais.pdf       (você subiu ou app copiou)
├── 12 Log.txt                     (histórico — modo append)
├── 13 Print CÁLCULO.pdf           (PDF unificado da planilha)
├── 13 Print CÁLCULO.png           (página inteira em PNG)
├── 13 Print 01 Dados do Contrato.png
├── 13 Print 02 Valores Recalculados.png
├── 13 Print 03 Saldo Recalculado.png
├── 13 Print 04 Conforme Pactuado.png
├── 13 Print 05 Parcela Taxa Media.png
├── 13 Print 06 Percentual + Indevidas.png
├── 13 Print 07 Item II do Contrato.png   (do PDF do contrato)
└── 13 Print 08 Series BACEN.png          (do PDF BACEN)
```

> Roselaine pode abrir o XLSX como **Sheets** (preview no Drive) ou baixar e abrir no **Excel** local. Ambos mostram a planilha com cálculo automático. Os PNGs servem como print-prontos pra arquivar/peticionar.

---

## Mensagens que você pode encontrar

### ✓ Verde (tudo certo)
- `Pasta encontrada` / `Contrato lido` / `Pronto`

### ⚠️ Amarelo (atenção, mas seguiu)
- `BACEN não estava na pasta da cliente. O sistema baixou do repositório central e gravou aqui automaticamente.` — recomendação: incluir o PDF manualmente da próxima vez (fonte oficial)
- `Cálculo já existe (modificado em ...). Deseja sobrescrever?` — pop-up de confirmação. Sim sobrescreve, não cancela
- `Capturas não geradas: ...` — XLSX e log seguem normais, mas os PNGs/PDF não foram gerados (provavelmente LibreOffice não está instalado no Mac/Win local)

### ✗ Vermelho (erro, parou)

| Mensagem | O que significa | O que fazer |
|----------|----------------|-------------|
| **Pasta não encontrada** | Nome digitado não bate nenhuma pasta no Drive | Conferir grafia exata. App sugere nomes parecidos |
| **Pasta ambígua** | Mesmo nome em mais de um estado | Refazer com nome mais específico |
| **Contrato não encontrado** | Nenhum PDF na pasta casa "Contrato Crefaz" | Renomear o arquivo pra `09 Contrato Crefaz.pdf` antes de tentar |
| **Vários contratos** | Mais de um candidato a contrato | App escolhe o mais provável; se não for o certo, renomear os outros pra outro padrão |
| **Erro ao ler contrato** | PDF está corrompido ou Item II faltando | Conferir se o PDF abre normalmente |
| **BACEN não encontrado** | Mês/ano da emissão não tem PDF disponível em lugar nenhum | Falar com a equipe da Rose pra subir o PDF do BACEN do mês |
| **Prazo não suportado** | Contrato com mais de 24 parcelas (Crefaz só opera até 24) | Abrir issue se for caso real |

---

## Logout

Botão **"Sair"** no canto superior direito. Limpa seu login do computador (necessário só se você for trocar de conta ou emprestar a máquina).

---

## Quando reportar problema

Se aparecer **"Erro inesperado"** ou se um cálculo der número estranho, mande pra Bruna Scopel ou Rodrigo Ribas:

1. **Nome da cliente** que estava sendo processada
2. **Print da janela do app** com o log completo
3. **Data e hora** que aconteceu

Não tente "corrigir manualmente" o XLSX — manter o gerado pelo app permite auditoria depois.

---

## Versão atual: v0.6.0

Mudanças desde v0.5.0:
- Template em duas camadas (DADOS oculta + CÁLCULO única)
- Aba única CÁLCULO (Crefaz só opera contratos até 24 parcelas)
- 8 capturas automáticas: PDF unificado + 1 PNG geral + 6 PNGs regionais (cada bloco do XLSX) + 2 PNGs dos PDFs (Item II do contrato + Séries BACEN)
- Log em modo append (cada execução adiciona um novo bloco no `12 Log.txt`)
- Aviso destacado quando BACEN é copiado do repositório central

Roadmap próximo:
- **v0.7** — distribuição automática (não precisa pedir pra Bruna empacotar a cada release)
- **v0.8** — versão Mac empacotada (`.app` arrastável)
- **v0.9** — notificação Telegram após cada cálculo

---

*Desenvolvido pela [Adventure Labs](https://adventurelabs.com.br) para a Rose Portal Advocacia. Suporte técnico: Rodrigo Ribas.*
