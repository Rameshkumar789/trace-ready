"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  createSupabaseSession,
  defaultRedirectForRole,
  serializeSession,
  TRACEREADY_SESSION_COOKIE,
  type TraceReadyRole
} from "@/lib/auth/session-cookie";
import { activateTraceReadyProfile, createSupabaseAnonClient, getTraceReadyProfile, upsertTraceReadyProfile } from "@/lib/supabase/server";

function normalizeLoginRoute(role: string): "operator" | "reviewer" {
  return role === "reviewer" || role === "consultant" ? "reviewer" : "operator";
}

function roleForLoginRoute(role: "operator" | "reviewer"): TraceReadyRole {
  return role === "reviewer" ? "fsma_reviewer" : "operator";
}

function safeNextPath(nextPath: FormDataEntryValue | null): string {
  if (typeof nextPath !== "string") return "";
  if (!nextPath.startsWith("/") || nextPath.startsWith("//")) return "";
  return nextPath;
}

function loginErrorPath(loginRoute: "operator" | "reviewer", error: string): string {
  return `/login/${loginRoute}?error=${encodeURIComponent(error)}`;
}

function signupErrorPath(loginRoute: "operator" | "reviewer", error: string): string {
  return `/signup/${loginRoute}?error=${encodeURIComponent(error)}`;
}

export async function loginAction(formData: FormData) {
  const loginRole = normalizeLoginRoute(String(formData.get("loginRole") ?? "operator"));
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const nextPath = safeNextPath(formData.get("next"));

  if (!email || !email.includes("@")) {
    redirect(loginErrorPath(loginRole, "valid_email_required"));
  }
  if (!password) {
    redirect(loginErrorPath(loginRole, "password_required"));
  }

  let supabase: ReturnType<typeof createSupabaseAnonClient>;
  try {
    supabase = createSupabaseAnonClient();
  } catch (error) {
    const message = error instanceof Error ? error.message : "supabase_auth_not_configured";
    redirect(loginErrorPath(loginRole, message));
  }

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password
  });

  if (error || !data.user || !data.session) {
    redirect(loginErrorPath(loginRole, error?.message ?? "signin_failed"));
  }
  if (!data.user.email_confirmed_at) {
    redirect(loginErrorPath(loginRole, "email_not_verified"));
  }

  const profile = await getTraceReadyProfile(data.user.id);
  if (!profile) {
    redirect(loginErrorPath(loginRole, "profile_required"));
  }
  if (profile.status === "invited") {
    await activateTraceReadyProfile(data.user.id);
  } else if (profile.status !== "active") {
    redirect(loginErrorPath(loginRole, "profile_inactive"));
  }

  await setTraceReadySessionCookie({
    userId: data.user.id,
    email: data.user.email ?? profile.email ?? email,
    fullName: profile.fullName,
    companyName: profile.companyName,
    role: profile.role,
    expiresAt: data.session.expires_at ? data.session.expires_at * 1000 : Date.now() + 8 * 60 * 60 * 1000
  });

  redirect(nextPath || defaultRedirectForRole(profile.role));
}

export async function signUpAction(formData: FormData) {
  const loginRole = normalizeLoginRoute(String(formData.get("loginRole") ?? "operator"));
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const confirmPassword = String(formData.get("confirmPassword") ?? "");
  const fullName = String(formData.get("fullName") ?? "").trim();
  const companyName = String(formData.get("companyName") ?? "").trim();
  const role = roleForLoginRoute(loginRole);

  if (!fullName) {
    redirect(signupErrorPath(loginRole, "full_name_required"));
  }
  if (!companyName) {
    redirect(signupErrorPath(loginRole, "company_required"));
  }
  if (!email || !email.includes("@")) {
    redirect(signupErrorPath(loginRole, "valid_email_required"));
  }
  if (password.length < 12) {
    redirect(signupErrorPath(loginRole, "password_too_short"));
  }
  if (password !== confirmPassword) {
    redirect(signupErrorPath(loginRole, "password_mismatch"));
  }

  let supabase: ReturnType<typeof createSupabaseAnonClient>;
  try {
    supabase = createSupabaseAnonClient();
  } catch (error) {
    const message = error instanceof Error ? error.message : "supabase_auth_not_configured";
    redirect(signupErrorPath(loginRole, message));
  }

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName,
        company_name: companyName,
        requested_workspace: loginRole
      }
    }
  });

  if (error || !data.user) {
    redirect(signupErrorPath(loginRole, error?.message ?? "signup_failed"));
  }

  await upsertTraceReadyProfile({
    userId: data.user.id,
    email,
    role,
    fullName,
    companyName,
    status: data.user.email_confirmed_at ? "active" : "invited"
  });

  if (!data.session || !data.user.email_confirmed_at) {
    redirect(`/login/${loginRole}?status=confirm_email&email=${encodeURIComponent(email)}`);
  }

  await setTraceReadySessionCookie({
    userId: data.user.id,
    email: data.user.email ?? email,
    fullName,
    companyName,
    role,
    expiresAt: data.session.expires_at ? data.session.expires_at * 1000 : Date.now() + 8 * 60 * 60 * 1000
  });

  redirect(defaultRedirectForRole(role));
}

async function setTraceReadySessionCookie({
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
}): Promise<void> {
  const cookieStore = await cookies();
  const traceReadySession = createSupabaseSession({
    userId,
    email,
    fullName,
    companyName,
    role,
    expiresAt
  });

  const serialized = await serializeSession(traceReadySession);
  const maxAge = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
  // TEMP diagnostic — confirms login reached the cookie-set and the attributes it used.
  console.log(
    "[login-auth]",
    JSON.stringify({
      stage: "set-cookie",
      role,
      serializedLen: serialized.length,
      secure: process.env.NODE_ENV === "production",
      maxAge,
      expiresInMin: Math.round((expiresAt - Date.now()) / 60000)
    })
  );
  cookieStore.set(TRACEREADY_SESSION_COOKIE, serialized, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge
  });
}
