"use client";

import { useEffect, useRef, useState } from "react";
import { CHANGELOG, LATEST_VERSION } from "@/lib/changelog";

// Marca a última versão cujas novidades o usuário já viu (some o badge).
const STORAGE_KEY = "revcalc:novidades:lastSeen";

export default function Novidades() {
  const [open, setOpen] = useState(false);
  const [hasNew, setHasNew] = useState(false);
  const [mounted, setMounted] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  // localStorage só no cliente (evita mismatch de hidratação).
  useEffect(() => {
    setMounted(true);
    try {
      const seen = localStorage.getItem(STORAGE_KEY);
      setHasNew(!!LATEST_VERSION && seen !== LATEST_VERSION);
    } catch {
      /* localStorage indisponível — segue sem badge */
    }
  }, []);

  // Fecha o painel ao clicar fora.
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next && hasNew) {
      try {
        localStorage.setItem(STORAGE_KEY, LATEST_VERSION);
      } catch {
        /* ignora */
      }
      setHasNew(false);
    }
  }

  if (!CHANGELOG.length) return null;

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        onClick={toggle}
        aria-label="Novidades"
        aria-expanded={open}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: 0,
          position: "relative",
          color: "var(--accent)",
          font: "inherit",
        }}
      >
        🔔 Novidades
        {mounted && hasNew && (
          <span
            aria-hidden
            style={{
              position: "absolute",
              top: -3,
              right: -7,
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--erro)",
            }}
          />
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Novidades"
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + 8px)",
            zIndex: 50,
            width: 340,
            maxWidth: "82vw",
            maxHeight: 380,
            overflowY: "auto",
            background: "var(--panel)",
            color: "var(--fg)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
            padding: 14,
            textAlign: "left",
          }}
        >
          <strong style={{ display: "block", marginBottom: 10 }}>Novidades</strong>
          {CHANGELOG.map((rel) => (
            <div key={rel.version} style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>
                v{rel.version} · {rel.date}
              </div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {rel.items.map((it, i) => (
                  <li key={i} style={{ marginBottom: 6, lineHeight: 1.4 }}>
                    {it}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
