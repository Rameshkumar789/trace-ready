// Workbook formats plus the inbound trading-partner formats the engine can normalize
// (CSV, EDI 856 ASN, EPCIS/GDSN XML).
const allowedExtensions = [".xlsx", ".xlsm", ".csv", ".edi", ".x12", ".asn", ".xml"];
const maxBytes = 10 * 1024 * 1024;

export function validateUploadMetadata(fileName: string, sizeBytes: number) {
  const errors: string[] = [];
  const lower = fileName.toLowerCase();
  if (!allowedExtensions.some((extension) => lower.endsWith(extension))) {
    errors.push("Allowed: .xlsx/.xlsm workbooks, .csv, EDI 856 (.edi/.x12/.asn), or EPCIS/GDSN .xml.");
  }
  if (sizeBytes > maxBytes) {
    errors.push("Workbook exceeds the 10 MB pilot upload limit.");
  }
  return { valid: errors.length === 0, errors };
}
