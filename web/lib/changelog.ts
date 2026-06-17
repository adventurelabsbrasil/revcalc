// Changelog visível ao usuário no app (painel "Novidades").
// Cada correção/feature que o usuário percebe entra aqui — mais recente primeiro.
// Mantém em sincronia com src/calculadora_crefaz/__init__.py (__version__).

export interface ChangelogEntry {
  version: string;
  date: string; // dd/mm/yyyy
  items: string[];
}

export const CHANGELOG: ChangelogEntry[] = [
  {
    version: "0.9.7",
    date: "17/06/2026",
    items: [
      "As tabelas de parcelas (conforme o contrato, recalculadas e valores pagos) agora mostram exatamente o número de parcelas do contrato — sem linhas em branco sobrando. Vale para contratos ativos e quitados.",
    ],
  },
];

export const LATEST_VERSION: string = CHANGELOG[0]?.version ?? "";
