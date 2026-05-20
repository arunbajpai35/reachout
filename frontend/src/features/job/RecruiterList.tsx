import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type RankedRecruiter, type RecruiterContact } from "@/lib/api";
import { Badge, Button, Card, CardBody, ScoreBar } from "@/components/ui";
import { cn, copy } from "@/lib/cn";
import {
  Check,
  ChevronDown,
  ChevronRight,
  Copy as CopyIcon,
  ExternalLink,
  Mail,
  MapPin,
  Phone,
  UserSearch,
} from "lucide-react";

type RecruiterListProps = {
  recruiters: RankedRecruiter[];
  selectedId: string | null;
  onSelect: (r: RankedRecruiter) => void;
  jobId: string;
};

export default function RecruiterList({
  recruiters,
  selectedId,
  onSelect,
  jobId,
}: RecruiterListProps) {
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
          jobId={jobId}
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
  jobId,
}: {
  recruiter: RankedRecruiter;
  selected: boolean;
  onSelect: () => void;
  jobId: string;
}) {
  const [showRationale, setShowRationale] = useState(false);
  const parsed = parseRationale(recruiter.rationale);
  const qc = useQueryClient();
  const enrich = useMutation({
    mutationFn: () => api.recruiters.enrich(recruiter.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recruiters", jobId] }),
  });

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

          <ContactStrip
            recruiter={recruiter}
            onEnrich={() => enrich.mutate()}
            enriching={enrich.isPending}
            error={enrich.error ? (enrich.error as Error).message : null}
          />

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

function ContactStrip({
  recruiter,
  onEnrich,
  enriching,
  error,
}: {
  recruiter: RankedRecruiter;
  onEnrich: () => void;
  enriching: boolean;
  error: string | null;
}) {
  const hasContacts = recruiter.contacts.length > 0;
  const triedAndEmpty = !hasContacts && recruiter.enriched_at !== null;

  return (
    <div className="mt-3" onClick={(e) => e.stopPropagation()}>
      {hasContacts && (
        <div className="space-y-1">
          {recruiter.contacts.map((c, i) => (
            <ContactRow key={i} contact={c} />
          ))}
        </div>
      )}

      {!hasContacts && !triedAndEmpty && (
        <Button variant="secondary" size="sm" onClick={onEnrich} loading={enriching}>
          <UserSearch className="h-3 w-3" />
          Find contact
        </Button>
      )}

      {triedAndEmpty && (
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>No contact info found.</span>
          <button
            onClick={onEnrich}
            disabled={enriching}
            className="text-slate-500 underline-offset-2 hover:underline disabled:opacity-50"
          >
            {enriching ? "retrying…" : "retry"}
          </button>
        </div>
      )}

      {error && (
        <div className="mt-1 rounded bg-rose-50 px-2 py-1 text-[11px] text-rose-700">
          {error}
        </div>
      )}
    </div>
  );
}

function ContactRow({ contact }: { contact: RecruiterContact }) {
  const [copied, setCopied] = useState(false);
  const Icon = contact.kind === "phone" ? Phone : Mail;
  const label =
    contact.kind === "work_email"
      ? "Work email"
      : contact.kind === "personal_email"
      ? "Personal email"
      : "Phone";

  async function doCopy() {
    if (await copy(contact.value)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  }

  return (
    <div className="flex items-center gap-2 rounded-md border border-slate-100 bg-slate-50 px-2 py-1">
      <Icon className="h-3 w-3 text-slate-500" />
      <span className="text-[10px] uppercase tracking-wide text-slate-400">{label}</span>
      <span className="flex-1 truncate font-mono text-xs text-slate-700">{contact.value}</span>
      {contact.verified && <Badge tone="emerald">verified</Badge>}
      {contact.confidence !== null && contact.confidence !== undefined && !contact.verified && (
        <span className="font-mono text-[10px] text-slate-400">
          c={contact.confidence.toFixed(2)}
        </span>
      )}
      <button
        onClick={doCopy}
        className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        title="Copy"
      >
        {copied ? (
          <Check className="h-3 w-3 text-emerald-600" />
        ) : (
          <CopyIcon className="h-3 w-3" />
        )}
      </button>
    </div>
  );
}
