"use client";

import { useMemo, useState } from "react";
import { Siren } from "lucide-react";
import { Card, SectionHeader } from "@/components/ui";
import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import { runTracebackFireDrill, type FireDrillResult } from "@/lib/report/fire-drill";

export function FireDrillPanel({ dataset }: { dataset: NormalizedAuditDataset }) {
  const [lot, setLot] = useState("");
  const [result, setResult] = useState<FireDrillResult | null>(null);

  // Suggest a few lot codes from the data so the user can try it in one click.
  const sampleLots = useMemo(() => {
    const seen = new Set<string>();
    for (const line of dataset.lineItems) {
      const value = (line.lotOrTlc ?? "").trim();
      if (value) seen.add(value);
      if (seen.size >= 6) break;
    }
    return [...seen];
  }, [dataset.lineItems]);

  function run(value: string) {
    const trimmed = value.trim();
    setLot(trimmed);
    setResult(trimmed ? runTracebackFireDrill(dataset, trimmed) : null);
  }

  const tone = !result ? "" : result.passed ? "#117A57" : result.completenessScore >= 0.5 ? "#B7791F" : "#B42318";

  return (
    <section className="flex flex-col gap-3">
      <SectionHeader
        icon={<Siren size={18} />}
        title="24-hour traceback fire-drill"
        hint="Pick a lot — can you produce a complete one-up/one-down record?"
      />
      <Card padding="lg">
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={lot}
            onChange={(e) => setLot(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && run(lot)}
            placeholder="Enter a lot / TLC code"
            className="rounded-pill border border-line bg-surface px-3 py-2 font-mono text-sm text-ink"
          />
          <button
            type="button"
            onClick={() => run(lot)}
            className="rounded-pill bg-accent px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
          >
            Run fire-drill
          </button>
        </div>

        {sampleLots.length ? (
          <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-muted">
            <span>try:</span>
            {sampleLots.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => run(s)}
                className="rounded border border-line px-2 py-0.5 font-mono hover:border-accent hover:text-accent"
              >
                {s}
              </button>
            ))}
          </div>
        ) : null}

        {result ? (
          <div className="mt-4 border-t border-line pt-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl font-extrabold" style={{ color: tone }}>
                {Math.round(result.completenessScore * 100)}%
              </span>
              <div className="flex flex-col">
                <span className="font-semibold" style={{ color: tone }}>
                  {result.passed ? "Recallable — complete chain" : "Not fully recallable"}
                </span>
                <span className="text-xs text-muted">
                  lot {result.targetLot} · {result.eventCount} event(s) · one-up {result.oneUpLinked ? "✓" : "✗"} · one-down {result.oneDownLinked ? "✓" : "✗"}
                </span>
              </div>
            </div>
            {result.missingLinks.length ? (
              <ul className="mt-2 flex flex-col gap-1 text-sm text-muted">
                {result.missingLinks.map((m) => (
                  <li key={m}>• {m}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </Card>
    </section>
  );
}
