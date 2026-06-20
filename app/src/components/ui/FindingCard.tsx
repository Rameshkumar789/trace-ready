import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  BookOpen,
  ClipboardList,
  ExternalLink,
  FileSearch,
  HelpCircle,
  Wrench,
} from "lucide-react";
import type { ReactNode } from "react";
import type { Finding } from "@/lib/findings/finding";
import type { ObligationExplanation } from "@/lib/audit/operator-audit-db";
import { Card } from "./Card";
import { Chip } from "./Chip";
import { StatusPill } from "./StatusPill";
import { CTE_LABELS, evidenceCell, severityTone } from "./finding-format";

function BlockLabel({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <p className="mb-1 flex items-center gap-1.5 text-[13px] text-muted">
      {icon}
      {children}
    </p>
  );
}

export function FindingCard({
  finding,
  explanation,
  detailed = false,
}: {
  finding: Finding;
  explanation?: ObligationExplanation;
  detailed?: boolean;
}) {
  const tone = severityTone(finding.severity);
  const recordLabel = CTE_LABELS[finding.fieldOrKde ?? ""] ?? null;
  const evidence = evidenceCell(finding);

  return (
    <Card accent={tone} as="article">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span
            className={`grid h-9 w-9 shrink-0 place-items-center rounded-card ${
              tone === "risk" ? "bg-risk-soft text-risk" : "bg-review-soft text-review"
            }`}
            aria-hidden
          >
            {tone === "risk" ? <AlertTriangle size={17} /> : <HelpCircle size={17} />}
          </span>
          <div>
            <h3 className="text-base font-semibold leading-snug text-ink">{finding.title}</h3>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {recordLabel ? (
                <Chip
                  icon={
                    finding.fieldOrKde === "shipping" ? (
                      <ArrowUpRight size={13} />
                    ) : finding.fieldOrKde === "receiving" ? (
                      <ArrowDownLeft size={13} />
                    ) : null
                  }
                >
                  {recordLabel}
                </Chip>
              ) : null}
              {finding.eventId ? <Chip>{finding.eventId}</Chip> : null}
            </div>
          </div>
        </div>
        <StatusPill tone={tone}>{tone === "risk" ? "High" : "Review"}</StatusPill>
      </div>

      <div className="mt-3.5 grid gap-3">
        {explanation?.whyItMatters ? (
          <div>
            <BlockLabel icon={<HelpCircle size={15} />}>Why it matters</BlockLabel>
            <p className="text-sm leading-relaxed text-ink">{explanation.whyItMatters}</p>
          </div>
        ) : null}

        {evidence ? (
          <div>
            <BlockLabel icon={<FileSearch size={15} />}>What we found in your workbook</BlockLabel>
            <div className="rounded-pill border border-line bg-surface px-3 py-2 font-mono text-[13px] text-ink">
              {evidence}
            </div>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-4">
          {explanation ? (
            <div className="min-w-[220px] flex-1">
              <BlockLabel icon={<BookOpen size={15} />}>The FSMA rule</BlockLabel>
              <RuleCitation explanation={explanation} />
            </div>
          ) : null}
          {finding.recommendation ? (
            <div className="min-w-[220px] flex-1">
              <BlockLabel icon={<Wrench size={15} />}>How to fix</BlockLabel>
              <p className="text-sm leading-relaxed text-ink">{finding.recommendation}</p>
            </div>
          ) : null}
        </div>

        {detailed && explanation?.supportText ? (
          <details>
            <summary className="flex cursor-pointer items-center gap-1.5 text-[13px] text-muted">
              <ClipboardList size={14} /> Read the exact rule text
            </summary>
            <p className="mt-2 rounded-pill border border-line bg-surface px-3 py-2.5 text-[13px] leading-relaxed text-ink">
              {explanation.supportText}
            </p>
          </details>
        ) : null}
      </div>
    </Card>
  );
}

function RuleCitation({ explanation }: { explanation: ObligationExplanation }) {
  const inner = (
    <div className="rounded-pill border border-line px-3 py-2">
      <span className="inline-flex items-center gap-1 text-[13px] font-medium text-accent">
        {explanation.sectionRef ?? "FSMA 204"}
        {explanation.sourceUrl ? <ExternalLink size={13} /> : null}
      </span>
      <p className="mt-0.5 text-[13px] leading-normal text-muted">{explanation.plainRequirement}</p>
    </div>
  );
  if (explanation.sourceUrl) {
    return (
      <a href={explanation.sourceUrl} target="_blank" rel="noreferrer" className="no-underline">
        {inner}
      </a>
    );
  }
  return inner;
}
