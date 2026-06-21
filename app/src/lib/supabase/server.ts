import { createClient } from "@supabase/supabase-js";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { normalizeBellwetherRole, type BellwetherRole } from "@/lib/auth/roles";

interface BellwetherProfileRow {
  user_id: string;
  email: string | null;
  full_name?: string | null;
  company_name?: string | null;
  role: string;
  status: string;
}

export interface BellwetherProfile {
  userId: string;
  email?: string;
  fullName?: string;
  companyName?: string;
  role: BellwetherRole;
  status: "active" | "inactive" | "invited";
}

function getSupabasePublishableKey(): string {
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!key) {
    throw new Error("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY is required for Supabase Auth.");
  }
  return key;
}

// Cookie-bound Supabase client for Server Components, Route Handlers, and Server
// Actions. It reads/writes the @supabase/ssr auth cookie so sessions persist and
// refresh natively. In a Server Component context cookie writes throw (read-only);
// that is expected — the middleware refreshes the session on the next request.
export async function createServerSupabaseClient() {
  const cookieStore = await cookies();
  return createServerClient(getSupabaseUrl(), getSupabasePublishableKey(), {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
        } catch {
          // Called from a Server Component — safe to ignore; middleware refreshes the cookie.
        }
      }
    }
  });
}

function createSupabaseServiceClient() {
  const url = getSupabaseUrl();
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!serviceRoleKey) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY is required to read Bellwether role profiles.");
  }

  return createClient(url, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      persistSession: false
    }
  });
}

export async function getBellwetherProfile(userId: string): Promise<BellwetherProfile | undefined> {
  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase
    .from("traceready_profiles")
    .select("user_id,email,full_name,company_name,role,status")
    .eq("user_id", userId)
    .maybeSingle();

  if (error) {
    throw new Error(`Unable to load Bellwether profile: ${error.message}`);
  }

  if (!data) return undefined;
  const row = data as BellwetherProfileRow;
  const role = normalizeBellwetherRole(row.role);
  const status = normalizeProfileStatus(row.status);
  if (!role || !status) return undefined;

  return {
    userId: row.user_id,
    email: row.email ?? undefined,
    fullName: row.full_name ?? undefined,
    companyName: row.company_name ?? undefined,
    role,
    status
  };
}

export async function upsertBellwetherProfile({
  userId,
  email,
  role,
  fullName,
  companyName,
  status = "active"
}: {
  userId: string;
  email: string;
  role: BellwetherRole;
  fullName?: string;
  companyName?: string;
  status?: BellwetherProfile["status"];
}): Promise<void> {
  const supabase = createSupabaseServiceClient();
  const { error } = await supabase.from("bellwether_profiles").upsert(
    {
      user_id: userId,
      email: email.trim().toLowerCase(),
      full_name: fullName?.trim() || null,
      company_name: companyName?.trim() || null,
      role,
      status,
      updated_at: new Date().toISOString()
    },
    { onConflict: "user_id" }
  );

  if (error) {
    throw new Error(`Unable to create Bellwether profile: ${error.message}`);
  }
}

export async function activateBellwetherProfile(userId: string): Promise<void> {
  const supabase = createSupabaseServiceClient();
  const { error } = await supabase
    .from("traceready_profiles")
    .update({
      status: "active",
      updated_at: new Date().toISOString()
    })
    .eq("user_id", userId)
    .eq("status", "invited");

  if (error) {
    throw new Error(`Unable to activate Bellwether profile: ${error.message}`);
  }
}

export function getApplicationOrigin(headersList?: Headers): string {
  const configuredUrl = process.env.NEXT_PUBLIC_APP_URL;
  if (configuredUrl) return configuredUrl.replace(/\/$/u, "");

  const host = headersList?.get("x-forwarded-host") ?? headersList?.get("host");
  if (!host) return "http://localhost:3000";
  const protocol = headersList?.get("x-forwarded-proto") ?? "http";
  return `${protocol}://${host}`;
}

function getSupabaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  if (!url) {
    throw new Error("NEXT_PUBLIC_SUPABASE_URL is required for Supabase Auth.");
  }
  return url;
}

function normalizeProfileStatus(value: unknown): BellwetherProfile["status"] | undefined {
  if (value === "active" || value === "inactive" || value === "invited") return value;
  return undefined;
}
