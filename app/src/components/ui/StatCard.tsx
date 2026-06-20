import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "./cn";
import { toneText, type Tone } from "./tone";

export function StatCard({
  label,
  value,
  hint,
  tone = "neutral",
  icon,
  href,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
  href?: string;
}) {
  const inner = (
    <>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted">
          {label}
        </span>
        {icon ? <span className={cn("shrink-0", toneText[tone])}>{icon}</span> : null}
      </div>
      <div
        className={cn(
          "mt-2 text-3xl font-bold leading-none",
          tone === "neutral" ? "text-ink" : toneText[tone],
        )}
      >
        {value}
      </div>
      {hint ? <div className="mt-1.5 text-xs text-muted">{hint}</div> : null}
    </>
  );

  const className =
    "block rounded-card border border-line bg-panel p-4 shadow-sm transition-colors";

  if (href) {
    return (
      <Link href={href} className={cn(className, "hover:bg-surface-strong")}>
        {inner}
      </Link>
    );
  }
  return <div className={className}>{inner}</div>;
}
