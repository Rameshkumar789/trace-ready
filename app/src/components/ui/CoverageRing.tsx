import { cn } from "./cn";
import type { Tone } from "./tone";

const strokeForTone: Record<Tone, string> = {
  ok: "var(--color-ok)",
  review: "var(--color-review)",
  risk: "var(--color-risk)",
  accent: "var(--color-accent)",
  neutral: "var(--color-muted)",
};

function toneForValue(value: number): Tone {
  if (value >= 90) return "ok";
  if (value >= 70) return "review";
  return "risk";
}

/** SVG donut showing a 0–100 coverage percentage. */
export function CoverageRing({
  value,
  label,
  size = 120,
  tone,
  className,
}: {
  value: number;
  label?: string;
  size?: number;
  tone?: Tone;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  const resolvedTone = tone ?? toneForValue(pct);
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = (pct / 100) * circumference;

  return (
    <div className={cn("inline-flex flex-col items-center gap-2", className)}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-line)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeForTone[resolvedTone]}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
        <text
          x="50%"
          y="50%"
          dominantBaseline="central"
          textAnchor="middle"
          className="rotate-90 fill-ink text-[20px] font-bold"
          style={{ transformOrigin: "center" }}
        >
          {pct}%
        </text>
      </svg>
      {label ? <span className="text-xs font-medium text-muted">{label}</span> : null}
    </div>
  );
}
