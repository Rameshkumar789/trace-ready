import type { ReactNode } from "react";
import { cn } from "./cn";
import { toneSoft, type Tone } from "./tone";

export function StatusPill({
  tone = "neutral",
  children,
  icon,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 text-xs font-semibold whitespace-nowrap",
        toneSoft[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}
