import Link from "next/link";
import { notFound } from "next/navigation";
import { TraceReadyLogo } from "@/components/TraceReadyLogo";

const roleConfig = {
  operator: {
    label: "Operator Login",
    title: "Enter the Operator Workspace",
    description: "Upload traceability workbooks, run readiness audits, resolve gaps, and export evidence packages.",
    badge: "Workbook audit access",
    alternateHref: "/login/reviewer",
    alternateLabel: "Reviewer login",
    signupHref: "/signup/operator"
  },
  reviewer: {
    label: "Consultant Reviewer Login",
    title: "Enter the Reviewer Workbench",
    description: "For TraceReady consultants and legal reviewers approving source-backed rule cards, citations, customer findings, and package gates.",
    badge: "Consultant review access",
    alternateHref: "/login/operator",
    alternateLabel: "Operator login",
    signupHref: "/signup/reviewer"
  }
} as const;

function normalizeLoginRoute(role: string): keyof typeof roleConfig | undefined {
  if (role === "operator" || role === "partner") return "operator";
  if (role === "reviewer" || role === "consultant") return "reviewer";
  return undefined;
}

function errorMessage(error?: string): string | undefined {
  if (!error) return undefined;
  if (error === "valid_email_required") return "Use a valid work email.";
  if (error === "password_required") return "Enter your password.";
  if (error === "signin_failed") return "We could not sign you in with those credentials.";
  if (error === "email_not_verified") return "Confirm your email before signing in.";
  if (error === "missing_code") return "The Supabase confirmation link is missing a code.";
  if (error === "profile_required") return "Your Supabase user needs an active TraceReady profile role.";
  if (error === "profile_inactive") return "Your TraceReady profile is not active.";
  return error;
}

export default async function LoginPage({
  params,
  searchParams
}: {
  params: Promise<{ role: string }>;
  searchParams?: Promise<{ error?: string; next?: string; auth?: string; status?: string; email?: string }>;
}) {
  const { role } = await params;
  const loginRoute = normalizeLoginRoute(role);
  if (!loginRoute) notFound();
  const resolvedSearchParams = await searchParams;
  const config = roleConfig[loginRoute];
  const readableError = errorMessage(resolvedSearchParams?.error);

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <TraceReadyLogo />
        <span className={`badge ${loginRoute === "operator" ? "ok" : "warn"}`}>{config.badge}</span>
        <div>
          <h1>{config.title}</h1>
          <p className="muted">{config.description}</p>
        </div>
        {resolvedSearchParams?.auth === "required" ? (
          <p className="badge warn">Sign in to continue.</p>
        ) : null}
        {resolvedSearchParams?.status === "confirm_email" ? (
          <p className="auth-notice">Account created. Confirm {resolvedSearchParams.email ?? "your email"}, then sign in with your password.</p>
        ) : null}
        {readableError ? (
          <p className="badge danger">{readableError}</p>
        ) : null}
        <form action="/auth/login" method="post" className="auth-form">
          <input name="loginRole" type="hidden" value={loginRoute} />
          <input name="next" type="hidden" value={resolvedSearchParams?.next ?? ""} />
          <label>
            Work email
            <input autoComplete="email" name="email" placeholder="name@company.com" required type="email" />
          </label>
          <label>
            Password
            <input autoComplete="current-password" name="password" placeholder="Enter your password" required type="password" />
          </label>
          <button className="button" type="submit">
            Sign in
          </button>
        </form>
        <div className="auth-footer">
          <Link href={config.alternateHref}>{config.alternateLabel}</Link>
          <Link href={config.signupHref}>Create account</Link>
          <Link href="/">Back to overview</Link>
        </div>
      </section>
    </main>
  );
}
