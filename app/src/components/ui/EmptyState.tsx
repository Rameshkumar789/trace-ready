import type { ReactNode } from "react";
import { cn } from "./cn";

export function EmptyState({
  title,
  body,
  icon,
  action,
  className,
}: {
  title: ReactNode;
  body?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-card border border-dashed border-line bg-surface px-6 py-12 text-center",
        className,
      )}
    >
      {icon ? (
        <span className="inline-grid h-12 w-12 place-items-center rounded-card bg-surface-strong text-muted">
          {icon}
        </span>
      ) : null}
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {body ? <p className="max-w-md text-sm text-muted">{body}</p> : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
