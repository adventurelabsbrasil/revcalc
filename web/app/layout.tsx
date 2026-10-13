import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RevCalc — Calculadora de Revisão de Contratos",
  description: "Gera cálculos revisionais e salva os resultados no Drive.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
