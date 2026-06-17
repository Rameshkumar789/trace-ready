import type { KDE } from "@/lib/ontology/types";
import type { WorkbookRow } from "@/lib/import/workbook-parser";
import { normalizeCteType } from "./event-mapper";

export function mapKdeValues(rows: WorkbookRow[]): KDE[] {
  return rows.map((row, index) => ({
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
}
