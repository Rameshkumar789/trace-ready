export const TRACEREADY_SESSION_COOKIE = "traceready_session";

export type TraceReadyRole = "operator" | "fsma_reviewer" | "founder_admin";

export interface TraceReadySession {
  authProvider: "supabase";
  userId: string;
  email: string;
  fullName?: string;
  companyName?: string;
  role: TraceReadyRole;
  issuedAt: number;
  expiresAt: number;
}

const operatorRoles = new Set<TraceReadyRole>(["operator", "founder_admin"]);
const regulatoryRoles = new Set<TraceReadyRole>(["fsma_reviewer", "founder_admin"]);

export function createSupabaseSession({
  userId,
  email,
  fullName,
  companyName,
  role,
  expiresAt
}: {
  userId: string;
  email: string;
  fullName?: string;
  companyName?: string;
  role: TraceReadyRole;
  expiresAt: number;
}): TraceReadySession {
  return {
    authProvider: "supabase",
    userId,
    email: email.trim().toLowerCase(),
    fullName: normalizeOptionalText(fullName),
    companyName: normalizeOptionalText(companyName),
    role,
    issuedAt: Date.now(),
    expiresAt
  };
}

export async function serializeSession(session: TraceReadySession): Promise<string> {
  const payload = base64UrlEncode(JSON.stringify(session));
  const signature = await signPayload(payload);
  return `${payload}.${signature}`;
}

export async function parseSessionCookie(value: string | undefined): Promise<TraceReadySession | undefined> {
  if (!value) return undefined;
  const [payload, signature] = value.split(".");
  if (!payload || !signature) return undefined;
  try {
    const expectedSignature = await signPayload(payload);
    if (!timingSafeEqual(signature, expectedSignature)) return undefined;
    const parsed = JSON.parse(base64UrlDecode(payload)) as Partial<TraceReadySession>;
    if (parsed.authProvider !== "supabase") return undefined;
    if (!parsed.userId || !parsed.email || !isTraceReadyRole(parsed.role)) return undefined;
    if (!parsed.issuedAt || !parsed.expiresAt || parsed.expiresAt <= Date.now()) return undefined;
    return {
      authProvider: "supabase",
      userId: parsed.userId,
      email: parsed.email,
      fullName: normalizeOptionalText(parsed.fullName),
      companyName: normalizeOptionalText(parsed.companyName),
      role: parsed.role,
      issuedAt: parsed.issuedAt,
      expiresAt: parsed.expiresAt
    };
  } catch {
    return undefined;
  }
}

// Edge-middleware-safe decode: validates the cookie's STRUCTURE and expiry WITHOUT verifying
// the HMAC signature, so it needs no secret and never fails just because the Edge runtime can't
// resolve TRACEREADY_AUTH_SECRET. Use this ONLY for optimistic routing in middleware. The
// authoritative signature check stays in parseSessionCookie (run server-side in getPilotSession),
// so a forged/tampered cookie passes the middleware but is rejected when a protected page renders.
export function decodeSessionCookieUnverified(value: string | undefined): TraceReadySession | undefined {
  if (!value) return undefined;
  const [payload, signature] = value.split(".");
  if (!payload || !signature) return undefined;
  try {
    const parsed = JSON.parse(base64UrlDecode(payload)) as Partial<TraceReadySession>;
    if (parsed.authProvider !== "supabase") return undefined;
    if (!parsed.userId || !parsed.email || !isTraceReadyRole(parsed.role)) return undefined;
    if (!parsed.issuedAt || !parsed.expiresAt || parsed.expiresAt <= Date.now()) return undefined;
    return {
      authProvider: "supabase",
      userId: parsed.userId,
      email: parsed.email,
      fullName: normalizeOptionalText(parsed.fullName),
      companyName: normalizeOptionalText(parsed.companyName),
      role: parsed.role,
      issuedAt: parsed.issuedAt,
      expiresAt: parsed.expiresAt
    };
  } catch {
    return undefined;
  }
}

function normalizeOptionalText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

export function isTraceReadyRole(value: unknown): value is TraceReadyRole {
  return value === "operator" || value === "fsma_reviewer" || value === "founder_admin";
}

export function normalizeTraceReadyRole(value: unknown): TraceReadyRole | undefined {
  if (value === "operator" || value === "partner" || value === "trace_ready_operator") return "operator";
  if (value === "reviewer" || value === "consultant" || value === "fsma_reviewer") return "fsma_reviewer";
  if (value === "admin" || value === "founder_admin") return "founder_admin";
  return undefined;
}

export function canAccessPath(session: TraceReadySession | undefined, pathname: string): boolean {
  if (!session) return false;
  if (pathname.startsWith("/admin") || pathname.startsWith("/reviewer")) return regulatoryRoles.has(session.role);
  if (pathname.startsWith("/audits") && pathname.includes("/review")) return operatorRoles.has(session.role) || regulatoryRoles.has(session.role);
  if (pathname.startsWith("/operator") || pathname.startsWith("/upload") || pathname.startsWith("/audits")) return operatorRoles.has(session.role);
  return true;
}

export function defaultRedirectForRole(role: TraceReadyRole): string {
  if (role === "operator") return "/operator";
  return "/reviewer";
}

export function loginPathForTarget(pathname: string): string {
  if (pathname.startsWith("/audits") && pathname.includes("/review")) return "/login/reviewer";
  return pathname.startsWith("/admin") || pathname.startsWith("/reviewer") ? "/login/reviewer" : "/login/operator";
}

function getAuthSecret(): string {
  const secret = process.env.TRACEREADY_AUTH_SECRET;
  if (!secret) {
    throw new Error("TRACEREADY_AUTH_SECRET is required for Supabase-backed TraceReady sessions.");
  }
  return secret;
}

async function signPayload(payload: string): Promise<string> {
  const cryptoApi = globalThis.crypto;
  if (!cryptoApi?.subtle) {
    throw new Error("Web Crypto is required to sign TraceReady sessions.");
  }
  const key = await cryptoApi.subtle.importKey(
    "raw",
    new TextEncoder().encode(getAuthSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await cryptoApi.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
  return bytesToBase64Url(new Uint8Array(signature));
}

function timingSafeEqual(left: string, right: string): boolean {
  if (left.length !== right.length) return false;
  let result = 0;
  for (let index = 0; index < left.length; index += 1) {
    result |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return result === 0;
}

function base64UrlEncode(value: string): string {
  return bytesToBase64Url(new TextEncoder().encode(value));
}

function base64UrlDecode(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/u, "");
}
