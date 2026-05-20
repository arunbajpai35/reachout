import { forwardRef, type ButtonHTMLAttributes, type HTMLAttributes, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn, scorePercent, scoreTier } from "@/lib/cn";
import type { JobStatus } from "@/lib/api";
import { Loader2 } from "lucide-react";

// ---------- Button ----------
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  loading?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, className, children, disabled, ...rest },
  ref,
) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors " +
    "disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-indigo-500";
  const sizes = { sm: "px-2.5 py-1.5 text-xs", md: "px-3.5 py-2 text-sm" };
  const variants = {
    primary: "bg-slate-900 text-white hover:bg-slate-800",
    secondary: "bg-slate-100 text-slate-900 hover:bg-slate-200",
    ghost: "text-slate-700 hover:bg-slate-100",
    danger: "bg-rose-600 text-white hover:bg-rose-500",
  };
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(base, sizes[size], variants[variant], className)}
      {...rest}
    >
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {children}
    </button>
  );
});

// ---------- Card ----------
export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-xl border border-slate-200 bg-white shadow-sm", className)}
      {...rest}
    />
  );
}

export function CardHeader({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("border-b border-slate-100 px-5 py-3", className)} {...rest} />;
}

export function CardBody({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 py-4", className)} {...rest} />;
}

// ---------- Input / Textarea ----------
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "block w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm",
          "placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500",
          className,
        )}
        {...rest}
      />
    );
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...rest }, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "block w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm leading-relaxed",
        "placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500",
        className,
      )}
      {...rest}
    />
  );
});

// ---------- Badge ----------
type BadgeTone = "slate" | "indigo" | "emerald" | "amber" | "rose" | "violet" | "blue";
export function Badge({
  tone = "slate",
  children,
  className,
}: {
  tone?: BadgeTone;
  children: React.ReactNode;
  className?: string;
}) {
  const tones: Record<BadgeTone, string> = {
    slate: "bg-slate-100 text-slate-700",
    indigo: "bg-indigo-100 text-indigo-700",
    emerald: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-800",
    rose: "bg-rose-100 text-rose-700",
    violet: "bg-violet-100 text-violet-700",
    blue: "bg-blue-100 text-blue-700",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

// ---------- Status pill (job lifecycle) ----------
const STATUS_TONE: Record<JobStatus, BadgeTone> = {
  pending: "amber",
  extracted: "blue",
  recruiters_pending: "violet",
  recruiters_found: "emerald",
  failed: "rose",
};

const STATUS_LABEL: Record<JobStatus, string> = {
  pending: "extracting",
  extracted: "ready to confirm company",
  recruiters_pending: "finding recruiters",
  recruiters_found: "recruiters ready",
  failed: "failed",
};

export function StatusPill({ status }: { status: JobStatus }) {
  const pulsing = status === "pending" || status === "recruiters_pending";
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          {
            amber: "bg-amber-500",
            blue: "bg-blue-500",
            violet: "bg-violet-500",
            emerald: "bg-emerald-500",
            rose: "bg-rose-500",
            slate: "bg-slate-500",
            indigo: "bg-indigo-500",
          }[STATUS_TONE[status]],
          pulsing && "animate-pulse",
        )}
      />
      <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>
    </span>
  );
}

// ---------- ScoreBar ----------
export function ScoreBar({ score }: { score: number }) {
  const pct = scorePercent(score);
  const tier = scoreTier(score);
  const color = {
    high: "bg-emerald-500",
    mid: "bg-blue-500",
    low: "bg-amber-500",
    weak: "bg-slate-300",
  }[tier];
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-100">
        <div className={cn("h-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs tabular-nums text-slate-600">{pct}</span>
    </div>
  );
}

// ---------- Spinner ----------
export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-4 w-4 animate-spin text-slate-400", className)} />;
}

// ---------- Section header ----------
export function SectionTitle({
  children,
  hint,
}: {
  children: React.ReactNode;
  hint?: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex items-baseline justify-between">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        {children}
      </h2>
      {hint && <span className="text-xs text-slate-400">{hint}</span>}
    </div>
  );
}
