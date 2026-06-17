import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { AlertTriangle, CheckCircle2, ClipboardCheck, FileSearch, GitBranch, History, LockKeyhole, MessageSquare, ShieldCheck } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadOperatorStoredAudit } from "@/lib/audit/operator-audit-db";
import { loadCustomerReviewGovernance } from "@/lib/audit/customer-review-db";
import type { Finding } from "@/lib/findings/finding";
import { buildExplainabilityTraces, initializePhase14Governance } from "@/lib/governance/phase14-governance";
import type { ExplainabilityTrace, Phase14GovernanceState } from "@/lib/governance/types";
import type { StoredAudit } from "@/lib/audit/stored-audit";
import { overrideFindingAction, promoteOverrideAction, reviewFindingAction } from "./actions";

export default async function ReviewPage({
  params,
  searchParams
}: {
  params: Promise<{ auditId: string }>;
  searchParams: Promise<{ finding?: string }>;
}) {
  const { auditId } = await params;
  const query = await searchParams;
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}/review`)) {
    redirect(`/login/reviewer?auth=required&next=${encodeURIComponent(`/audits/${auditId}/review`)}`);
  }
  const audit = auditId === "demo" ? demoAsStored() : await loadOperatorStoredAudit(auditId, session);
  if (!audit) notFound();
  const governance = auditId === "demo" ? initializePhase14Governance(audit.auditId) : await loadCustomerReviewGovernance(auditId, session);
  if (!governance) notFound();
  const findings = reviewableFindings(audit.findings);
  const selectedFinding = findings.find((finding) => finding.findingId === query.finding) ?? findings[0];
  const traces = buildExplainabilityTraces(audit);
  const selectedTrace = selectedFinding ? traces.find((trace) => trace.findingId === selectedFinding.findingId) : undefined;
  const readOnly = audit.auditId === "demo";

  return (
    <AppShell>
      <div className="phase14-page">
        <nav className="audit-breadcrumb" aria-label="Breadcrumb">
          <Link href="/audits">Audits</Link>
          <span>/</span>
          <Link href={`/audits/${audit.auditId}`}>{audit.auditId}</Link>
          <span>/</span>
          <strong>Review</strong>
        </nav>

        <div className="audit-workspace-toolbar">
          <div>
            <h1>Reviewer operations</h1>
            <p>Inspect evidence, approve findings, pin versions, and preserve every reviewer decision.</p>
          </div>
          <span className={`badge ${readOnly ? "warn" : "ok"}`}>{readOnly ? "demo read-only" : "live audit"}</span>
        </div>

        <section className="audit-kpi-grid" aria-label="Reviewer governance summary">
          <Phase14Kpi icon={<ClipboardCheck />} label="Review queue" value={String(findings.length)} detail={`${pendingCount(findings)} pending`} />
          <Phase14Kpi icon={<History />} label="Action log" value={String(governance.reviewActionLog.length)} detail="Immutable append-only entries" />
          <Phase14Kpi icon={<LockKeyhole />} label="Overrides" value={String(governance.reviewerOverrides.length)} detail={`${excludedOverrideCount(governance)} excluded from automation`} />
          <Phase14Kpi icon={<ShieldCheck />} label="Pinned rules" value={`v${governance.packagePin.rulePackageVersion}`} detail={governance.packagePin.rulePackageId} />
        </section>

        <section className="phase14-grid">
          <div className="panel phase14-console">
            <div className="phase14-section-head">
              <div>
                <h2>Customer evidence review</h2>
                <p className="muted">Extracted facts, source cells, review questions, and proposed corrections.</p>
              </div>
              <span className="badge warn">{audit.readinessGate.blockers.length} blocker(s)</span>
            </div>

            <div className="phase14-fact-grid">
              {audit.dataset.events.slice(0, 6).map((event) => {
                const lineItems = audit.dataset.lineItems.filter((line) => line.eventId === event.eventId);
                const eventFindings = findings.filter((finding) => finding.eventId === event.eventId);
                return (
                  <article className="phase14-fact" key={event.eventId}>
                    <div>
                      <strong>{event.eventType}</strong>
                      <span>{event.eventId}</span>
                    </div>
                    <dl>
                      <dt>Date</dt>
                      <dd>{event.eventDatetime ?? "missing"}</dd>
                      <dt>Reference</dt>
                      <dd>{[event.referenceRecordType, event.referenceRecordNo].filter(Boolean).join(" / ") || "missing"}</dd>
                      <dt>Products</dt>
                      <dd>{lineItems.map((line) => line.productName).join(", ") || "not linked"}</dd>
                      <dt>Confidence</dt>
                      <dd>{eventFindings.length ? "review required" : "deterministic import"}</dd>
                    </dl>
                  </article>
                );
              })}
            </div>

            <div className="phase14-review-table" role="table" aria-label="Finding review workflow">
              <div className="phase14-review-row head" role="row">
                <span>Finding</span>
                <span>Evidence</span>
                <span>State</span>
                <span>Action</span>
              </div>
              {findings.map((finding) => (
                <div className={`phase14-review-row ${selectedFinding?.findingId === finding.findingId ? "selected" : ""}`} key={finding.findingId} role="row">
                  <Link href={`/audits/${audit.auditId}/review?finding=${encodeURIComponent(finding.findingId)}`}>
                    <strong>{finding.title}</strong>
                    <small>{finding.recommendation}</small>
                  </Link>
                  <span>
                    {finding.evidenceRefs.length ? evidenceLabel(finding) : "No source cell"}
                    <small>{finding.fieldOrKde ?? finding.findingType}</small>
                  </span>
                  <span>
                    <span className={`badge ${finding.reviewState === "approved" ? "ok" : "warn"}`}>{finding.reviewState.replaceAll("_", " ")}</span>
                  </span>
                  <form action={reviewFindingAction} className="phase14-inline-form">
                    <input name="auditId" type="hidden" value={audit.auditId} />
                    <input name="findingId" type="hidden" value={finding.findingId} />
                    <input name="reason" required placeholder="Reason" disabled={readOnly} />
                    <button name="action" value="approve" type="submit" disabled={readOnly}>
                      <CheckCircle2 size={15} />
                      Approve
                    </button>
                    <button name="action" value="request_more_evidence" type="submit" disabled={readOnly}>
                      <MessageSquare size={15} />
                      Ask
                    </button>
                  </form>
                </div>
              ))}
            </div>
          </div>

          <aside className="panel phase14-detail">
            {selectedFinding ? (
              <>
                <div className="phase14-section-head">
                  <div>
                    <h2>Finding trace</h2>
                    <p className="muted">{selectedFinding.findingId}</p>
                  </div>
                  <span className={`severity-badge ${selectedFinding.severity}`}>{selectedFinding.severity}</span>
                </div>

                <TraceList trace={selectedTrace} />

                <div className="phase14-subpanel">
                  <h3>
                    <GitBranch size={16} />
                    Package pin
                  </h3>
                  <dl className="phase14-pin-list">
                    <dt>Rule package</dt>
                    <dd>{governance.packagePin.rulePackageId} v{governance.packagePin.rulePackageVersion}</dd>
                    <dt>Scenario gate</dt>
                    <dd>{governance.packagePin.scenarioRegressionStatus}</dd>
                    <dt>Customer evidence</dt>
                    <dd>{governance.packagePin.customerEvidenceVersion}</dd>
                    <dt>Parser versions</dt>
                    <dd>{governance.packagePin.parserVersions.join(", ")}</dd>
                    <dt>Models</dt>
                    <dd>{governance.packagePin.modelVersions.join(", ")}</dd>
                  </dl>
                </div>

                <div className="phase14-subpanel">
                  <h3>
                    <AlertTriangle size={16} />
                    Reviewer override
                  </h3>
                  <form action={overrideFindingAction} className="phase14-override-form">
                    <input name="auditId" type="hidden" value={audit.auditId} />
                    <input name="findingId" type="hidden" value={selectedFinding.findingId} />
                    <textarea name="reason" required placeholder="Reason required for override" disabled={readOnly} />
                    <button type="submit" disabled={readOnly}>Create override</button>
                  </form>
                  <p className="muted">Overrides remain excluded from future automation unless promoted through approval.</p>
                </div>
              </>
            ) : (
              <div className="empty-finding-state">
                <CheckCircle2 size={32} />
                <strong>No review items</strong>
                <span>This audit has no open customer-facing findings.</span>
              </div>
            )}
          </aside>
        </section>

        <section className="phase14-bottom-grid">
          <div className="panel">
            <div className="phase14-section-head">
              <div>
                <h2>Reviewer action log</h2>
                <p className="muted">Append-only history of finding and exception decisions.</p>
              </div>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Reviewer</th>
                  <th>Action</th>
                  <th>Finding</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {governance.reviewActionLog.slice(-8).reverse().map((entry) => (
                  <tr key={entry.actionId}>
                    <td>{formatDateTime(entry.createdAt)}</td>
                    <td>{entry.reviewer}</td>
                    <td>{entry.action.replaceAll("_", " ")}</td>
                    <td>{entry.findingId ?? entry.exceptionId ?? "audit"}</td>
                    <td>{entry.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <div className="phase14-section-head">
              <div>
                <h2>Override controls</h2>
                <p className="muted">Overrides are audit-scoped and excluded from automation unless promoted.</p>
              </div>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Override</th>
                  <th>Status</th>
                  <th>Reason</th>
                  <th>Promote</th>
                </tr>
              </thead>
              <tbody>
                {governance.reviewerOverrides.length ? governance.reviewerOverrides.map((override) => (
                  <tr key={override.overrideId}>
                    <td>{override.findingId}</td>
                    <td>{override.status.replaceAll("_", " ")}</td>
                    <td>{override.reason}</td>
                    <td>
                      <form action={promoteOverrideAction} className="phase14-inline-form">
                        <input name="auditId" type="hidden" value={audit.auditId} />
                        <input name="overrideId" type="hidden" value={override.overrideId} />
                        <input name="reason" required placeholder="Approval reason" disabled={readOnly || override.status === "promoted_by_approval"} />
                        <button type="submit" disabled={readOnly || override.status === "promoted_by_approval"}>Promote</button>
                      </form>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={4}>No overrides recorded.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function Phase14Kpi({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string; detail: string }) {
  return (
    <div className="audit-kpi-card blue">
      <div className="audit-kpi-label">
        <span>{label}</span>
        {icon}
      </div>
      <div className="audit-kpi-main">
        <strong>{value}</strong>
      </div>
      <p>{detail}</p>
    </div>
  );
}

function TraceList({ trace }: { trace?: ExplainabilityTrace }) {
  if (!trace) {
    return <p className="muted">No trace available.</p>;
  }
  return (
    <ol className="phase14-trace-list">
      {trace.steps.map((step) => (
        <li key={step.step}>
          <FileSearch size={16} />
          <div>
            <strong>{step.label}</strong>
            <span>{step.detail}</span>
          </div>
        </li>
      ))}
    </ol>
  );
}

function reviewableFindings(findings: Finding[]) {
  return findings.filter((finding) => finding.status !== "pass" && finding.status !== "not_applicable");
}

function pendingCount(findings: Finding[]) {
  return findings.filter((finding) => finding.reviewState === "pending" || finding.reviewState === "needs_more_evidence").length;
}

function excludedOverrideCount(governance: Phase14GovernanceState) {
  return governance.reviewerOverrides.filter((override) => override.status === "excluded_from_automation").length;
}

function evidenceLabel(finding: Finding) {
  const ref = finding.evidenceRefs[0];
  if (!ref) return "No source cell";
  return `${ref.sheet ?? "Workbook"}${ref.row ? ` row ${ref.row}` : ""}${ref.field ? ` / ${ref.field}` : ""}`;
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
      events: [
        { eventId: "rec-1", eventType: "receiving", eventDatetime: "2026-06-10" },
        { eventId: "trans-1", eventType: "transformation", eventDatetime: "2026-06-11" },
        { eventId: "ship-1", eventType: "shipping", eventDatetime: "2026-06-12" }
      ],
      lineItems: [
        { eventLineId: "line-1", eventId: "rec-1", productId: "prod-1", productName: "Fresh Basil" },
        { eventLineId: "line-2", eventId: "trans-1", productId: "prod-1", productName: "Basil Pesto" },
        { eventLineId: "line-3", eventId: "ship-1", productId: "prod-1", productName: "Basil Pesto" }
      ],
      kdeValues: [],
      lineage: [],
      sourceDocuments: []
    },
    findings: audit.findings,
    readinessGate: audit.readinessGate,
    coverage: audit.coverage,
    mode: "draft",
    governance: initializePhase14Governance("demo")
  };
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}
