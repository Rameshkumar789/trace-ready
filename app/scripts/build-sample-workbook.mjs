import ExcelJS from "exceljs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outputPath = path.resolve(__dirname, "../../data/samples/fsma204-full-audit-sample.xlsx");

const workbook = new ExcelJS.Workbook();
workbook.creator = "TraceReady";
workbook.created = new Date("2026-06-14T00:00:00.000Z");

const sheets = {
  "00_Business_Profile": {
    columns: ["business_id", "company_name", "business_type", "handles_ftl_foods", "covered_entity_status"],
    rows: [["biz-1", "Bay Area Produce Co", "distributor", "yes", "not_determined"]]
  },
  "01_Product_Master": {
    columns: ["product_id", "product_name", "ftl_food_category", "is_ftl_maybe"],
    rows: [
      ["prod-1", "Fresh Basil", "Herbs fresh", "yes"],
      ["prod-2", "Mixed Fresh Item", "", "unknown"]
    ]
  },
  "02_Location_Master": {
    columns: ["location_id", "location_name", "location_type"],
    rows: [["loc-1", "San Jose Warehouse", "warehouse"]]
  },
  "03_Partner_Master": {
    columns: ["partner_id", "partner_name", "partner_type", "relationship"],
    rows: [["supplier-1", "Supplier A", "external", "supplier"]]
  },
  "04_Traceability_Plan": {
    columns: ["plan_item", "answer", "evidence_id"],
    rows: [["record_maintenance_procedure", "Exports from WMS and invoices", "ev-plan-1"]]
  },
  "05_CTE_Events": {
    columns: ["event_id", "event_type", "event_datetime", "actor_location_id", "reference_record_type", "reference_record_no"],
    rows: [
      ["rec-1", "receiving", "2026-06-10", "loc-1", "invoice", "INV-1"],
      ["trans-1", "transformation", "2026-06-11", "loc-1", "batch_log", "BATCH-1"],
      ["ship-1", "shipping", "2026-06-12", "loc-1", "bol", "BOL-1"]
    ]
  },
  "06_Event_Line_Items": {
    columns: ["event_line_id", "event_id", "product_id", "product_name", "lot_or_tlc", "source_lot_or_tlc", "output_lot_or_tlc"],
    rows: [
      ["line-1", "rec-1", "prod-1", "Fresh Basil", "", "", ""],
      ["line-2", "trans-1", "prod-1", "Basil Pesto", "", "", "TLC-PESTO-1"],
      ["line-3", "ship-1", "prod-1", "Basil Pesto", "TLC-PESTO-1", "", ""]
    ]
  },
  "07_KDE_Values": {
    columns: ["kde_id", "event_id", "event_line_id", "cte_type", "kde_name", "field_key", "kde_value"],
    rows: [
      ["kde-1", "rec-1", "line-1", "receiving", "Received date", "received_date", "2026-06-10"],
      ["kde-2", "ship-1", "line-3", "shipping", "Reference document number", "reference_document_number", "BOL-1"]
    ]
  },
  "08_TLC_Lineage": {
    columns: ["lineage_id", "relationship_type", "source_lot_or_tlc", "target_lot_or_tlc", "lineage_status"],
    rows: [["lin-1", "received_to_transformed", "", "TLC-PESTO-1", "gap"]]
  },
  "09_Source_Documents": {
    columns: ["evidence_id", "event_id", "evidence_type", "evidence_status"],
    rows: [["ev-1", "rec-1", "invoice", "available"]]
  },
  "10_Exemptions_Claims": {
    columns: ["claim_id", "claim_type", "claimed_by", "evidence_provided"],
    rows: [["claim-1", "small_producer", "Supplier A", "no"]]
  }
};

for (const [name, sheet] of Object.entries(sheets)) {
  const worksheet = workbook.addWorksheet(name);
  worksheet.addRow(sheet.columns);
  for (const row of sheet.rows) worksheet.addRow(row);
  worksheet.getRow(1).font = { bold: true };
  worksheet.columns.forEach((column) => {
    column.width = 24;
  });
}

await workbook.xlsx.writeFile(outputPath);
console.log(outputPath);
