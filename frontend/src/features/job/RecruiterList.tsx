import { useState } from "react";
import type { RankedRecruiter } from "@/lib/api";
import { Badge, Card, CardBody, ScoreBar } from "@/components/ui";
import { cn } from "@/lib/cn";
import { ChevronDown, ChevronRight, ExternalLink, MapPin } from "lucide-react";

export default function RecruiterList({
  recruiters,
  selectedId,
  onSelect,
}: {
  recruiters: RankedRecruiter[];
  selectedId: string | null;
  onSelect: (r: RankedRecruiter) => void;
}) {
  if (recruiters.length === 0) {
    return (
      <Card>
        <CardBody className="text-sm text-slate-500">
          No recruiters matched the threshold. Try a different company slug or check the JD.
        </CardBody>
      </Card>
    );
  }
  return (
    <div className="space-y-2">
      {recruiters.map((r) => (
        <RecruiterCard
          key={r.id}
          recruiter={r}
          selected={r.id === selectedId}
          onSelect={() => onSelect(r)}
        />
      ))}
    </div>
  );
}

// Pull the title category out of the rationale string the backend stamps on every
// link row, e.g. "title=technical_recruiter(technical recruiter|w=1.0); location=tier1:bengaluru(1.0); ..."
function parseRationale(s: string): {
  category: string | null;
  signals: string | null;
  locationToken: string | null;
} {
  const titleMatch = s.match(/title=([a-z_]+)\(([^|)]*)/);
  const locMatch = s.match(/location=([^()]+)/);
  return {
    category: titleMatch?.[1] ?? null,
    signals: titleMatch?.[2] ?? null,
    locationToken: locMatch?.[1] ?? null,
  };
}

function categoryBadge(category: string | null) {
  if (category === "technical_recruiter")
    return <Badge tone="emerald">Technical recruiter</Badge>;
  if (category === "general_recruiter")
    return <Badge tone="blue">General recruiter</Badge>;
  return <Badge tone="rose">Unrelated</Badge>;
}

function locationBadge(token: string | null) {
  if (!token) return null;
  if (token.startsWith("tier1:"))
    return <Badge tone="emerald">Tier-1 India · {token.split(":")[1]}</Badge>;
  if (token.startsWith("tier2:"))
    return <Badge tone="blue">Tier-2 India · {token.split(":")[1]}</Badge>;
  if (token.startsWith("india_generic")) return <Badge tone="violet">India</Badge>;
  if (token.startsWith("remote")) return <Badge tone="amber">Remote</Badge>;
  if (token.startsWith("other:"))
    return <Badge tone="slate">Outside India · {token.split(":")[1]}</Badge>;
  return <Badge>{token}</Badge>;
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function RecruiterCard({
  recruiter,
  selected,
  onSelect,
}: {
  recruiter: RankedRecruiter;
  selected: boolean;
  onSelect: () => void;
}) {
  const [showRationale, setShowRationale] = useState(false);
  const parsed = parseRationale(recruiter.rationale);

  return (
    <button
      onClick={onSelect}
      className={cn(
        "block w-full rounded-xl border bg-white p-4 text-left transition-all",
        selected
          ? "border-indigo-500 ring-2 ring-indigo-100"
          : "border-slate-200 hover:border-slate-300 hover:shadow-sm",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-full bg-indigo-50 text-xs font-medium text-indigo-700">
          {initials(recruiter.full_name)}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium text-slate-900">
                  {recruiter.full_name}
                </span>
                {recruiter.linkedin_url && (
                  <a
                    href={recruiter.linkedin_url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-slate-300 hover:text-slate-600"
                  >
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
              {recruiter.title && (
                <div className="truncate text-xs text-slate-500">{recruiter.title}</div>
              )}
              {recruiter.location && (
                <div className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                  <MapPin className="h-3 w-3" />
                  {recruiter.location}
                </div>
              )}
            </div>

            <div className="flex-shrink-0">
              <ScoreBar score={recruiter.score} />
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            {categoryBadge(parsed.category)}
            {locationBadge(parsed.locationToken)}
            {parsed.signals && parsed.signals !== "none" && (
              <span className="text-xs text-slate-400">
                matched: <span className="font-mono">{parsed.signals}</span>
              </span>
            )}
          </div>

          <div className="mt-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowRationale((s) => !s);
              }}
              className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600"
            >
              {showRationale ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              {showRationale ? "Hide" : "Show"} ranking rationale
            </button>
            {showRationale && (
              <pre className="mt-1 whitespace-pre-wrap break-all rounded bg-slate-50 px-2 py-1 font-mono text-[11px] leading-relaxed text-slate-600">
                {recruiter.rationale}
              </pre>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
