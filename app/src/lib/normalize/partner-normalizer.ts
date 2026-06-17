export function normalizePartnerName(value: string | undefined) {
  return (value ?? "").trim().replace(/\s+/g, " ");
}
