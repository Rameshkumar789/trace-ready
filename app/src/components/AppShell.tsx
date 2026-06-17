import { cookies } from "next/headers";
import { getTraceReadySession } from "@/lib/auth/session";
import { AppShellFrame } from "./AppShellFrame";

const operatorLinks = [
  ["/operator", "Home"],
  ["/upload", "Upload Records"],
  ["/audits", "Audits"]
] as const;

const reviewerLinks = [
  ["/reviewer", "Reviewer Workbench", "review"],
  ["/admin/regulatory/review", "Review Queue", "review"]
] as const;

export async function AppShell({ children }: { children: React.ReactNode }) {
  const session = await getTraceReadySession();
  const cookieStore = await cookies();
  const initialNavCollapsed = cookieStore.get("traceready_nav_collapsed")?.value === "true";
  const links =
    session?.role === "operator"
      ? operatorLinks
      : session?.role === "founder_admin"
        ? [...operatorLinks, ...reviewerLinks]
        : reviewerLinks;

  return (
    <AppShellFrame
      initialNavCollapsed={initialNavCollapsed}
      links={links.map(([href, label, section]) => ({ href, label, section }))}
      profile={
        session
          ? {
              email: session.email,
              fullName: session.fullName,
              companyName: session.companyName,
              role: session.role === "operator" ? "Operator" : session.role === "fsma_reviewer" ? "Consultant Reviewer" : "Founder Admin"
            }
          : undefined
      }
    >
      {children}
    </AppShellFrame>
  );
}
