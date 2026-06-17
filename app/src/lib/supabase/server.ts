import { createClient } from "@supabase/supabase-js";
import { normalizeTraceReadyRole, type TraceReadyRole } from "@/lib/auth/session-cookie";

interface TraceReadyProfileRow {
  user_id: string;
  email: string | null;
  full_name?: string | null;
  company_name?: string | null;
  role: string;
  status: string;
}

export interface TraceReadyProfile {
  userId: string;
  email?: string;
  fullName?: string;
  companyName?: string;
  role: TraceReadyRole;
  status: "active" | "inactive" | "invited";
}

export function createSupabaseAnonClient() {
  const url = getSupabaseUrl();
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!publishableKey) {
    throw new Error("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY is required for Supabase Auth.");
  }

  return createClient(url, publishableKey, {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      persistSession: false
    }
  });
}

export function createSupabaseServiceClient() {
  const url = getSupabaseUrl();
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!serviceRoleKey) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY is required to read TraceReady role profiles.");
  }

  return createClient(url, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      persistSession: false
    }
  });
}

export async function getTraceReadyProfile(userId: string): Promise<TraceReadyProfile | undefined> {
  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase
    .from("traceready_profiles")
    .select("user_id,email,full_name,company_name,role,status")
    .eq("user_id", userId)
    .maybeSingle();

  if (error) {
    throw new Error(`Unable to load TraceReady profile: ${error.message}`);
  }

  if (!data) return undefined;
  const row = data as TraceReadyProfileRow;
  const role = normalizeTraceReadyRole(row.role);
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

export async function upsertTraceReadyProfile({
  userId,
  email,
  role,
  fullName,
  companyName,
  status = "active"
}: {
  userId: string;
  email: string;
  role: TraceReadyRole;
  fullName?: string;
  companyName?: string;
  status?: TraceReadyProfile["status"];
}): Promise<void> {
  const supabase = createSupabaseServiceClient();
  const { error } = await supabase.from("traceready_profiles").upsert(
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
    throw new Error(`Unable to create TraceReady profile: ${error.message}`);
  }
}

export async function activateTraceReadyProfile(userId: string): Promise<void> {
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
    throw new Error(`Unable to activate TraceReady profile: ${error.message}`);
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

function normalizeProfileStatus(value: unknown): TraceReadyProfile["status"] | undefined {
  if (value === "active" || value === "inactive" || value === "invited") return value;
  return undefined;
}
