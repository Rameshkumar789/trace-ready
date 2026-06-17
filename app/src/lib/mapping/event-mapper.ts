import type { CTEType, TraceabilityEvent } from "@/lib/ontology/types";
import type { WorkbookRow } from "@/lib/import/workbook-parser";
import { isCteType } from "@/lib/ontology/cte-types";

export function normalizeCteType(value: string | undefined): CTEType {
  const normalized = (value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  if (normalized === "ship") return "shipping";
  if (normalized === "receive") return "receiving";
  if (normalized === "pack" || normalized === "packing") return "initial_packing";
  if (normalized === "cool") return "cooling";
  return isCteType(normalized) ? normalized : "receiving";
}

export function mapEvents(rows: WorkbookRow[]): TraceabilityEvent[] {
  return rows.map((row) => ({
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
}
