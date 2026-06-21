/** Semantic status tones shared across the evidence-grade UI. */
export type Tone = "ok" | "review" | "risk" | "accent" | "neutral";

/** Soft-background + matching foreground, for pills, chips and stat accents. */
export const toneSoft: Record<Tone, string> = {
  ok: "bg-ok-soft text-ok",
  review: "bg-review-soft text-review",
  risk: "bg-risk-soft text-risk",
  accent: "bg-accent-soft text-accent-strong",
  neutral: "bg-surface-strong text-muted",
};

/** Left-border accent colour for cards. */
export const toneBorder: Record<Tone, string> = {
  ok: "border-l-ok",
  review: "border-l-review",
  risk: "border-l-risk",
  accent: "border-l-accent",
  neutral: "border-l-line",
};
