import { loadRegulatoryBundle } from "@/lib/regulatory/data-loader";
import { mapWorkbookToOntology } from "@/lib/mapping/workbook-to-ontology";
import type { WorkbookRow } from "@/lib/import/workbook-parser";
import { runAudit } from "./audit-orchestrator";

const demoSheets: Record<string, WorkbookRow[]> = {
  "00_Business_Profile": [
    {
      business_id: "biz-1",
      company_name: "Bay Area Produce Co",
      business_type: "distributor",
      handles_ftl_foods: "yes",
      covered_entity_status: "not_determined"
    }
  ],
  "01_Product_Master": [
    { product_id: "prod-1", product_name: "Fresh Basil", ftl_food_category: "Herbs fresh", is_ftl_maybe: "yes" },
    { product_id: "prod-2", product_name: "Mixed Fresh Item", ftl_food_category: "", is_ftl_maybe: "unknown" }
  ],
  "02_Location_Master": [{ location_id: "loc-1", location_name: "San Jose Warehouse", location_type: "warehouse" }],
  "03_Partner_Master": [{ partner_id: "supplier-1", partner_name: "Supplier A", partner_type: "external", relationship: "supplier" }],
  "04_Traceability_Plan": [
    { plan_item: "record_maintenance_procedure", answer: "Exports from WMS and invoices", evidence_id: "ev-plan-1" }
  ],
  "05_CTE_Events": [
    { event_id: "rec-1", event_type: "receiving", event_datetime: "2026-06-10", actor_location_id: "loc-1" },
    { event_id: "trans-1", event_type: "transformation", event_datetime: "2026-06-11", actor_location_id: "loc-1" },
    { event_id: "ship-1", event_type: "shipping", event_datetime: "2026-06-12", actor_location_id: "loc-1" }
  ],
  "06_Event_Line_Items": [
    {
      event_line_id: "line-1",
      event_id: "rec-1",
      product_id: "prod-1",
      product_name: "Fresh Basil",
      lot_or_tlc: "",
      source_lot_or_tlc: "",
      output_lot_or_tlc: ""
    },
    {
      event_line_id: "line-2",
      event_id: "trans-1",
      product_id: "prod-1",
      product_name: "Basil Pesto",
      lot_or_tlc: "",
      source_lot_or_tlc: "",
      output_lot_or_tlc: "TLC-PESTO-1"
    },
    {
      event_line_id: "line-3",
      event_id: "ship-1",
      product_id: "prod-1",
      product_name: "Basil Pesto",
      lot_or_tlc: "TLC-PESTO-1",
      source_lot_or_tlc: "",
      output_lot_or_tlc: ""
    }
  ],
  "07_KDE_Values": [
    { kde_id: "kde-1", event_id: "rec-1", cte_type: "receiving", kde_name: "Received date", field_key: "received_date", kde_value: "2026-06-10" },
    {
      kde_id: "kde-2",
      event_id: "ship-1",
      cte_type: "shipping",
      kde_name: "Reference document number",
      field_key: "reference_document_number",
      kde_value: "BOL-1"
    }
  ],
  "08_TLC_Lineage": [
    {
      lineage_id: "lin-1",
      relationship_type: "received_to_transformed",
      source_lot_or_tlc: "",
      target_lot_or_tlc: "TLC-PESTO-1",
      lineage_status: "gap"
    }
  ],
  "09_Source_Documents": [{ evidence_id: "ev-1", evidence_type: "invoice", evidence_status: "available", event_id: "rec-1" }],
  "10_Exemptions_Claims": [{ claim_id: "claim-1", claim_type: "small_producer", claimed_by: "Supplier A", evidence_provided: "no" }]
};

export function runDemoAudit() {
  const bundle = loadRegulatoryBundle();
  return runAudit({
    mode: "draft",
    ...bundle,
    dataset: mapWorkbookToOntology(demoSheets)
  });
}
