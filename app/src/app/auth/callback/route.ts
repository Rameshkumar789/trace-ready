import { NextResponse } from "next/server";
import { canAccessPath, defaultRedirectForRole } from "@/lib/auth/roles";
import { createServerSupabaseClient, getBellwetherProfile } from "@/lib/supabase/server";

// Supabase email-confirmation / OAuth callback. exchangeCodeForSession writes the
// auth cookie via the @supabase/ssr adapter, then we redirect into the workspace.
export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");

  if (!code) {
    return redirectToLogin(requestUrl, "missing_code");
  }

  try {
    const supabase = await createServerSupabaseClient();
    const { data, error } = await supabase.auth.exchangeCodeForSession(code);
    if (error || !data.user) {
      return redirectToLogin(requestUrl, error?.message ?? "supabase_callback_failed");
    }

    const profile = await getBellwetherProfile(data.user.id);
    if (!profile) {
      return redirectToLogin(requestUrl, "profile_required");
    }
    if (profile.status !== "active") {
      return redirectToLogin(requestUrl, "profile_inactive");
    }

    const requestedNext = safeNextPath(requestUrl.searchParams.get("next"));
    const destination =
      requestedNext && canAccessPath({ role: profile.role }, requestedNext)
        ? requestedNext
        : defaultRedirectForRole(profile.role);
    return NextResponse.redirect(new URL(destination, requestUrl.origin));
  } catch (error) {
    const message = error instanceof Error ? error.message : "supabase_callback_failed";
    return redirectToLogin(requestUrl, message);
  }
}

function safeNextPath(value: string | null): string {
  if (!value) return "";
  if (!value.startsWith("/") || value.startsWith("//")) return "";
  return value;
}

function redirectToLogin(url: URL, error: string): NextResponse {
  const destination = new URL("/login/operator", url.origin);
  destination.searchParams.set("error", error);
  return NextResponse.redirect(destination);
}
