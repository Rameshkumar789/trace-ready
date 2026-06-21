"use server";

import { redirect } from "next/navigation";
import { defaultRedirectForRole } from "@/lib/auth/roles";
import { createServerSupabaseClient, upsertBellwetherProfile } from "@/lib/supabase/server";

// Operator-only signup. Supabase Auth creates the user (and, if email confirmation
// is off, the @supabase/ssr client sets the session cookie); we mirror name/company
// into the profile row. Login itself is the /auth/login route handler.

function signupErrorPath(error: string): string {
  return `/signup/operator?error=${encodeURIComponent(error)}`;
}

export async function signUpAction(formData: FormData) {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const confirmPassword = String(formData.get("confirmPassword") ?? "");
  const fullName = String(formData.get("fullName") ?? "").trim();
  const companyName = String(formData.get("companyName") ?? "").trim();

  if (!fullName) redirect(signupErrorPath("full_name_required"));
  if (!companyName) redirect(signupErrorPath("company_required"));
  if (!email || !email.includes("@")) redirect(signupErrorPath("valid_email_required"));
  if (password.length < 12) redirect(signupErrorPath("password_too_short"));
  if (password !== confirmPassword) redirect(signupErrorPath("password_mismatch"));

  let supabase: Awaited<ReturnType<typeof createServerSupabaseClient>>;
  try {
    supabase = await createServerSupabaseClient();
  } catch (error) {
    redirect(signupErrorPath(error instanceof Error ? error.message : "supabase_auth_not_configured"));
  }

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { full_name: fullName, company_name: companyName }
    }
  });

  if (error || !data.user) {
    redirect(signupErrorPath(error?.message ?? "signup_failed"));
  }

  await upsertBellwetherProfile({
    userId: data.user.id,
    email,
    role: "operator",
    fullName,
    companyName,
    status: data.user.email_confirmed_at ? "active" : "invited"
  });

  if (!data.session || !data.user.email_confirmed_at) {
    redirect(`/login/operator?status=confirm_email&email=${encodeURIComponent(email)}`);
  }

  redirect(defaultRedirectForRole("operator"));
}
