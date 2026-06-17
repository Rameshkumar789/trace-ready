export function normalizeLocationName(value: string | undefined) {
  return (value ?? "").trim().replace(/\s+/g, " ");
}
