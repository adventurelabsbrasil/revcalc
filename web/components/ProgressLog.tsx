"use client";

export interface LogLine {
  level: "info" | "aviso" | "ok" | "erro";
  message: string;
}

const COR: Record<LogLine["level"], string> = {
  info: "#e6e6e6",
  aviso: "#ffd43b",
  ok: "#51cf66",
  erro: "#ff6b6b",
};

// Reproduz o painel de log escuro do app desktop (ui.py: bg #1a1a1a, fonte mono).
export default function ProgressLog({ lines }: { lines: LogLine[] }) {
  if (lines.length === 0) return null;
  return (
    <pre className="log">
      {lines.map((l, i) => (
        <div key={i} style={{ color: COR[l.level] }}>
          {l.level === "ok" ? "✓ " : l.level === "erro" ? "✗ " : "› "}
          {l.message}
        </div>
      ))}
    </pre>
  );
}
