"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getBellwetherSession } from "@/lib/auth/session";
import { createServerSupabaseClient, getApplicationOrigin, upsertBellwetherProfile } from "@/lib/supabase/server";

// Persist workspace settings: name/company go to the bellwether_profiles row;
// the rest (operation type, facilities, commodity, notification prefs, 2FA
// preference) live in Supabase user_metadata.
export async function saveSettingsAction(formData: FormData) {
  const session = await getBellwetherSession();
  if (!session) redirect("/login/operator?auth=required&next=/operator/settings");

  const fullName = String(formData.get("fullName") ?? "").trim();
  const companyName = String(formData.get("companyName") ?? "").trim();

  await upsertBellwetherProfile({
    userId: session.userId,
    email: session.email,
    role: session.role,
    fullName,
    companyName,
    status: "active"
  });

  const supabase = await createServerSupabaseClient();
  await supabase.auth.updateUser({
    data: {
      full_name: fullName,
      company_name: companyName,
      operation_type: String(formData.get("operationType") ?? ""),
      facilities: String(formData.get("facilities") ?? ""),
      primary_commodity: String(formData.get("primaryCommodity") ?? ""),
      notif_audit_complete: formData.get("notif_audit_complete") === "on",
      notif_high_severity: formData.get("notif_high_severity") === "on",
      notif_weekly_summary: formData.get("notif_weekly_summary") === "on",
      two_factor: formData.get("two_factor") === "on"
    }
  });

  redirect("/operator/settings?saved=1");
}

// Send a Supabase password-reset email to the signed-in operator.
export async function changePasswordAction() {
  const session = await getBellwetherSession();
  if (!session) redirect("/login/operator?auth=required&next=/operator/settings");

  const origin = getApplicationOrigin(await headers());
  const supabase = await createServerSupabaseClient();
  const { error } = await supabase.auth.resetPasswordForEmail(session.email, {
    redirectTo: `${origin}/auth/callback?next=/operator/settings`
  });

  redirect(`/operator/settings?reset=${error ? "error" : "sent"}`);
}
