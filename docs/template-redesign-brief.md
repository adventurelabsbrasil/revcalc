# Brief — Refactor completo do template `Calculo.xlsx`

> **Status:** planejamento aberto, retomar amanhã (2026-04-29)
> **Pedido original:** "refazer a planilha do jeito correto, profissional" — Rodrigo, 2026-04-28
> **Substitui:** `template-modifications-v0.5.1.md` (que era patch dos bugs do template atual)

## Contexto

A v0.5.0 entregou MVP funcional, mas o template original `Calculo.xlsx` herdou problemas estruturais do XLSX da cliente Jaqueline da Silva Brum (quem foi o "molde"):

- Datas hardcoded da Jaqueline contaminavam outros clientes
- PRICE 24X com 15 linhas estáticas (não cobre 16-24 parcelas)
- PRICE 36x/48x/60x com coluna Vencimento totalmente vazia
- Format de data US (`mm-dd-yy`) em vez de BR
- PRICE 48x em portrait (todas as outras paisagem)
- Strings mal-digitadas (`'30/102024'` em PRICE 60x)
- Sem identidade visual definida
- 4 abas redundantes (PRICE 24X/36x/48x/60x) com conteúdo quase idêntico

Decisão: refazer do zero com critério, ao invés de patchar.

## Decisões estratégicas pendentes

### D1. Estrutura de abas

- [ ] **(A)** Manter 4 abas (24X/36x/48x/60x) — código apaga as outras 3
- [ ] **(B)** 1 aba única, dinâmica até 60 parcelas — recomendado pelo Cowork

### D2. Compatibilidade com `planilha.py`

- [ ] **(A)** Manter mapeamento de células atual (I7, I9, ..., AP15, BL8) — só refactor visual
- [ ] **(B)** Refactor coordenado: novo template + novo `planilha.py` — recomendado pelo Cowork
  - Implica que isso vira **v0.6** (não v0.5.1)

### D3. Identidade visual — insumos necessários

- [ ] Paleta de cores Rose Portal Advocacia (hex codes)
- [ ] Paleta Adventure Labs (hex codes)
- [ ] Logo Rose (PNG/SVG alta resolução)
- [ ] Logo Adventure Labs (PNG/SVG)
- [ ] Fonte preferida (Calibri default? Outra?)
- [ ] Exemplo de comunicação visual de referência (caso queira algo específico)

### D4. Conteúdo jurídico das seções

Manter as 6 seções atuais (estrutura jurídica que a Roselaine usa pra montar a petição)?

- DADOS DO CONTRATO (input)
- VALORES RECALCULADOS (com expurgo de abusividades)
- SALDO RECALCULADO DESCONTANDO PARCELAS PAGAS
- CONFORME PACTUADO (PRICE original)
- PARCELA COM TAXA MÉDIA E EXPURGO DE ABUSIVIDADES (PRICE corrigido)
- 3 TABELAS DE PARCELAS (Conforme contrato / Recalculadas / Valores pagos)

- [ ] Sim, manter exatamente
- [ ] Repensar — Roselaine valida antes

### D5. Validação final

- [ ] Roselaine valida o template novo antes de virar produção (recomendado)
- [ ] Founder valida sozinho

## Achados técnicos consolidados (do audit anterior)

Vide `template-modifications-v0.5.1.md` — diagnóstico técnico completo. Especialmente:

- Linhas 5 (PRICE 24X) e 6 (outras) estão LIVRES — pode adicionar células sem mover nada (irrelevante se for refactor 1 aba)
- Nenhuma fórmula de cabeçalho referencia a tabela de parcelas — `IF(..., "")` é seguro
- Coluna AE/BF replicam D via fórmula `=D[N]` — automático
- `EDATE(data, n)` é a função correta pra somar meses calendário

## Estimativa de tempo

Assumindo refactor coordenado (D1=B + D2=B):

| Fase | Estimativa |
|------|-----------|
| Audit + design (paleta, layout, hierarquia visual) | 1-2h |
| Construção do template via openpyxl | 3-4h |
| Atualização do `planilha.py` | 1h |
| Atualização dos testes | 1h |
| Smoke E2E (Adriano, Marlí, caso 30+ parcelas hipotético) | 1h |
| Iteração com feedback do Founder e Roselaine | 1-2h |
| **Total** | **8-11h** |

Cabe em 1 dia focado se as 4 decisões estiverem tomadas no início.

## Workflow proposto

1. **Cowork** constrói via openpyxl (controle total sobre cada célula, formatação, fórmula)
2. **Cowork** entrega XLSX em `templates/Calculo-v2.xlsx` (mantém o original como `Calculo-v1-backup.xlsx`)
3. **Founder** abre no LibreOffice/Numbers pra avaliar visual (não edita)
4. **Cowork** ajusta com base em feedback até OK do Founder
5. **Roselaine** valida cálculos jurídicos no Excel real
6. **CLI sessão v0.6** atualiza `planilha.py` + testes + smokes
7. **Bruna** valida o XLSX final no ASUS dela
8. Commit + tag v0.6

## Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| openpyxl não renderiza formatação condicional 100% como Excel | Testar visualmente em LibreOffice + Excel real antes de fechar |
| Roselaine demanda mudanças que quebram lógica do código | Validação dela ANTES de mexer no `planilha.py` |
| Refactor exposto a regressão dos cálculos PRICE | Comparar célula a célula contra v0.5.0 com Adriano/Marlí — qualquer divergência é flag |
| Sem logo / paleta da Rose, fica genérico | Usar paleta neutra corporativa (azul-marinho + cinza + branco) e adicionar logo depois |

## Pendências fora deste escopo

- Branding Adventure Labs detalhado (rodapé Tkinter, log.txt, .exe metadata)
- GH Actions Win-only (v0.7+)
- Capturas xlwings (v0.8+)
- Telegram outbound (v0.9+)
