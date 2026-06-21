import type { ReactNode } from "react";
import { cn } from "./cn";
import { toneBorder, type Tone } from "./tone";

export function Card({
  children,
  className,
  padding = "md",
  accent,
  as: As = "div",
}: {
  children: ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  /** Adds a coloured left border to signal status. */
  accent?: Tone;
  as?: "div" | "section" | "article";
}) {
  const pad = { none: "", sm: "p-3", md: "p-5", lg: "p-6" }[padding];
  return (
    <As
      className={cn(
        "rounded-card border border-line bg-panel shadow-sm",
        accent && cn("border-l-4", toneBorder[accent]),
        pad,
        className,
      )}
    >
      {children}
    </As>
  );
}
