import { NextResponse } from "next/server";
import {
  canAccessPath,
  createSupabaseSession,
  defaultRedirectForRole,
  serializeSession,
  TRACEREADY_SESSION_COOKIE
} from "@/lib/auth/session-cookie";
import { createSupabaseAnonClient, getTraceReadyProfile } from "@/lib/supabase/server";

const defaultSessionTtlMs = 8 * 60 * 60 * 1000;

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const loginRoute = normalizeLoginRoute(requestUrl.searchParams.get("role") ?? "operator");

  if (!code) {
    return redirectToLogin(requestUrl, loginRoute, "missing_code");
  }

  try {
    const supabase = createSupabaseAnonClient();
    const { data, error } = await supabase.auth.exchangeCodeForSession(code);
    if (error || !data.user) {
      return redirectToLogin(requestUrl, loginRoute, error?.message ?? "supabase_callback_failed");
    }

    const profile = await getTraceReadyProfile(data.user.id);
    if (!profile) {
      return redirectToLogin(requestUrl, loginRoute, "profile_required");
    }
    if (profile.status !== "active") {
      return redirectToLogin(requestUrl, loginRoute, "profile_inactive");
    }

    const email = data.user.email ?? profile.email;
    if (!email) {
      return redirectToLogin(requestUrl, loginRoute, "email_required");
    }

    const expiresAt = data.session?.expires_at ? data.session.expires_at * 1000 : Date.now() + defaultSessionTtlMs;
    const traceReadySession = createSupabaseSession({
      userId: data.user.id,
      email,
      role: profile.role,
      expiresAt
    });

    const requestedNext = safeNextPath(requestUrl.searchParams.get("next"));
    const destinationPath =
      requestedNext && canAccessPath(traceReadySession, requestedNext)
        ? requestedNext
        : defaultRedirectForRole(profile.role);
    const response = NextResponse.redirect(new URL(destinationPath, requestUrl.origin));
    response.cookies.set(TRACEREADY_SESSION_COOKIE, await serializeSession(traceReadySession), {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: Math.max(0, Math.floor((expiresAt - Date.now()) / 1000))
    });
    return response;
  } catch (error) {
    const message = error instanceof Error ? error.message : "supabase_callback_failed";
    return redirectToLogin(requestUrl, loginRoute, message);
  }
}

function normalizeLoginRoute(value: string): "operator" | "reviewer" {
  return value === "reviewer" || value === "consultant" ? "reviewer" : "operator";
}

function safeNextPath(value: string | null): string {
  if (!value) return "";
  if (!value.startsWith("/") || value.startsWith("//")) return "";
  return value;
}

function redirectToLogin(url: URL, loginRoute: "operator" | "reviewer", error: string): NextResponse {
  const destination = new URL(`/login/${loginRoute}`, url.origin);
  destination.searchParams.set("error", error);
  return NextResponse.redirect(destination);
}
