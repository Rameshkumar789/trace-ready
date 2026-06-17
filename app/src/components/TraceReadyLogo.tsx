import Link from "next/link";

export function TraceReadyLogo({ href = "/", linked = true, showText = true }: { href?: string; linked?: boolean; showText?: boolean }) {
  const content = (
    <>
      <span className="trace-logo" aria-hidden="true">
        <svg viewBox="0 0 54 42" role="img">
          <path className="trace-logo-path" d="M7 27.5C14.5 27.5 15.8 16 24 16h6.5c7.6 0 8.8 10.5 16.5 10.5" />
          <circle className="trace-logo-dot primary" cx="7" cy="27.5" r="5" />
          <circle className="trace-logo-dot" cx="24" cy="16" r="5" />
          <circle className="trace-logo-dot accent" cx="47" cy="26.5" r="5.4" />
        </svg>
      </span>
      {showText ? (
        <span>
          <strong>TraceReady</strong>
          <small>Make traceability provable.</small>
        </span>
      ) : null}
    </>
  );

  if (!linked) {
    return <span className={`brand ${showText ? "" : "mark-only"}`}>{content}</span>;
  }

  return (
    <Link className={`brand ${showText ? "" : "mark-only"}`} href={href}>
      {content}
    </Link>
  );
}
