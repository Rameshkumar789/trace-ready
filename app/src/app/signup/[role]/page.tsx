import Link from "next/link";
import { notFound } from "next/navigation";
import { TraceReadyLogo } from "@/components/TraceReadyLogo";
import { signUpAction } from "@/app/login/[role]/actions";

const roleConfig = {
  operator: {
    title: "Create an Operator Account",
    description: "For food operators who upload records, run audits, resolve exceptions, and export readiness evidence.",
    badge: "Audit workspace",
    loginHref: "/login/operator"
  },
  reviewer: {
    title: "Create a Consultant Reviewer Account",
    description: "For TraceReady consultants and legal reviewers who approve regulatory sources, rule cards, KDE requirements, customer findings, and scenario coverage.",
    badge: "Consultant review workspace",
    loginHref: "/login/reviewer"
  }
} as const;

function normalizeSignupRoute(role: string): keyof typeof roleConfig | undefined {
  if (role === "operator" || role === "partner") return "operator";
  if (role === "reviewer" || role === "consultant") return "reviewer";
  return undefined;
}

function errorMessage(error?: string): string | undefined {
  if (!error) return undefined;
  if (error === "full_name_required") return "Enter your full name.";
  if (error === "company_required") return "Enter your company name.";
  if (error === "valid_email_required") return "Use a valid work email.";
  if (error === "password_too_short") return "Use at least 12 characters for your password.";
  if (error === "password_mismatch") return "Passwords do not match.";
  if (error === "signup_failed") return "We could not create the account.";
  return error;
}

export default async function SignupPage({
  params,
  searchParams
}: {
  params: Promise<{ role: string }>;
  searchParams?: Promise<{ error?: string }>;
}) {
  const { role } = await params;
  const signupRoute = normalizeSignupRoute(role);
  if (!signupRoute) notFound();

  const resolvedSearchParams = await searchParams;
  const config = roleConfig[signupRoute];
  const readableError = errorMessage(resolvedSearchParams?.error);

  return (
    <main className="auth-page">
      <section className="auth-panel signup-panel">
        <TraceReadyLogo />
        <span className={`badge ${signupRoute === "operator" ? "ok" : "warn"}`}>{config.badge}</span>
        <div>
          <h1>{config.title}</h1>
          <p className="muted">{config.description}</p>
        </div>
        {readableError ? <p className="badge danger">{readableError}</p> : null}
        <form action={signUpAction} className="auth-form">
          <input name="loginRole" type="hidden" value={signupRoute} />
          <label>
            Full name
            <input autoComplete="name" name="fullName" placeholder="Ramesh Korlakunta" required type="text" />
          </label>
          <label>
            Company
            <input autoComplete="organization" name="companyName" placeholder="TraceReady pilot company" required type="text" />
          </label>
          <label>
            Work email
            <input autoComplete="email" name="email" placeholder="name@company.com" required type="email" />
          </label>
          <label>
            Password
            <input autoComplete="new-password" minLength={12} name="password" placeholder="At least 12 characters" required type="password" />
          </label>
          <label>
            Confirm password
            <input autoComplete="new-password" minLength={12} name="confirmPassword" placeholder="Re-enter password" required type="password" />
          </label>
          <button className="button" type="submit">
            Create account
          </button>
        </form>
        <div className="auth-footer">
          <Link href={config.loginHref}>Already have an account?</Link>
          <Link href="/">Back to overview</Link>
        </div>
      </section>
    </main>
  );
}
