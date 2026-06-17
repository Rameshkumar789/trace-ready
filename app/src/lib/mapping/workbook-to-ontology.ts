import type {
  BusinessProfile,
  CTEType,
  ExemptionClaim,
  FTLItem,
  KDE,
  NormalizedAuditDataset,
  ProductScopeDecision,
  SourceDocument,
  TLCLineage,
  TraceabilityEvent,
  TraceabilityPlan
} from "@/lib/ontology/types";
import type { WorkbookRow } from "@/lib/import/workbook-parser";
import { normalizeBooleanLike } from "@/lib/normalize/value-normalizer";

export function mapWorkbookToOntology(sheets: Record<string, WorkbookRow[]>): NormalizedAuditDataset {
  const businessProfiles = (sheets["00_Business_Profile"] ?? []).map<BusinessProfile>((row, index) => ({
    businessId: row.business_id || `business-${index + 1}`,
    companyName: row.company_name || "Unknown company",
    businessType: row.business_type,
    handlesFtlFoods: normalizeBooleanLike(row.handles_ftl_foods),
    coveredEntityStatus: normalizeCoveredStatus(row.covered_entity_status),
    evidenceRefs: [{ sheet: "00_Business_Profile", row: index + 2 }]
  }));

  const products = (sheets["01_Product_Master"] ?? []).map<FTLItem>((row) => ({
    productId: row.product_id,
    productName: row.product_name,
    ftlCategory: row.ftl_food_category,
    isFtlMaybe: normalizeBooleanLike(row.is_ftl_maybe)
  }));

  const productScopeDecisions = products.map<ProductScopeDecision>((product) => ({
    productId: product.productId,
    status: product.isFtlMaybe === true ? "covered" : product.isFtlMaybe === false ? "not_covered" : "not_determined",
    reason: product.isFtlMaybe === "unknown" ? "Product scope needs review." : "Mapped from product master FTL flag.",
    evidenceRefs: [{ sheet: "01_Product_Master", field: product.productName }]
  }));

  const traceabilityPlans = [
    {
      exists: (sheets["04_Traceability_Plan"] ?? []).length > 0,
      recordMaintenanceProcedure: findPlanAnswer(sheets, "record_maintenance_procedure"),
      ftlIdentificationProcedure: findPlanAnswer(sheets, "ftl_identification_procedure"),
      tlcAssignmentProcedure: findPlanAnswer(sheets, "tlc_assignment_procedure"),
      pointOfContact: findPlanAnswer(sheets, "point_of_contact"),
      farmMapAvailable: normalizeBooleanLike(findPlanAnswer(sheets, "farm_map_available") ?? "unknown"),
      evidenceRefs: [{ sheet: "04_Traceability_Plan" }]
    } satisfies TraceabilityPlan
  ];

  const events = (sheets["05_CTE_Events"] ?? []).map<TraceabilityEvent>((row) => ({
    eventId: row.event_id,
    sourceSystem: row.source_system,
    eventType: normalizeCteType(row.event_type),
    eventDatetime: row.event_datetime,
    actorLocationId: row.actor_location_id,
    fromPartnerId: row.from_partner_id,
    toPartnerId: row.to_partner_id,
    referenceRecordType: row.reference_record_type,
    referenceRecordNo: row.reference_record_no,
    eventStatus: row.event_status
  }));

  const lineItems = (sheets["06_Event_Line_Items"] ?? []).map((row) => ({
    eventLineId: row.event_line_id,
    eventId: row.event_id,
    productId: row.product_id,
    productName: row.product_name,
    ftlCategory: row.ftl_category,
    lotOrTlc: row.lot_or_tlc,
    quantity: row.quantity ? Number(row.quantity) : undefined,
    unit: row.unit,
    sourceLotOrTlc: row.source_lot_or_tlc,
    outputLotOrTlc: row.output_lot_or_tlc
  }));

  const kdeValues = (sheets["07_KDE_Values"] ?? []).map<KDE>((row, index) => ({
    kdeId: row.kde_id || `kde-${index + 1}`,
    eventId: row.event_id,
    eventLineId: row.event_line_id,
    cteType: normalizeCteType(row.cte_type),
    kdeName: row.kde_name,
    fieldKey: row.field_key || row.kde_name,
    value: row.kde_value,
    status: row.kde_value ? "present" : "missing",
    evidenceRefs: [{ sheet: "07_KDE_Values", row: index + 2, field: row.field_key || row.kde_name }]
  }));

  const lineage = (sheets["08_TLC_Lineage"] ?? []).map<TLCLineage>((row) => ({
    lineageId: row.lineage_id,
    relationshipType: row.relationship_type,
    sourceEventId: row.source_event_id,
    sourceEventLineId: row.source_event_line_id,
    sourceLotOrTlc: row.source_lot_or_tlc,
    targetEventId: row.target_event_id,
    targetEventLineId: row.target_event_line_id,
    targetLotOrTlc: row.target_lot_or_tlc,
    lineageStatus: normalizeLineageStatus(row.lineage_status)
  }));

  const sourceDocuments = (sheets["09_Source_Documents"] ?? []).map<SourceDocument>((row) => ({
    evidenceId: row.evidence_id,
    eventId: row.event_id,
    eventLineId: row.event_line_id,
    evidenceType: row.evidence_type,
    fileOrUrl: row.file_or_url,
    referenceNo: row.reference_no,
    evidenceStatus: normalizeEvidenceStatus(row.evidence_status)
  }));

  const exemptionClaims = (sheets["10_Exemptions_Claims"] ?? []).map<ExemptionClaim>((row) => ({
    claimId: row.claim_id,
    claimType: row.claim_type,
    claimedBy: row.claimed_by,
    evidenceProvided: normalizeBooleanLike(row.evidence_provided) === true,
    decision: normalizeBooleanLike(row.evidence_provided) === true ? "partially_exempt" : "not_determined",
    evidenceRefs: [{ sheet: "10_Exemptions_Claims", field: row.claim_type }]
  }));

  return {
    businessProfiles,
    exemptionClaims,
    products,
    productScopeDecisions,
    traceabilityPlans,
    events,
    lineItems,
    kdeValues,
    lineage,
    sourceDocuments
  };
}

function findPlanAnswer(sheets: Record<string, WorkbookRow[]>, item: string) {
  return (sheets["04_Traceability_Plan"] ?? []).find((row) => row.plan_item === item)?.answer;
}

function normalizeCoveredStatus(value: string | undefined): BusinessProfile["coveredEntityStatus"] {
  const normalized = (value ?? "").toLowerCase();
  if (["covered", "not_covered", "exempt", "partially_exempt"].includes(normalized)) {
    return normalized as BusinessProfile["coveredEntityStatus"];
  }
  return "not_determined";
}

function normalizeCteType(value: string | undefined): CTEType {
  const normalized = (value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  if (normalized === "ship") return "shipping";
  if (normalized === "receive") return "receiving";
  if (normalized === "pack" || normalized === "packing") return "initial_packing";
  if (normalized === "cool") return "cooling";
  if (
    [
      "harvest",
      "cooling",
      "initial_packing",
      "first_land_based_receiving",
      "shipping",
      "receiving",
      "transformation"
    ].includes(normalized)
  ) {
    return normalized as CTEType;
  }
  return "receiving";
}

function normalizeLineageStatus(value: string | undefined): TLCLineage["lineageStatus"] {
  const normalized = (value ?? "").toLowerCase();
  if (["linked", "gap", "conflicting", "unverified"].includes(normalized)) return normalized as TLCLineage["lineageStatus"];
  return "unverified";
}

function normalizeEvidenceStatus(value: string | undefined): SourceDocument["evidenceStatus"] {
  const normalized = (value ?? "").toLowerCase();
  if (["available", "missing", "optional", "unverified"].includes(normalized)) return normalized as SourceDocument["evidenceStatus"];
  return "unverified";
}
