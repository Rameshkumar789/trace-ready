export function normalizeBooleanLike(value: string | boolean | undefined): boolean | "unknown" {
  if (typeof value === "boolean") return value;
  const normalized = (value ?? "").trim().toLowerCase();
  if (["yes", "y", "true", "1", "covered"].includes(normalized)) return true;
  if (["no", "n", "false", "0", "not covered"].includes(normalized)) return false;
  return "unknown";
}

export function normalizeText(value: unknown) {
  return String(value ?? "").trim();
}

export function normalizeUnit(value: string | undefined) {
  return normalizeText(value).toLowerCase();
}

export function normalizeQuantity(value: string | number | undefined) {
  const parsed = typeof value === "number" ? value : Number(String(value ?? "").replace(/,/g, ""));
  return Number.isFinite(parsed) ? parsed : undefined;
}
