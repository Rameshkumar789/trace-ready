import type { ReactNode } from "react";
import { cn } from "./cn";

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  breadcrumb,
  className,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  breadcrumb?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex flex-col gap-4", className)}>
      {breadcrumb ? <div className="text-sm text-muted">{breadcrumb}</div> : null}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          {eyebrow ? (
            <div className="text-xs font-semibold uppercase tracking-wide text-accent">
              {eyebrow}
            </div>
          ) : null}
          <h1 className="mt-1 text-3xl font-bold leading-tight text-ink">{title}</h1>
          {subtitle ? (
            <p className="mt-2 text-base leading-relaxed text-muted">{subtitle}</p>
          ) : null}
        </div>
        {actions ? <div className="flex items-center gap-3">{actions}</div> : null}
      </div>
    </header>
  );
}
