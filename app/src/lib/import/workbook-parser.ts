import readXlsxFile from "read-excel-file/node";
import { requiredWorkbookSheets } from "./workbook-schema";

export type WorkbookRow = Record<string, string>;

export interface WorkbookParseError {
  sheet: string;
  row?: number;
  column?: string;
  reason: string;
}

export interface ParsedWorkbook {
  sheets: Record<string, WorkbookRow[]>;
  errors: WorkbookParseError[];
}

export async function parseWorkbook(buffer: ArrayBuffer): Promise<ParsedWorkbook> {
  const workbookBuffer = Buffer.from(buffer);
  const workbookSheets = await readXlsxFile(workbookBuffer);
  const sheetNames = workbookSheets.map((sheet) => sheet.sheet);
  const sheets: Record<string, WorkbookRow[]> = {};
  const errors: WorkbookParseError[] = [];

  for (const required of requiredWorkbookSheets) {
    if (!sheetNames.includes(required.name)) {
      errors.push({ sheet: required.name, reason: "Required sheet is missing." });
      continue;
    }

    const rows = workbookSheets.find((sheet) => sheet.sheet === required.name)?.data ?? [];
    const [headerRow, ...dataRows] = rows;
    const headers = (headerRow ?? []).map((header: unknown) => normalizeHeader(String(header ?? "")));
    const normalizedRows = dataRows.map((row) =>
      Object.fromEntries(headers.map((header: string, index: number) => [header, String(row[index] ?? "").trim()]))
    );
    sheets[required.name] = normalizedRows;

    for (const column of required.columns) {
      const hasColumn = headers.includes(column);
      if (!hasColumn) {
        errors.push({ sheet: required.name, column, reason: "Required column is missing." });
      }
    }
  }

  return { sheets, errors };
}

export function validateParsedWorkbook(sheets: Record<string, WorkbookRow[]>): WorkbookParseError[] {
  const errors: WorkbookParseError[] = [];
  for (const required of requiredWorkbookSheets) {
    const rows = sheets[required.name];
    if (!rows) {
      errors.push({ sheet: required.name, reason: "Required sheet is missing." });
      continue;
    }
    rows.forEach((row, index) => {
      required.columns.forEach((column) => {
        if (!Object.prototype.hasOwnProperty.call(row, column)) {
          errors.push({ sheet: required.name, row: index + 2, column, reason: "Required column is missing." });
        }
      });
    });
  }
  return errors;
}

export function normalizeHeader(header: string) {
  return header.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}
