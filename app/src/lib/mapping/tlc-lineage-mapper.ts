import type { TLCLineage } from "@/lib/ontology/types";
import type { WorkbookRow } from "@/lib/import/workbook-parser";

export function mapTlcLineage(rows: WorkbookRow[]): TLCLineage[] {
  return rows.map((row) => ({
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
}

function normalizeLineageStatus(value: string | undefined): TLCLineage["lineageStatus"] {
  const normalized = (value ?? "").toLowerCase();
  if (["linked", "gap", "conflicting", "unverified"].includes(normalized)) {
    return normalized as TLCLineage["lineageStatus"];
  }
  return "unverified";
}
