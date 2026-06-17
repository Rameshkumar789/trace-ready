export interface RequiredSheet {
  name: string;
  description: string;
  columns: string[];
}

export const requiredWorkbookSheets: RequiredSheet[] = [
  {
    name: "00_Business_Profile",
    description: "Company, role, covered-entity, and current systems context.",
    columns: ["business_id", "company_name", "business_type", "handles_ftl_foods", "covered_entity_status"]
  },
  {
    name: "01_Product_Master",
    description: "Product names, FTL categories, and scope hints.",
    columns: ["product_id", "product_name", "ftl_food_category", "is_ftl_maybe"]
  },
  {
    name: "02_Location_Master",
    description: "Physical event and TLC source locations.",
    columns: ["location_id", "location_name", "location_type"]
  },
  {
    name: "03_Partner_Master",
    description: "Suppliers, customers, internal partners, and contacts.",
    columns: ["partner_id", "partner_name", "partner_type", "relationship"]
  },
  {
    name: "04_Traceability_Plan",
    description: "Traceability plan evidence and plan readiness fields.",
    columns: ["plan_item", "answer", "evidence_id"]
  },
  {
    name: "05_CTE_Events",
    description: "Event headers for all major CTEs.",
    columns: ["event_id", "event_type", "event_datetime", "actor_location_id"]
  },
  {
    name: "06_Event_Line_Items",
    description: "Product, lot/TLC, and quantity rows linked to CTE events.",
    columns: ["event_line_id", "event_id", "product_id", "product_name", "lot_or_tlc"]
  },
  {
    name: "07_KDE_Values",
    description: "Observed KDE values from event exports or mapped evidence.",
    columns: ["kde_id", "event_id", "cte_type", "kde_name", "field_key", "kde_value"]
  },
  {
    name: "08_TLC_Lineage",
    description: "Lot/TLC source-to-target relationships across events.",
    columns: ["lineage_id", "relationship_type", "source_lot_or_tlc", "target_lot_or_tlc", "lineage_status"]
  },
  {
    name: "09_Source_Documents",
    description: "Evidence files and source references tied to events.",
    columns: ["evidence_id", "evidence_type", "evidence_status"]
  },
  {
    name: "10_Exemptions_Claims",
    description: "Exemption or partial-exemption claims and supplied evidence.",
    columns: ["claim_id", "claim_type", "claimed_by", "evidence_provided"]
  }
];

export const generatedWorkbookSheets = [
  "11_TraceReady_Findings",
  "12_Readiness_Summary",
  "13_FDA_Sortable_Export_Check"
];
