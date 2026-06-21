import { redirect } from "next/navigation";
import { OperatorLoginScreen } from "@/components/bellwether/OperatorLoginScreen";

// Bellwether is operator-only. The dynamic [role] segment is kept for back-compat
// (operator + partner alias); any other role is redirected to the operator login.

function errorMessage(error?: string): string | undefined {
  if (!error) return undefined;
  if (error === "valid_email_required") return "Use a valid work email.";
  if (error === "password_required") return "Enter your password.";
  if (error === "signin_failed") return "We could not sign you in with those credentials.";
  if (error === "email_not_verified") return "Confirm your email before signing in.";
  if (error === "missing_code") return "The Supabase confirmation link is missing a code.";
  if (error === "profile_required") return "Your Supabase user needs an active Bellwether profile role.";
  if (error === "profile_inactive") return "Your Bellwether profile is not active.";
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
  if (role !== "operator" && role !== "partner") {
    redirect("/login/operator");
  }
  const sp = await searchParams;

  return (
    <OperatorLoginScreen
      next={sp?.next ?? ""}
      error={errorMessage(sp?.error)}
      authRequired={sp?.auth === "required"}
      confirmEmail={sp?.status === "confirm_email"}
      confirmEmailAddress={sp?.email}
      signupHref="/signup/operator"
    />
  );
}
