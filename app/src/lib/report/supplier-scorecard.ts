import type { StoredAudit } from "@/lib/audit/stored-audit";
import type { Finding } from "@/lib/findings/finding";

/**
 * P1 + P4 (frontend surfacing) — derive the supplier×product scope matrix and per-supplier
 * scorecards purely from data the operator UI already has (dataset events/line items +
 * findings). No backend persistence required; mirrors the Python engine's
 * build_supplier_product_coverage / build_supplier_scorecards so the two stay conceptually
 * aligned.
 */

export interface SupplierProductCoverageRow {
  supplierId: string;
  product: string;
  ftlStatus: "on" | "investigate" | "off";
  eventCount: number;
  gapCount: number;
  tlcGap: boolean;
  status: "covered" | "gap" | "out_of_scope";
}

export interface SupplierScorecardAction {
  fieldOrIssue: string;
  action: string;
}

export interface SupplierScorecardRow {
  supplierId: string;
  grade: "A" | "B" | "C" | "D" | "F";
  inScopeProducts: number;
  productsWithGaps: number;
  tlcGap: boolean;
  recommendedActions: SupplierScorecardAction[];
}

const GAP_STATUSES = new Set(["gap", "missing_evidence", "conflict", "cannot_determine"]);

function isGapFinding(finding: Finding): boolean {
  return GAP_STATUSES.has(finding.status) || finding.severity === "high" || finding.severity === "critical";
}

function isTlcFinding(finding: Finding): boolean {
  const key = `${finding.fieldOrKde ?? ""} ${finding.findingType}`.toLowerCase();
  return key.includes("tlc") || key.includes("lot") || key.includes("lineage");
}

function ftlStatusFor(isFtlMaybe: boolean | "unknown" | undefined): "on" | "investigate" | "off" {
  if (isFtlMaybe === false) return "off";
  if (isFtlMaybe === true) return "investigate"; // "maybe" => needs confirmation
  return "investigate";
}

export function buildSupplierProductCoverage(audit: StoredAudit): SupplierProductCoverageRow[] {
  const { events, lineItems, products } = audit.dataset;
  const supplierByEvent = new Map<string, string>();
  for (const event of events) {
    supplierByEvent.set(event.eventId, event.fromPartnerId || event.toPartnerId || "unknown_supplier");
  }
  const ftlByProductId = new Map<string, boolean | "unknown">();
  for (const product of products) {
    ftlByProductId.set(product.productId, product.isFtlMaybe);
  }

  // Findings grouped by event so a cell inherits its event's findings.
  const findingsByEvent = new Map<string, Finding[]>();
  for (const finding of audit.findings) {
    if (!finding.eventId) continue;
    const list = findingsByEvent.get(finding.eventId) ?? [];
    list.push(finding);
    findingsByEvent.set(finding.eventId, list);
  }

  const cells = new Map<string, SupplierProductCoverageRow & { _events: Set<string> }>();
  for (const line of lineItems) {
    const supplierId = supplierByEvent.get(line.eventId) ?? "unknown_supplier";
    const product = line.productName || line.productId || "unknown_product";
    const key = `${supplierId}::${product}`;
    const ftlStatus = ftlStatusFor(ftlByProductId.get(line.productId));
    const cell =
      cells.get(key) ??
      {
        supplierId,
        product,
        ftlStatus,
        eventCount: 0,
        gapCount: 0,
        tlcGap: false,
        status: "covered" as const,
        _events: new Set<string>()
      };
    if (!cell._events.has(line.eventId)) {
      cell._events.add(line.eventId);
      cell.eventCount += 1;
      for (const finding of findingsByEvent.get(line.eventId) ?? []) {
        if (isGapFinding(finding)) {
          cell.gapCount += 1;
          if (isTlcFinding(finding)) cell.tlcGap = true;
        }
      }
    }
    cells.set(key, cell);
  }

  const rows: SupplierProductCoverageRow[] = [];
  for (const cell of cells.values()) {
    const status: SupplierProductCoverageRow["status"] =
      cell.ftlStatus === "off" ? "out_of_scope" : cell.gapCount > 0 || cell.tlcGap ? "gap" : "covered";
    rows.push({
      supplierId: cell.supplierId,
      product: cell.product,
      ftlStatus: cell.ftlStatus,
      eventCount: cell.eventCount,
      gapCount: cell.gapCount,
      tlcGap: cell.tlcGap,
      status
    });
  }
  rows.sort((a, b) =>
    Number(a.status !== "gap") - Number(b.status !== "gap") ||
    Number(!a.tlcGap) - Number(!b.tlcGap) ||
    b.gapCount - a.gapCount ||
    a.supplierId.localeCompare(b.supplierId)
  );
  return rows;
}

function gradeFor(inScope: number, withGaps: number, tlcGap: boolean): SupplierScorecardRow["grade"] {
  if (inScope === 0) return "A";
  const ratio = withGaps / inScope;
  if (ratio >= 0.5) return "F";
  if (ratio >= 0.3) return "D";
  if (ratio >= 0.15) return "C";
  if (ratio > 0) return "B";
  return tlcGap ? "B" : "A";
}

export function buildSupplierScorecards(audit: StoredAudit): SupplierScorecardRow[] {
  const coverage = buildSupplierProductCoverage(audit);
  const bySupplier = new Map<string, { inScope: number; gaps: number; tlcGap: boolean }>();
  for (const row of coverage) {
    const bucket = bySupplier.get(row.supplierId) ?? { inScope: 0, gaps: 0, tlcGap: false };
    if (row.ftlStatus !== "off") {
      bucket.inScope += 1;
      if (row.status === "gap") bucket.gaps += 1;
    }
    if (row.tlcGap) bucket.tlcGap = true;
    bySupplier.set(row.supplierId, bucket);
  }

  const cards: SupplierScorecardRow[] = [];
  for (const [supplierId, bucket] of bySupplier) {
    const actions: SupplierScorecardAction[] = [];
    if (bucket.tlcGap) {
      actions.push({ fieldOrIssue: "tlc_lineage", action: "Link each shipped lot to its source/transformation lot (21 CFR 1.1350)." });
    }
    if (bucket.gaps > 0) {
      actions.push({ fieldOrIssue: "kde_gaps", action: "Provide the missing required KDEs on every covered record (21 CFR 1.1340/1.1345)." });
    }
    cards.push({
      supplierId,
      grade: gradeFor(bucket.inScope, bucket.gaps, bucket.tlcGap),
      inScopeProducts: bucket.inScope,
      productsWithGaps: bucket.gaps,
      tlcGap: bucket.tlcGap,
      recommendedActions: actions
    });
  }
  const rank: Record<string, number> = { F: 0, D: 1, C: 2, B: 3, A: 4 };
  cards.sort((a, b) => rank[a.grade] - rank[b.grade] || b.productsWithGaps - a.productsWithGaps || a.supplierId.localeCompare(b.supplierId));
  return cards;
}

export function coverageToRows(rows: SupplierProductCoverageRow[]) {
  return rows.map((r) => ({
    supplier_id: r.supplierId,
    product: r.product,
    ftl_status: r.ftlStatus,
    event_count: String(r.eventCount),
    gap_count: String(r.gapCount),
    tlc_gap: r.tlcGap ? "yes" : "no",
    status: r.status
  }));
}

export function scorecardsToRows(cards: SupplierScorecardRow[]) {
  return cards.map((c) => ({
    supplier_id: c.supplierId,
    grade: c.grade,
    in_scope_products: String(c.inScopeProducts),
    products_with_gaps: String(c.productsWithGaps),
    tlc_gap: c.tlcGap ? "yes" : "no",
    recommended_actions: c.recommendedActions.map((a) => a.action).join(" | ")
  }));
}
