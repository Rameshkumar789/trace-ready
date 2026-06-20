import type { Finding } from "@/lib/findings/finding";
import type { FindingSeverity } from "@/lib/ontology/types";
import type { Tone } from "./tone";

export const SHEET_LABELS: Record<string, string> = {
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
  "10_exemptions_claims": "10_Exemptions_Claims",
};

export const CTE_LABELS: Record<string, string> = {
  receiving: "Receiving record",
  shipping: "Shipping record",
  transformation: "Transformation record",
  first_land_based_receiving: "First land-based receiving",
  initial_packing: "Initial packing record",
  harvesting: "Harvest record",
  cooling: "Cooling record",
  traceability_plan: "Traceability plan",
};

/** Short column labels for the severity × CTE matrix. */
export const CTE_SHORT: Record<string, string> = {
  receiving: "Receiving",
  shipping: "Shipping",
  transformation: "Transform",
  first_land_based_receiving: "First recv",
  initial_packing: "Packing",
  harvesting: "Harvest",
  cooling: "Cooling",
  traceability_plan: "Plan",
};

export function severityTone(severity: FindingSeverity): Tone {
  return severity === "high" || severity === "critical" ? "risk" : "review";
}

export function evidenceCell(finding: Finding): string | undefined {
  const ref = finding.evidenceRefs.find((r) => r.evidenceId)?.evidenceId;
  if (!ref) return undefined;
  const match = /-(\d{2}_[a-z0-9_]+)-r(\d+)-c\d+/i.exec(ref);
  if (!match) return undefined;
  const sheet = SHEET_LABELS[match[1].toLowerCase()] ?? match[1];
  return `${sheet} · row ${match[2]}`;
}

export function sortFindings(findings: Finding[]): Finding[] {
  const rank: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  return [...findings].sort(
    (a, b) =>
      (rank[a.severity] ?? 9) - (rank[b.severity] ?? 9) || a.title.localeCompare(b.title),
  );
}
