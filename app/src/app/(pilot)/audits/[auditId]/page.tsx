import type React from "react";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ClipboardList,
  ExternalLink,
  FileSearch,
  HelpCircle,
  Info,
  Wrench
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadObligationExplanations, loadOperatorStoredAudit, type ObligationExplanation } from "@/lib/audit/operator-audit-db";
import { loadAuditProcessingStatus } from "@/lib/audit/audit-processing-status";
import { AuditProcessing } from "./AuditProcessing";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import type { Finding } from "@/lib/findings/finding";
import type { StoredAudit } from "@/lib/audit/stored-audit";

const SHEET_LABELS: Record<string, string> = {
  "00_business_profile": "00_Business_Profile",
  "01_product_master": "01_Product_Master",
  "02_location_master": "02_Location_Master",
  "03_partner_master": "03_Partner_Master",
  "04_traceability_plan": "04_Traceability_Plan",
  "05_cte_events": "05_CTE_Events",
  "06_event_line_items": "06_Event_Line_Items",
  "07_kde_values": "07_KDE_Values",
  "08_tlc_lineage": "08_TLC_Lineage",
  "09_source_documents": "09_Source_Documents",
  "10_exemptions_claims": "10_Exemptions_Claims"
};

const CTE_LABELS: Record<string, string> = {
  receiving: "Receiving record",
  shipping: "Shipping record",
  transformation: "Transformation record",
  first_land_based_receiving: "First land-based receiving",
  initial_packing: "Initial packing record",
  harvesting: "Harvest record",
  cooling: "Cooling record",
  traceability_plan: "Traceability plan"
};

export default async function AuditWorkspacePage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}`)) {
    redirect(`/login/operator?auth=required&next=${encodeURIComponent(`/audits/${auditId}`)}`);
  }
  // Real audits run synchronously on upload (no cron/queue worker). While that is still in
  // flight we show a spinner that polls until findings are ready — instead of a separate
  // processing/status page.
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
  const explanations = await loadObligationExplanations(findings.map((f) => f.approvedObligationId ?? "")).catch(() => ({}));
  const mustFix = findings.filter((f) => f.severity === "high" || f.severity === "critical");
  const toReview = findings.filter((f) => f.severity !== "high" && f.severity !== "critical");
  const recordsChecked = audit.dataset.events.length || undefined;

  return (
    <AppShell>
      <div className="audit-workspace-page" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <nav style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--muted)" }} aria-label="Breadcrumb">
          <Link href="/audits" style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "var(--muted)", textDecoration: "none" }}>
            <ChevronLeft size={15} /> Audits
          </Link>
          <span>/</span>
          <span>{audit.fileName}</span>
        </nav>

        <VerdictHeader audit={audit} findings={findings} mustFixCount={mustFix.length} reviewCount={toReview.length} recordsChecked={recordsChecked} />

        {mustFix.length ? (
          <section>
            <SectionHeading icon={<AlertTriangle size={18} />} tone="danger" title="Must fix first" count={mustFix.length} />
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {mustFix.map((finding) => (
                <FindingCard key={finding.findingId} finding={finding} explanation={lookup(explanations, finding)} detailed />
              ))}
            </div>
          </section>
        ) : null}

        {toReview.length ? (
          <section>
            <SectionHeading icon={<HelpCircle size={18} />} tone="warn" title="Review & confirm" count={toReview.length} hint="TraceReady won't guess a pass/fail" />
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {toReview.map((finding) => (
                <FindingCard key={finding.findingId} finding={finding} explanation={lookup(explanations, finding)} />
              ))}
            </div>
          </section>
        ) : null}

        {!findings.length ? (
          <div style={card()}>
            <strong>No open findings.</strong>
            <p style={{ color: "var(--muted)", margin: "6px 0 0" }}>This audit has no exceptions to resolve.</p>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}

function VerdictHeader({
  audit,
  findings,
  mustFixCount,
  reviewCount,
  recordsChecked
}: {
  audit: StoredAudit;
  findings: Finding[];
  mustFixCount: number;
  reviewCount: number;
  recordsChecked?: number;
}) {
  const ready = audit.readinessGate.passed;
  const headline = mustFixCount
    ? `${mustFixCount} must-fix gap${mustFixCount === 1 ? "" : "s"}${reviewCount ? `, ${reviewCount} to review` : ""}`
    : reviewCount
      ? `${reviewCount} item${reviewCount === 1 ? "" : "s"} to review`
      : "No issues found";
  const summary = mustFixCount
    ? "Your traceability records are mostly complete. Fix the missing lot codes first — those are what a recall depends on. The rest just need a quick human confirmation."
    : reviewCount
      ? "No hard gaps. A few records need a human to confirm scope before TraceReady will score them."
      : "Every checked record carries the key data FSMA 204 expects.";

  return (
    <section style={card(true)}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div style={{ maxWidth: "46ch" }}>
          <span style={pill(ready ? "ok" : "warn")}>
            {ready ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
            {ready ? "Ready" : "Action needed"}
          </span>
          <h1 style={{ margin: "10px 0 4px", fontSize: 24 }}>{headline}</h1>
          <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>{summary}</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>FSMA 204 readiness review</p>
          <p style={{ margin: "2px 0 0", fontSize: 13, color: "var(--ink)" }}>{audit.fileName}</p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12, marginTop: "1.1rem" }}>
        <Metric label="Must fix" value={mustFixCount} tone="danger" />
        <Metric label="To review" value={reviewCount} tone="warn" />
        <Metric label="Findings" value={findings.length} />
        {recordsChecked ? <Metric label="Records checked" value={recordsChecked} /> : null}
      </div>

      <p style={{ margin: "0.9rem 0 0", fontSize: 12, color: "var(--muted)", display: "flex", alignItems: "center", gap: 6 }}>
        <Info size={14} /> Readiness review, not a legal certification. Findings come from approved FSMA 204 rules run against your workbook.
      </p>
    </section>
  );
}

function FindingCard({ finding, explanation, detailed = false }: { finding: Finding; explanation?: ObligationExplanation; detailed?: boolean }) {
  const tone = finding.severity === "high" || finding.severity === "critical" ? "danger" : "warn";
  const recordLabel = CTE_LABELS[finding.fieldOrKde ?? ""] ?? null;
  const evidence = evidenceCell(finding);

  return (
    <article style={{ ...card(), borderLeft: `3px solid var(--${tone === "danger" ? "coral" : "gold"})`, borderRadius: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <span style={iconBadge(tone)} aria-hidden>
            {tone === "danger" ? <AlertTriangle size={17} /> : <HelpCircle size={17} />}
          </span>
          <div>
            <h3 style={{ margin: "0 0 7px", fontSize: 16, lineHeight: 1.4 }}>{finding.title}</h3>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {recordLabel ? (
                <span style={chip()}>
                  {finding.fieldOrKde === "shipping" ? <ArrowUpRight size={13} /> : finding.fieldOrKde === "receiving" ? <ArrowDownLeft size={13} /> : null}
                  {recordLabel}
                </span>
              ) : null}
              {finding.eventId ? <span style={chip()}>{finding.eventId}</span> : null}
            </div>
          </div>
        </div>
        <span style={pill(tone === "danger" ? "danger" : "warn")}>{tone === "danger" ? "High" : "Review"}</span>
      </div>

      <div style={{ display: "grid", gap: 12, marginTop: 14 }}>
        {explanation?.whyItMatters ? (
          <LabeledBlock icon={<HelpCircle size={15} />} label="Why it matters">
            {explanation.whyItMatters}
          </LabeledBlock>
        ) : null}

        {evidence ? (
          <div>
            <BlockLabel icon={<FileSearch size={15} />}>What we found in your workbook</BlockLabel>
            <div style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", fontSize: 13, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8, padding: "9px 12px" }}>
              {evidence}
            </div>
          </div>
        ) : null}

        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {explanation ? (
            <div style={{ flex: 1, minWidth: 220 }}>
              <BlockLabel icon={<BookOpen size={15} />}>The FSMA rule</BlockLabel>
              <RuleCitation explanation={explanation} />
            </div>
          ) : null}
          {finding.recommendation ? (
            <div style={{ flex: 1, minWidth: 220 }}>
              <BlockLabel icon={<Wrench size={15} />}>How to fix</BlockLabel>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55 }}>{finding.recommendation}</p>
            </div>
          ) : null}
        </div>

        {detailed && explanation?.supportText ? (
          <details>
            <summary style={{ cursor: "pointer", fontSize: 13, color: "var(--muted)", display: "flex", alignItems: "center", gap: 6 }}>
              <ClipboardList size={14} /> Read the exact rule text
            </summary>
            <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--ink)", lineHeight: 1.65, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8, padding: "10px 12px" }}>
              {explanation.supportText}
            </p>
          </details>
        ) : null}
      </div>
    </article>
  );
}

function RuleCitation({ explanation }: { explanation: ObligationExplanation }) {
  const inner = (
    <div style={{ border: "1px solid var(--line)", borderRadius: 8, padding: "9px 12px" }}>
      <span style={{ fontSize: 13, fontWeight: 500, color: "var(--accent)", display: "inline-flex", alignItems: "center", gap: 4 }}>
        {explanation.sectionRef ?? "FSMA 204"}
        {explanation.sourceUrl ? <ExternalLink size={13} /> : null}
      </span>
      <p style={{ margin: "3px 0 0", fontSize: 13, color: "var(--muted)", lineHeight: 1.5 }}>{explanation.plainRequirement}</p>
    </div>
  );
  if (explanation.sourceUrl) {
    return (
      <a href={explanation.sourceUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
        {inner}
      </a>
    );
  }
  return inner;
}

function LabeledBlock({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div>
      <BlockLabel icon={icon}>{label}</BlockLabel>
      <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{children}</p>
    </div>
  );
}

function BlockLabel({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <p style={{ margin: "0 0 4px", fontSize: 13, color: "var(--muted)", display: "flex", alignItems: "center", gap: 6 }}>
      {icon}
      {children}
    </p>
  );
}

function SectionHeading({ icon, tone, title, count, hint }: { icon: React.ReactNode; tone: "danger" | "warn"; title: string; count: number; hint?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 0 0.75rem" }}>
      <span style={{ color: `var(--${tone === "danger" ? "danger" : "warn"})`, display: "inline-flex" }}>{icon}</span>
      <h2 style={{ margin: 0, fontSize: 18 }}>{title}</h2>
      <span style={{ fontSize: 13, color: "var(--muted)" }}>
        {count} item{count === 1 ? "" : "s"}
        {hint ? ` — ${hint}` : ""}
      </span>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone?: "danger" | "warn" }) {
  const color = tone === "danger" ? "var(--danger)" : tone === "warn" ? "var(--warn)" : "var(--ink)";
  return (
    <div style={{ background: "var(--surface)", borderRadius: 8, padding: "0.85rem 1rem" }}>
      <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>{label}</p>
      <p style={{ margin: "2px 0 0", fontSize: 24, fontWeight: 600, color }}>{value}</p>
    </div>
  );
}

function card(strong = false): React.CSSProperties {
  return {
    background: "var(--panel)",
    border: "1px solid var(--line)",
    borderRadius: 12,
    padding: strong ? "1.25rem" : "1.1rem 1.25rem"
  };
}

function pill(tone: "ok" | "warn" | "danger"): React.CSSProperties {
  const map = {
    ok: { bg: "var(--surface-strong)", fg: "var(--ok)" },
    warn: { bg: "var(--gold-soft)", fg: "var(--warn)" },
    danger: { bg: "var(--coral-soft)", fg: "var(--danger)" }
  } as const;
  const c = map[tone];
  return { display: "inline-flex", alignItems: "center", gap: 6, background: c.bg, color: c.fg, fontSize: 12, padding: "4px 10px", borderRadius: 8, whiteSpace: "nowrap" };
}

function chip(): React.CSSProperties {
  return { display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, background: "var(--surface)", color: "var(--muted)", padding: "3px 9px", borderRadius: 8 };
}

function iconBadge(tone: "danger" | "warn"): React.CSSProperties {
  const c = tone === "danger" ? { bg: "var(--coral-soft)", fg: "var(--danger)" } : { bg: "var(--gold-soft)", fg: "var(--warn)" };
  return {
    flexShrink: 0,
    width: 34,
    height: 34,
    borderRadius: 9,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    background: c.bg,
    color: c.fg
  };
}

function lookup(explanations: Record<string, ObligationExplanation>, finding: Finding): ObligationExplanation | undefined {
  return finding.approvedObligationId ? explanations[finding.approvedObligationId] : undefined;
}

function evidenceCell(finding: Finding): string | undefined {
  const ref = finding.evidenceRefs.find((r) => r.evidenceId)?.evidenceId;
  if (!ref) return undefined;
  const match = /-(\d{2}_[a-z0-9_]+)-r(\d+)-c\d+/i.exec(ref);
  if (!match) return undefined;
  const sheet = SHEET_LABELS[match[1].toLowerCase()] ?? match[1];
  return `${sheet} · row ${match[2]}`;
}

function sortFindings(findings: Finding[]) {
  const rank: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  return [...findings].sort((a, b) => (rank[a.severity] ?? 9) - (rank[b.severity] ?? 9) || a.title.localeCompare(b.title));
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
      sourceDocuments: []
    },
    findings: audit.findings,
    readinessGate: audit.readinessGate,
    coverage: audit.coverage,
    mode: "draft"
  };
}
