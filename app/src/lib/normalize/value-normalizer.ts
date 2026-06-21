export function normalizeBooleanLike(value: string | boolean | undefined): boolean | "unknown" {
  if (typeof value === "boolean") return value;
  const normalized = (value ?? "").trim().toLowerCase();
  if (["yes", "y", "true", "1", "covered"].includes(normalized)) return true;
  if (["no", "n", "false", "0", "not covered"].includes(normalized)) return false;
  return "unknown";
}

