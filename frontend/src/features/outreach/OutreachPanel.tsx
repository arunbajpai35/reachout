import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  ALL_CHANNELS,
  ALL_TONES,
  type Channel,
  type Job,
  type OutreachDraft,
  type RankedRecruiter,
  type Tone,
} from "@/lib/api";
import { Button, Card, CardBody, CardHeader, Spinner } from "@/components/ui";
import { cn } from "@/lib/cn";
import { Sparkles, X } from "lucide-react";
import DraftCard from "./DraftCard";

const CHANNEL_LABELS: Record<Channel, string> = {
  recruiter_email: "Email",
  linkedin_dm: "LinkedIn DM",
  networking_intro: "Networking intro",
};

const TONE_LABELS: Record<Tone, string> = {
  concise: "Concise",
  technical: "Technical",
  warm: "Warm",
  "founder-energy": "Founder energy",
};

export default function OutreachPanel({
  job,
  recruiter,
  onClose,
}: {
  job: Job;
  recruiter: RankedRecruiter | null;
  onClose: () => void;
}) {
  if (!recruiter) {
    return (
      <Card>
        <CardBody>
          <div className="text-sm text-slate-500">
            <Sparkles className="mb-2 inline h-4 w-4 text-indigo-400" />
            <p className="mb-1 font-medium text-slate-700">Pick a recruiter</p>
            <p className="text-xs">
              Select someone from the list to draft an email, LinkedIn DM, and short networking
              intro tailored to this role.
            </p>
          </div>
        </CardBody>
      </Card>
    );
  }
  return <PanelContent job={job} recruiter={recruiter} onClose={onClose} />;
}

function PanelContent({
  job,
  recruiter,
  onClose,
}: {
  job: Job;
  recruiter: RankedRecruiter;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const pairKey = ["outreach", job.id, recruiter.id];
  const [tone, setTone] = useState<Tone>("concise");

  const draftsQuery = useQuery({
    queryKey: pairKey,
    queryFn: () => api.outreach.listForPair(job.id, recruiter.id),
  });

  const generate = useMutation({
    mutationFn: () =>
      api.outreach.generate({
        job_id: job.id,
        recruiter_id: recruiter.id,
        channels: ALL_CHANNELS,
        tone,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: pairKey }),
  });

  const regenerate = useMutation({
    mutationFn: (id: string) => api.outreach.regenerate(id, tone),
    onSuccess: () => qc.invalidateQueries({ queryKey: pairKey }),
  });

  // Always show latest draft per channel.
  const latestByChannel: Partial<Record<Channel, OutreachDraft>> = {};
  for (const d of draftsQuery.data ?? []) {
    if (!latestByChannel[d.channel]) latestByChannel[d.channel] = d;
  }

  const hasAny = Object.keys(latestByChannel).length > 0;

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-wide text-slate-400">Drafting for</div>
          <div className="truncate text-sm font-medium text-slate-900">{recruiter.full_name}</div>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
          <X className="h-4 w-4" />
        </button>
      </CardHeader>

      <CardBody className="space-y-3">
        <ToneSelector value={tone} onChange={setTone} />
        <ContextDisclosure job={job} recruiter={recruiter} />

        {draftsQuery.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Spinner /> Loading drafts…
          </div>
        ) : !hasAny ? (
          <div className="rounded-md bg-slate-50 px-3 py-4 text-center">
            <p className="text-sm text-slate-600">No drafts yet for this recruiter.</p>
            <Button
              className="mt-3"
              onClick={() => generate.mutate()}
              loading={generate.isPending}
            >
              <Sparkles className="h-3.5 w-3.5" />
              Generate drafts
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {ALL_CHANNELS.map((ch) => {
              const draft = latestByChannel[ch];
              if (!draft) return null;
              return (
                <DraftCard
                  key={ch}
                  draft={draft}
                  label={CHANNEL_LABELS[ch]}
                  onRegenerate={() => regenerate.mutate(draft.id)}
                  regenerating={regenerate.isPending && regenerate.variables === draft.id}
                />
              );
            })}
            <div className="flex justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => generate.mutate()}
                loading={generate.isPending}
              >
                Regenerate all
              </Button>
            </div>
          </div>
        )}

        {generate.isError && (
          <div className="rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">
            {(generate.error as Error).message}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

// Inline disclosure showing exactly which fields flowed into the model.
function ContextDisclosure({ job, recruiter }: { job: Job; recruiter: RankedRecruiter }) {
  const [open, setOpen] = useState(false);
  const candidateQ = useQuery({ queryKey: ["candidate"], queryFn: () => api.candidate.get() });

  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="font-medium text-slate-600 hover:text-slate-900"
      >
        {open ? "Hide" : "Show"} context the model uses
      </button>
      {open && (
        <dl className="mt-2 space-y-1 text-slate-600">
          <Row k="Role">{job.parsed?.title ?? "—"}</Row>
          <Row k="Seniority">{job.parsed?.seniority ?? "—"}</Row>
          <Row k="Stack">{(job.parsed?.tech_stack ?? []).slice(0, 6).join(", ") || "—"}</Row>
          <Row k="Recruiter">
            {recruiter.full_name} · {recruiter.title ?? "—"}
          </Row>
          <Row k="Candidate target">{candidateQ.data?.target_role ?? "not set"}</Row>
          <Row k="Candidate skills">
            {(candidateQ.data?.skills ?? []).slice(0, 6).join(", ") || "not set"}
          </Row>
          {!candidateQ.data && (
            <div className="pt-1 text-amber-700">
              Tip: set your profile in <a href="/candidate" className="underline">Profile</a> for
              better drafts.
            </div>
          )}
        </dl>
      )}
    </div>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-2">
      <dt className="text-slate-400">{k}</dt>
      <dd className="truncate">{children}</dd>
    </div>
  );
}

function ToneSelector({ value, onChange }: { value: Tone; onChange: (t: Tone) => void }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-slate-500">
        Tone preset
      </div>
      <div className="grid grid-cols-2 gap-1">
        {ALL_TONES.map((t) => (
          <button
            key={t}
            onClick={() => onChange(t)}
            className={cn(
              "rounded-md border px-2 py-1.5 text-xs transition-colors",
              value === t
                ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                : "border-slate-200 text-slate-600 hover:bg-slate-50",
            )}
          >
            {TONE_LABELS[t]}
          </button>
        ))}
      </div>
    </div>
  );
}
