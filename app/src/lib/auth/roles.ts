// Pure role helpers (no crypto, no Next/Supabase deps). Relocated out of the old
// HMAC-cookie module when sessions moved to Supabase-native auth.

export type BellwetherRole = "operator" | "fsma_reviewer" | "founder_admin";

const operatorRoles = new Set<BellwetherRole>(["operator", "founder_admin"]);

export function normalizeBellwetherRole(value: unknown): BellwetherRole | undefined {
  if (value === "operator" || value === "partner" || value === "trace_ready_operator") return "operator";
  if (value === "reviewer" || value === "consultant" || value === "fsma_reviewer") return "fsma_reviewer";
  if (value === "admin" || value === "founder_admin") return "founder_admin";
  return undefined;
}

export function canAccessPath(session: { role: BellwetherRole } | undefined, pathname: string): boolean {
  if (!session) return false;
  if (pathname.startsWith("/operator")) return operatorRoles.has(session.role);
  return true;
}

export function defaultRedirectForRole(_role: BellwetherRole): string {
  return "/operator";
}

