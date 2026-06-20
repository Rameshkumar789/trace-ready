import type { ReactNode } from "react";
import { cn } from "./cn";
import { toneSoft, type Tone } from "./tone";

export function SectionHeader({
  title,
  count,
  hint,
  icon,
  tone = "neutral",
  actions,
  className,
}: {
  title: ReactNode;
  count?: number;
  hint?: ReactNode;
  icon?: ReactNode;
  tone?: Tone;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-end justify-between gap-4", className)}>
      <div className="flex items-center gap-3">
        {icon ? (
          <span
            className={cn(
              "inline-grid h-9 w-9 place-items-center rounded-card",
              toneSoft[tone],
            )}
          >
            {icon}
          </span>
        ) : null}
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold text-ink">
            {title}
            {typeof count === "number" ? (
              <span className="rounded-pill bg-surface-strong px-2 py-0.5 text-xs font-semibold text-muted">
                {count}
              </span>
            ) : null}
          </h2>
          {hint ? <p className="mt-0.5 text-sm text-muted">{hint}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
