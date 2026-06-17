export function normalizeProductName(value: string | undefined) {
  return (value ?? "").trim().replace(/\s+/g, " ");
}
