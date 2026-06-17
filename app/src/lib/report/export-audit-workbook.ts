import writeXlsxFile, { type SheetData } from "write-excel-file/node";
import type { StoredAudit } from "@/lib/audit/stored-audit";
import { buildAuditExportPackage } from "./export-package";

export async function exportAuditWorkbookBuffer(audit: StoredAudit): Promise<Buffer> {
  const artifact = buildAuditExportPackage(audit);
  const sheets = Object.entries(artifact).map(([name, rows]) => ({
    name,
    data: rowsToSheetData(rows)
  }));
  return writeXlsxFile(sheets).toBuffer();
}

function rowsToSheetData(rows: Array<Record<string, unknown>>): SheetData {
  if (rows.length === 0) return [["empty"]];
  const headers = Object.keys(rows[0]);
  return [
    headers,
    ...rows.map((row) => headers.map((header) => {
      const value = row[header];
      if (typeof value === "number" || typeof value === "boolean" || value instanceof Date) return value;
      return String(value ?? "");
    }))
  ];
}
