import type { ReactNode } from "react";
import { cn } from "./cn";

export function Chip({
  children,
  icon,
  className,
}: {
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-pill border border-line bg-surface px-2 py-0.5 text-xs font-medium text-muted",
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}
