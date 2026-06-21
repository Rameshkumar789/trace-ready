import type { Metadata } from "next";
import BellwetherLanding from "@/components/BellwetherLanding";

export const metadata: Metadata = {
  title: "Bellwether — FSMA 204 readiness audit & remediation",
  description:
    "Bellwether Audit finds every traceability gap in your products, suppliers, lot codes, and transformation data before an audit, recall, or onboarding does."
};

export default function HomePage() {
  return <BellwetherLanding />;
}
