import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { AlertTriangle, ChevronLeft, HelpCircle } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import {
  loadObligationExplanations,
  loadOperatorStoredAudit,
  type ObligationExplanation,
} from "@/lib/audit/operator-audit-db";
import { loadAuditProcessingStatus } from "@/lib/audit/audit-processing-status";
import { AuditProcessing } from "./AuditProcessing";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import type { Finding } from "@/lib/findings/finding";
import type { StoredAudit } from "@/lib/audit/stored-audit";
import {
  Card,
  FindingCard,
  ReadinessVerdict,
  SectionHeader,
  SeverityCteMatrix,
  sortFindings,
} from "@/components/ui";

export default async function AuditWorkspacePage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}`)) {
    redirect(`/login/operator?auth=required&next=${encodeURIComponent(`/audits/${auditId}`)}`);
  }
  // Real audits run synchronously on upload (no cron/queue worker). While that is still in
  // flight we show a spinner that polls until findings are ready.
  if (auditId !== "demo") {
    const status = await loadAuditProcessingStatus(auditId, session).catch(() => undefined);
    if (!status) notFound();
    const ready = status.projectStatus === "succeeded" || status.run?.status === "succeeded";
    if (!ready) {
      return (
        <AppShell>
          <AuditProcessing auditId={auditId} fileName={status.fileName} />
        </AppShell>
      );
    }
  }

  const audit = auditId === "demo" ? demoAsStored() : await loadOperatorStoredAudit(auditId, session);
  if (!audit) notFound();

  const findings = sortFindings(audit.findings);
  const explanations = await loadObligationExplanations(
    findings.map((f) => f.approvedObligationId ?? ""),
  ).catch(() => ({}) as Record<string, ObligationExplanation>);
  const mustFix = findings.filter((f) => f.severity === "high" || f.severity === "critical");
  const toReview = findings.filter((f) => f.severity !== "high" && f.severity !== "critical");
  const recordsChecked = audit.dataset.events.length || undefined;

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <nav className="flex items-center gap-1.5 text-[13px] text-muted" aria-label="Breadcrumb">
          <Link href="/audits" className="inline-flex items-center gap-1 text-muted no-underline hover:text-ink">
            <ChevronLeft size={15} /> Audits
          </Link>
          <span>/</span>
          <span className="text-ink">{audit.fileName}</span>
        </nav>

        <ReadinessVerdict
          ready={audit.readinessGate.passed}
          fileName={audit.fileName}
          mustFixCount={mustFix.length}
          reviewCount={toReview.length}
          findingsCount={findings.length}
          recordsChecked={recordsChecked}
        />

        {findings.length ? <SeverityCteMatrix findings={findings} /> : null}

        {mustFix.length ? (
          <section className="flex flex-col gap-3">
            <SectionHeader
              icon={<AlertTriangle size={18} />}
              tone="risk"
              title="Must fix first"
              count={mustFix.length}
              hint="These are what a recall depends on"
            />
            {mustFix.map((finding) => (
              <FindingCard
                key={finding.findingId}
                finding={finding}
                explanation={lookup(explanations, finding)}
                detailed
              />
            ))}
          </section>
        ) : null}

        {toReview.length ? (
          <section className="flex flex-col gap-3">
            <SectionHeader
              icon={<HelpCircle size={18} />}
              tone="review"
              title="Review & confirm"
              count={toReview.length}
              hint="TraceReady won't guess a pass/fail"
            />
            {toReview.map((finding) => (
              <FindingCard
                key={finding.findingId}
                finding={finding}
                explanation={lookup(explanations, finding)}
              />
            ))}
          </section>
        ) : null}

        {!findings.length ? (
          <Card padding="lg">
            <strong className="text-ink">No open findings.</strong>
            <p className="mt-1.5 text-sm text-muted">This audit has no exceptions to resolve.</p>
          </Card>
        ) : null}
      </div>
    </AppShell>
  );
}

function lookup(
  explanations: Record<string, ObligationExplanation>,
  finding: Finding,
): ObligationExplanation | undefined {
  return finding.approvedObligationId ? explanations[finding.approvedObligationId] : undefined;
}

function demoAsStored(): StoredAudit {
  const audit = runDemoAudit();
  return {
    auditId: "demo",
    createdAt: "2026-06-14T00:00:00.000Z",
    fileName: "Sample multi-CTE workbook",
    parseErrors: [],
    dataset: {
      businessProfiles: [],
      exemptionClaims: [],
      products: [],
      productScopeDecisions: [],
      traceabilityPlans: [],
      events: [],
      lineItems: [],
      kdeValues: [],
      lineage: [],
      sourceDocuments: [],
    },
    findings: audit.findings,
    readinessGate: audit.readinessGate,
    coverage: audit.coverage,
    mode: "draft",
  };
}
