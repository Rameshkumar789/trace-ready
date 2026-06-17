const allowedExtensions = [".xlsx", ".xlsm"];
const maxBytes = 10 * 1024 * 1024;

export function validateUploadMetadata(fileName: string, sizeBytes: number) {
  const errors: string[] = [];
  const lower = fileName.toLowerCase();
  if (!allowedExtensions.some((extension) => lower.endsWith(extension))) {
    errors.push("Only .xlsx and .xlsm workbooks are allowed for the pilot upload.");
  }
  if (sizeBytes > maxBytes) {
    errors.push("Workbook exceeds the 10 MB pilot upload limit.");
  }
  return { valid: errors.length === 0, errors };
}
