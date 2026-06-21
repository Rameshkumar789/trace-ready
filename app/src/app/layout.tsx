import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bellwether Audit",
  description: "FSMA 204 readiness audit for existing traceability records"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
