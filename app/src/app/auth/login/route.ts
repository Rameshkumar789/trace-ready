import { NextResponse } from "next/server";
import {
  canAccessPath,
  createSupabaseSession,
  defaultRedirectForRole,
  serializeSession,
  TRACEREADY_SESSION_COOKIE
} from "@/lib/auth/session-cookie";
import { activateTraceReadyProfile, createSupabaseAnonClient, getTraceReadyProfile } from "@/lib/supabase/server";

const sessionTtlMs = 8 * 60 * 60 * 1000;

// Email/password login as a ROUTE HANDLER (not a Server Action). It sets the session cookie on a
// standard 303 redirect response, which every browser (incl. Safari) reliably persists — unlike
// cookies set inside a Server Action, which were silently dropped in production. Route handlers
// also have no Server-Action id, so they never break on a stale client / new deployment.
export async function POST(request: Request) {
  const origin = new URL(request.url).origin;
  const formData = await request.formData();
  const role = normalizeLoginRoute(formData.get("loginRole"));
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const nextPath = safeNextPath(formData.get("next"));

  const fail = (error: string) =>
    NextResponse.redirect(new URL(`/login/${role}?error=${encodeURIComponent(error)}`, origin), 303);

  if (!email || !email.includes("@")) return fail("valid_email_required");
  if (!password) return fail("password_required");

  let supabase: ReturnType<typeof createSupabaseAnonClient>;
  try {
    supabase = createSupabaseAnonClient();
  } catch (error) {
    return fail(error instanceof Error ? error.message : "supabase_auth_not_configured");
  }

  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error || !data.user || !data.session) return fail(error?.message ?? "signin_failed");
  if (!data.user.email_confirmed_at) return fail("email_not_verified");

  const profile = await getTraceReadyProfile(data.user.id);
  if (!profile) return fail("profile_required");
  if (profile.status === "invited") {
    await activateTraceReadyProfile(data.user.id);
  } else if (profile.status !== "active") {
    return fail("profile_inactive");
  }

  const expiresAt = data.session.expires_at ? data.session.expires_at * 1000 : Date.now() + sessionTtlMs;
  const session = createSupabaseSession({
    userId: data.user.id,
    email: data.user.email ?? profile.email ?? email,
    fullName: profile.fullName,
    companyName: profile.companyName,
    role: profile.role,
    expiresAt
  });

  const destination = nextPath && canAccessPath(session, nextPath) ? nextPath : defaultRedirectForRole(profile.role);
  const response = NextResponse.redirect(new URL(destination, origin), 303);
  response.cookies.set(TRACEREADY_SESSION_COOKIE, await serializeSession(session), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: Math.max(0, Math.floor((expiresAt - Date.now()) / 1000))
  });
  return response;
}

function normalizeLoginRoute(value: FormDataEntryValue | null): "operator" | "reviewer" {
  const role = String(value ?? "operator");
  return role === "reviewer" || role === "consultant" ? "reviewer" : "operator";
}

function safeNextPath(value: FormDataEntryValue | null): string {
  if (typeof value !== "string") return "";
  if (!value.startsWith("/") || value.startsWith("//")) return "";
  return value;
}
