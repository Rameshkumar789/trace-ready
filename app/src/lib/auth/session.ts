import { createServerSupabaseClient, getBellwetherProfile } from "@/lib/supabase/server";
import type { BellwetherRole } from "./roles";

// The session is now sourced from Supabase Auth (the @supabase/ssr cookie that
// the middleware keeps fresh). We validate the user with auth.getUser(), then
// enrich with the profile row (name/company/role); user_metadata is the fallback.

export interface BellwetherSession {
  userId: string;
  email: string;
  fullName?: string;
  companyName?: string;
  role: BellwetherRole;
}

function metaString(metadata: Record<string, unknown> | undefined, key: string): string | undefined {
  const value = metadata?.[key];
  return typeof value === "string" && value.trim() ? value : undefined;
}

export async function getBellwetherSession(): Promise<BellwetherSession | undefined> {
  const supabase = await createServerSupabaseClient();
  const {
    data: { user }
  } = await supabase.auth.getUser();
  if (!user) return undefined;

  let profile;
  try {
    profile = await getBellwetherProfile(user.id);
  } catch {
    profile = undefined;
  }

  const metadata = user.user_metadata as Record<string, unknown> | undefined;

  return {
    userId: user.id,
    email: user.email ?? profile?.email ?? "",
    fullName: profile?.fullName ?? metaString(metadata, "full_name"),
    companyName: profile?.companyName ?? metaString(metadata, "company_name"),
    role: profile?.role ?? "operator"
  };
}

export const getPilotSession = getBellwetherSession;
