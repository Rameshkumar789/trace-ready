import { redirect } from "next/navigation";
import { OperatorSignupScreen } from "@/components/bellwether/OperatorSignupScreen";

// Bellwether is operator-only. The dynamic [role] segment is kept for back-compat
// (operator + partner alias); any other role is redirected to the operator signup.

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
  if (role !== "operator" && role !== "partner") {
    redirect("/signup/operator");
  }
  const sp = await searchParams;

  return <OperatorSignupScreen error={errorMessage(sp?.error)} loginHref="/login/operator" />;
}
