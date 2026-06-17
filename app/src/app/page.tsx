import Link from "next/link";
import { TraceReadyLogo } from "@/components/TraceReadyLogo";

type IconName =
  | "source"
  | "gap"
  | "proof"
  | "records"
  | "rules"
  | "fields"
  | "events"
  | "export"
  | "ingest"
  | "map"
  | "validate"
  | "resolve"
  | "operator"
  | "reviewer";

function Icon({ name }: { name: IconName }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 2
  };

  return (
    <svg aria-hidden="true" className="section-icon-svg" viewBox="0 0 24 24">
      {name === "source" && (
        <>
          <path {...common} d="M6 21V8l6-4 6 4v13" />
          <path {...common} d="M4 21h16" />
          <path {...common} d="M9 21v-6h6v6" />
          <path {...common} d="M9 10h.01M12 10h.01M15 10h.01" />
        </>
      )}
      {name === "gap" && (
        <>
          <path {...common} d="M12 3 2.8 19h18.4L12 3Z" />
          <path {...common} d="M12 9v4" />
          <path {...common} d="M12 17h.01" />
        </>
      )}
      {name === "proof" && (
        <>
          <path {...common} d="M20 7 9 18l-5-5" />
          <path {...common} d="M4 7V5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H8" />
        </>
      )}
      {name === "records" && (
        <>
          <path {...common} d="M7 3h7l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
          <path {...common} d="M14 3v5h5" />
          <path {...common} d="M8 12h8M8 16h8" />
        </>
      )}
      {name === "rules" && (
        <>
          <path {...common} d="M5 4h14v16H5z" />
          <path {...common} d="M8 8h8M8 12h8M8 16h5" />
          <path {...common} d="M4 7h2M4 12h2M4 17h2" />
        </>
      )}
      {name === "fields" && (
        <>
          <path {...common} d="M4 5h16v14H4z" />
          <path {...common} d="M4 10h16M9 5v14" />
          <path {...common} d="M12 14h5" />
        </>
      )}
      {name === "events" && (
        <>
          <circle {...common} cx="6" cy="7" r="2" />
          <circle {...common} cx="18" cy="7" r="2" />
          <circle {...common} cx="12" cy="17" r="2" />
          <path {...common} d="M8 8.5 11 15M16 8.5 13 15M8 7h8" />
        </>
      )}
      {name === "export" && (
        <>
          <path {...common} d="M12 3v12" />
          <path {...common} d="m7 10 5 5 5-5" />
          <path {...common} d="M5 21h14" />
          <path {...common} d="M6 17v4M18 17v4" />
        </>
      )}
      {name === "ingest" && (
        <>
          <path {...common} d="M12 3v12" />
          <path {...common} d="m7 8 5-5 5 5" />
          <path {...common} d="M5 15h14v5H5z" />
        </>
      )}
      {name === "map" && (
        <>
          <path {...common} d="M4 6h5l3 12h8" />
          <path {...common} d="M9 6h11" />
          <path {...common} d="M15 6v12" />
          <circle {...common} cx="4" cy="6" r="2" />
          <circle {...common} cx="20" cy="6" r="2" />
          <circle {...common} cx="20" cy="18" r="2" />
        </>
      )}
      {name === "validate" && (
        <>
          <path {...common} d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6l-7-3Z" />
          <path {...common} d="m9 12 2 2 4-5" />
        </>
      )}
      {name === "resolve" && (
        <>
          <path {...common} d="M5 4h14v16H5z" />
          <path {...common} d="m8 9 2 2 4-4" />
          <path {...common} d="M8 15h8" />
        </>
      )}
      {name === "operator" && (
        <>
          <circle {...common} cx="9" cy="8" r="3" />
          <path {...common} d="M3 20c.8-4 3-6 6-6s5.2 2 6 6" />
          <path {...common} d="M16 8h5M18.5 5.5v5" />
        </>
      )}
      {name === "reviewer" && (
        <>
          <path {...common} d="M6 3h9l3 3v15H6z" />
          <path {...common} d="M15 3v4h4" />
          <path {...common} d="m8 14 2 2 5-6" />
        </>
      )}
    </svg>
  );
}

const readiness = [
  ["Scope", "In scope", "ready"],
  ["CTEs", "8/9", "ready"],
  ["KDEs", "14 gaps", "warn"],
  ["Lots", "3 breaks", "risk"]
];

const exceptions = [
  ["Missing source reference", "Receiving", "High"],
  ["TLC not preserved", "Transformation", "High"],
  ["Ship date mismatch", "Shipping", "Review"]
];

const outcomes: Array<{ icon: IconName; title: string; copy: string }> = [
  { icon: "fields", title: "Find missing KDEs", copy: "Catch required fields, lot codes, and source references before review." },
  { icon: "events", title: "Check every event", copy: "Validate receiving, shipping, transformation, packing, cooling, and harvest records." },
  { icon: "export", title: "Export the proof", copy: "Create a sortable, evidence-linked package your team can defend." }
];

const buyerReasons: Array<{ icon: IconName; title: string; copy: string }> = [
  { icon: "source", title: "More records are required", copy: "FSMA 204 adds traceability records for covered foods and critical tracking events." },
  { icon: "gap", title: "Gaps are hard to see", copy: "KDEs, TLCs, supplier records, and event data are often spread across messy files." },
  { icon: "proof", title: "Proof is the output", copy: "TraceReady shows what is ready, what is missing, and what needs review." }
];

const flow: Array<{ icon: IconName; step: string; detail: string }> = [
  { icon: "ingest", step: "Ingest", detail: "Workbooks, EDI, ERP exports" },
  { icon: "map", step: "Map", detail: "Events, lots, KDEs" },
  { icon: "validate", step: "Validate", detail: "Approved rule checks" },
  { icon: "resolve", step: "Resolve", detail: "Exception workflow" },
  { icon: "export", step: "Export", detail: "Audit-ready package" }
];

const integrationSources = ["Excel / CSV", "EDI 856", "WMS", "ERP", "Supplier files", "API"];

const integrationOutputs = ["Missing KDEs", "TLC gaps", "Exception queue", "Sortable report"];

export default function HomePage() {
  return (
    <main className="home">
      <nav className="topbar" aria-label="Primary">
        <TraceReadyLogo />
        <div className="topbar-links">
          <a href="#why">Why</a>
          <a href="#product">Product</a>
          <a href="#integrations">Integrations</a>
          <a href="#proof">Proof</a>
          <a href="#access">Access</a>
        </div>
        <div className="topbar-actions">
          <Link className="button secondary" href="/login/reviewer">
            Reviewer Login
          </Link>
          <Link className="button" href="/login/operator">
            Operator Login
          </Link>
        </div>
      </nav>

      <section className="home-hero">
        <div className="hero-copy">
          <span className="eyebrow">FSMA 204 readiness</span>
          <h1>Make traceability provable.</h1>
          <p>
            Upload food traceability records. Find missing KDEs, broken TLCs,
            and risky event gaps before an audit or recall.
          </p>
          <div className="hero-actions">
            <Link className="button large" href="/login/operator">
              Run readiness audit
            </Link>
            <Link className="button secondary large" href="/login/reviewer">
              Review rule cards
            </Link>
          </div>
          <div className="hero-proof">
            <span>Excel in</span>
            <span>Gaps found</span>
            <span>Proof exported</span>
          </div>
        </div>

        <section className="product-console" aria-label="TraceReady dashboard preview">
          <div className="console-sidebar">
            <TraceReadyLogo href="/" />
            <a className="active">Dashboard</a>
            <a>Uploads</a>
            <a>Trace Checks</a>
            <a>Exceptions</a>
            <a>Reports</a>
          </div>
          <div className="console-main">
            <div className="console-header">
              <div>
                <span className="console-kicker">Readiness workspace</span>
                <h2>Traceability record set</h2>
              </div>
              <span className="badge warn">Needs review</span>
            </div>

            <div className="readiness-grid">
              {readiness.map(([label, value, status]) => (
                <div className={`readiness-card ${status}`} key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>

            <div className="console-panels">
              <article className="upload-card">
                <span className="mini-icon">XLS</span>
                <strong>shipment_records.xlsx</strong>
                <small>Records checked</small>
                <div className="progress-bar">
                  <span />
                </div>
              </article>

              <article className="citation-card">
                <h3>Source-backed checks</h3>
                <div><span /> eCFR rule source</div>
                <div><span /> FDA traceability list</div>
                <div><span /> Approved rule cards</div>
              </article>
            </div>

            <div className="exception-panel">
              <div className="exception-head">
                <h3>Exception queue</h3>
                <Link href="/login/operator">View report</Link>
              </div>
              {exceptions.map(([issue, event, level]) => (
                <div className="exception-row" key={issue}>
                  <strong>{issue}</strong>
                  <span>{event}</span>
                  <em>{level}</em>
                </div>
              ))}
            </div>
          </div>
        </section>
      </section>

      <section className="why-section" id="why" aria-label="Why operators need TraceReady">
        <div className="why-copy">
          <span className="eyebrow">Why it matters</span>
          <h2>FSMA 204 makes traceability proof a real operating requirement.</h2>
          <p>
            Most teams already have records. The risk is not knowing whether those
            records are complete, linked, and export-ready when someone asks.
          </p>
        </div>
        <div className="why-cards">
          {buyerReasons.map(({ icon, title, copy }) => (
            <article key={title}>
              <span className={`section-icon why-icon ${icon}`}>
                <Icon name={icon} />
              </span>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="evidence-section" aria-label="TraceReady evidence workflow">
        <div className="evidence-heading">
          <span className="eyebrow">Workflow</span>
          <h2>Upload records. Check the rule. Export proof.</h2>
        </div>
        <div className="evidence-strip">
          <div>
            <span className="section-icon workflow-icon records">
              <Icon name="records" />
            </span>
            <strong>Records</strong>
            <span>Upload supplier, shipment, lot, receiving, and transformation records.</span>
          </div>
          <div>
            <span className="section-icon workflow-icon rules">
              <Icon name="rules" />
            </span>
            <strong>Rules</strong>
            <span>Check FSMA 204 scope, CTEs, KDEs, TLCs, exemptions, and gaps.</span>
          </div>
          <div>
            <span className="section-icon workflow-icon proof">
              <Icon name="proof" />
            </span>
            <strong>Proof</strong>
            <span>Export a sortable, citation-backed readiness report.</span>
          </div>
        </div>
      </section>

      <section className="product-section" id="product">
        <div className="section-heading">
          <span className="eyebrow">Capabilities</span>
          <h2>See if your traceability records will hold up.</h2>
        </div>
        <div className="tiles three">
          {outcomes.map(({ icon, title, copy }, index) => (
            <article key={title}>
              <span className={`section-icon tile-icon product-icon ${icon} tone-${index + 1}`}>
                <Icon name={icon} />
              </span>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="proof-section" id="proof">
        <div className="proof-copy">
          <span className="eyebrow">Audit evidence</span>
          <h2>Every finding points to the record and the rule.</h2>
          <p>
            TraceReady shows the affected event, missing KDE or TLC issue,
            source row, review status, and rule citation behind each gap.
          </p>
        </div>
        <div className="flow-line">
          {flow.map(({ icon, step, detail }) => (
            <div className="flow-step" key={step}>
              <span className={`section-icon flow-icon ${icon}`}>
                <Icon name={icon} />
              </span>
              <strong>{step}</strong>
              <small>{detail}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="integration-section" id="integrations" aria-label="TraceReady integrations">
        <div className="integration-copy">
          <span className="eyebrow">Integrations</span>
          <h2>Bring your data. Get audit-ready evidence.</h2>
          <ul className="integration-benefits">
            <li>Connect systems you already use</li>
            <li>Map records to FSMA 204</li>
            <li>Surface gaps and actions</li>
          </ul>
        </div>
        <div className="integration-map" aria-label="Supported TraceReady data flow">
          <div className="integration-stack">
            <strong>Inputs</strong>
            {integrationSources.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          <div className="integration-hub">
            <span className="trace-mini-mark" aria-hidden="true">
              <svg viewBox="0 0 54 42">
                <path d="M7 27.5C14.5 27.5 15.8 16 24 16h6.5c7.6 0 8.8 10.5 16.5 10.5" />
                <circle cx="7" cy="27.5" r="5" />
                <circle cx="24" cy="16" r="5" />
                <circle cx="47" cy="26.5" r="5.4" />
              </svg>
            </span>
            <strong>TraceReady</strong>
            <em>Validate</em>
          </div>
          <div className="integration-stack output">
            <strong>Outputs</strong>
            {integrationOutputs.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="access-section" id="access">
        <div className="access-heading">
          <span className="eyebrow">Role-based access</span>
          <h2>Two workspaces. One source of truth.</h2>
          <p>Operators run checks. Reviewers approve rules.</p>
        </div>
        <article className="access-card partner">
          <div className="role-icon partner-icon">
            <Icon name="operator" />
          </div>
          <h3>Operators</h3>
          <p>Run checks. Close gaps. Be ready.</p>
          <ul className="role-actions">
            <li>Upload traceability records</li>
            <li>View gaps and exceptions</li>
            <li>Track resolution status</li>
            <li>Export audit-ready package</li>
          </ul>
          <Link className="button" href="/login/operator">
            Enter Operator Portal
          </Link>
        </article>
        <article className="access-card consultant">
          <div className="role-icon reviewer-icon">
            <Icon name="reviewer" />
          </div>
          <h3>Reviewers</h3>
          <p>Approve rules. Ensure accuracy.</p>
          <ul className="role-actions reviewer-actions">
            <li>Review rule cards and sources</li>
            <li>Approve KDE requirements</li>
            <li>Run scenario tests</li>
            <li>Publish rule versions</li>
          </ul>
          <Link className="button secondary" href="/login/reviewer">
            Enter Reviewer Console
          </Link>
        </article>
      </section>

      <footer className="site-footer">
        <div className="footer-main">
          <div className="footer-brand">
            <TraceReadyLogo />
            <p>Traceability readiness for food records, integrations, exceptions, and audit proof.</p>
          </div>

          <div className="footer-column">
            <strong>Product</strong>
            <a href="#why">Why TraceReady</a>
            <a href="#product">Trace checks</a>
            <a href="#integrations">Integrations</a>
            <a href="#proof">Audit evidence</a>
          </div>

          <div className="footer-column">
            <strong>Connect</strong>
            <a href="#product">Excel upload</a>
            <a href="#integrations">EDI 856 ASN</a>
            <a href="#integrations">WMS / ERP</a>
            <a href="#integrations">API feeds</a>
          </div>

          <div className="footer-column">
            <strong>Access</strong>
            <Link href="/login/operator">Operator Portal</Link>
            <Link href="/login/reviewer">Reviewer Console</Link>
            <a href="#access">Operator workspace</a>
            <a href="#proof">Rule review</a>
          </div>

          <div className="footer-column">
            <strong>Readiness</strong>
            <a href="#why">FSMA 204</a>
            <a href="#product">KDE checks</a>
            <a href="#product">TLC gaps</a>
            <a href="#proof">Sortable export</a>
          </div>
        </div>

        <div className="footer-bottom">
          <span>© 2026 TraceReady. All rights reserved.</span>
          <div>
            <a href="#why">Security</a>
            <a href="#proof">Compliance</a>
            <a href="#access">Status</a>
          </div>
        </div>
      </footer>
    </main>
  );
}
