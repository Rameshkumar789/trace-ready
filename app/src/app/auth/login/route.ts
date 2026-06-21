import { NextResponse } from "next/server";
import { canAccessPath, defaultRedirectForRole } from "@/lib/auth/roles";
import { activateBellwetherProfile, createServerSupabaseClient, getBellwetherProfile } from "@/lib/supabase/server";

// Email/password login as a ROUTE HANDLER (not a Server Action). The @supabase/ssr
// client writes the auth session cookie via the cookies() adapter, and the 303
// redirect carries it back — reliable across browsers and stale deployments.
export async function POST(request: Request) {
  const origin = new URL(request.url).origin;
  const formData = await request.formData();
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const nextPath = safeNextPath(formData.get("next"));

  const fail = (error: string) =>
    NextResponse.redirect(new URL(`/login/operator?error=${encodeURIComponent(error)}`, origin), 303);

  if (!email || !email.includes("@")) return fail("valid_email_required");
  if (!password) return fail("password_required");

  let supabase: Awaited<ReturnType<typeof createServerSupabaseClient>>;
  try {
    supabase = await createServerSupabaseClient();
  } catch (error) {
    return fail(error instanceof Error ? error.message : "supabase_auth_not_configured");
  }

  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error || !data.user || !data.session) return fail(error?.message ?? "signin_failed");
  if (!data.user.email_confirmed_at) return fail("email_not_verified");

  const profile = await getBellwetherProfile(data.user.id);
  if (!profile) return fail("profile_required");
  if (profile.status === "invited") {
    await activateBellwetherProfile(data.user.id);
  } else if (profile.status !== "active") {
    return fail("profile_inactive");
  }

  const destination = nextPath && canAccessPath({ role: profile.role }, nextPath) ? nextPath : defaultRedirectForRole(profile.role);
  return NextResponse.redirect(new URL(destination, origin), 303);
}

function safeNextPath(value: FormDataEntryValue | null): string {
  if (typeof value !== "string") return "";
  if (!value.startsWith("/") || value.startsWith("//")) return "";
  return value;
}
