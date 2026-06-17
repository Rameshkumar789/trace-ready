export function normalizeTlc(value: string | undefined) {
  const normalized = (value ?? "").trim();
  return normalized.length > 0 ? normalized.toUpperCase() : undefined;
}
