import { ArrowUp } from "lucide-react";
import { AppShell } from "@/components/AppShell";

export default function AskFsmaPage() {
  return (
    <AppShell>
      <div className="tr-page">
        <header className="tr-head">
          <div>
            <h1>Ask FSMA</h1>
            <p className="tr-sub">Ask about the FSMA 204 rule or your own records. Every answer is grounded in cited sources — no guessed compliance verdicts.</p>
          </div>
          <span className="tr-trust">Grounded in 21 CFR Subpart S</span>
        </header>

        <div className="tr-ask" aria-disabled="true">
          <span className="tr-ask-text">Ask about FSMA 204, or your own records…</span>
          <span className="tr-ask-send" aria-hidden="true"><ArrowUp size={16} /></span>
        </div>

        <section className="tr-outputs">
          <h2 className="tr-section-label">Coming soon</h2>
          <div className="tr-output-grid">
            <div className="tr-output">
              <div>
                <strong>Cited answers</strong>
                <span>Every claim links to the exact 21 CFR text it came from.</span>
              </div>
            </div>
            <div className="tr-output">
              <div>
                <strong>Answers about your records</strong>
                <span>Ask “what’s wrong with my cilantro shipments?” and get your real findings.</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
