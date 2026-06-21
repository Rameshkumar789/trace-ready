import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { Card } from "./Card";
import { StatusPill } from "./StatusPill";

export function ReadinessVerdict({
  ready,
  fileName,
  mustFixCount,
  reviewCount,
  findingsCount,
  recordsChecked,
}: {
  ready: boolean;
  fileName: string;
  mustFixCount: number;
  reviewCount: number;
  findingsCount: number;
  recordsChecked?: number;
}) {
  const headline = mustFixCount
    ? `${mustFixCount} must-fix gap${mustFixCount === 1 ? "" : "s"}${
        reviewCount ? `, ${reviewCount} to review` : ""
      }`
    : reviewCount
      ? `${reviewCount} item${reviewCount === 1 ? "" : "s"} to review`
      : "No issues found";
  const summary = mustFixCount
    ? "Your traceability records are mostly complete. Fix the missing lot codes first — those are what a recall depends on. The rest just need a quick human confirmation."
    : reviewCount
      ? "No hard gaps. A few records need a human to confirm scope before Bellwether will score them."
      : "Every checked record carries the key data FSMA 204 expects.";

  const metrics: Array<{ label: string; value: number; tone: "risk" | "review" | "neutral" }> = [
    { label: "Must fix", value: mustFixCount, tone: "risk" },
    { label: "To review", value: reviewCount, tone: "review" },
    { label: "Findings", value: findingsCount, tone: "neutral" },
  ];
  if (recordsChecked) {
    metrics.push({ label: "Records checked", value: recordsChecked, tone: "neutral" });
  }

  return (
    <Card padding="lg" as="section">
      <div className="flex flex-wrap justify-between gap-3">
        <div className="max-w-[46ch]">
          <StatusPill
            tone={ready ? "ok" : "review"}
            icon={ready ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
          >
            {ready ? "Ready" : "Action needed"}
          </StatusPill>
          <h1 className="mt-2.5 mb-1 text-2xl font-bold text-ink">{headline}</h1>
          <p className="text-sm leading-relaxed text-muted">{summary}</p>
        </div>
        <div className="text-right">
          <p className="text-[13px] text-muted">FSMA 204 readiness review</p>
          <p className="mt-0.5 text-[13px] text-ink">{fileName}</p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-[repeat(auto-fit,minmax(120px,1fr))] gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-pill bg-surface px-4 py-3">
            <p className="text-[13px] text-muted">{m.label}</p>
            <p
              className={`mt-0.5 text-2xl font-bold ${
                m.tone === "risk" ? "text-risk" : m.tone === "review" ? "text-review" : "text-ink"
              }`}
            >
              {m.value}
            </p>
          </div>
        ))}
      </div>

      <p className="mt-4 flex items-center gap-1.5 text-xs text-muted">
        <Info size={14} /> Readiness review, not a legal certification. Findings come from approved
        FSMA 204 rules run against your workbook.
      </p>
    </Card>
  );
}
