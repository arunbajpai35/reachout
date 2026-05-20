import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type Job, type RankedRecruiter } from "@/lib/api";
import { Card, CardBody, CardHeader, Spinner, StatusPill, SectionTitle } from "@/components/ui";
import ExtractedRoleCard from "./ExtractedRoleCard";
import CompanyConfirmCard from "./CompanyConfirmCard";
import RecruiterList from "./RecruiterList";
import OutreachPanel from "@/features/outreach/OutreachPanel";

// Polling cadence: only poll while the backend is mid-pipeline.
function pollIntervalForStatus(status: Job["status"] | undefined): number | false {
  if (!status) return 1500;
  return status === "pending" || status === "recruiters_pending" ? 1500 : false;
}

export default function JobWorkspacePage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [selectedRecruiter, setSelectedRecruiter] = useState<RankedRecruiter | null>(null);

  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.jobs.get(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => pollIntervalForStatus(q.state.data?.status),
  });

  if (!jobId) return null;
  if (jobQuery.isLoading) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-slate-500">
        <Spinner /> Loading job…
      </div>
    );
  }
  if (jobQuery.isError || !jobQuery.data) {
    return <div className="text-sm text-rose-600">Couldn't load this job.</div>;
  }

  const job = jobQuery.data;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-400">Job</div>
            <h1 className="mt-1 text-2xl font-semibold text-slate-900">
              {job.title ?? job.parsed?.title ?? "Untitled role"}
            </h1>
            <div className="mt-1 text-sm text-slate-500">
              {job.company?.name ?? job.parsed?.company_name ?? "—"}
              {job.source && <span className="ml-2 text-slate-400">via {job.source}</span>}
            </div>
          </div>
          <StatusPill status={job.status} />
        </div>

        {job.status === "pending" && <PendingExtraction />}
        {job.error && job.status === "failed" && (
          <Card>
            <CardBody>
              <div className="text-sm text-rose-700">
                <strong>Extraction failed:</strong> {job.error}
              </div>
            </CardBody>
          </Card>
        )}

        {job.parsed && <ExtractedRoleCard parsed={job.parsed} />}

        {/* Company confirmation: shown whenever the job is awaiting the user's
            go-ahead to spend recruiter-API credits. We also show it when a slug
            is already cached on the company row (from a previous job for the
            same company) -- the user still needs to confirm to fire discovery. */}
        {job.company && (job.status === "extracted" || job.status === "failed") && (
          <CompanyConfirmCard job={job} />
        )}

        {/* Mid-discovery loader */}
        {job.status === "recruiters_pending" && (
          <Card>
            <CardBody>
              <div className="flex items-center gap-3 text-sm text-slate-600">
                <Spinner />
                <div>
                  Finding recruiters at <strong>{job.company?.name}</strong>…
                  <div className="text-xs text-slate-400">
                    Querying recruiter provider · classifying titles · scoring locations
                  </div>
                </div>
              </div>
            </CardBody>
          </Card>
        )}

        {job.status === "recruiters_found" && (
          <RecruitersSection
            jobId={job.id}
            selectedId={selectedRecruiter?.id ?? null}
            onSelect={setSelectedRecruiter}
          />
        )}
      </div>

      {/* Right rail: outreach drafts */}
      <aside className="lg:sticky lg:top-8 lg:self-start">
        <OutreachPanel
          job={job}
          recruiter={selectedRecruiter}
          onClose={() => setSelectedRecruiter(null)}
        />
      </aside>
    </div>
  );
}

function PendingExtraction() {
  return (
    <Card>
      <CardHeader className="text-sm font-medium text-slate-700">Extracting role</CardHeader>
      <CardBody>
        <div className="flex items-center gap-3 text-sm text-slate-600">
          <Spinner />
          <div>
            Reading job description, extracting structured fields with GPT-4o.
            <div className="text-xs text-slate-400">Usually takes 5–10 seconds.</div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function RecruitersSection({
  jobId,
  selectedId,
  onSelect,
}: {
  jobId: string;
  selectedId: string | null;
  onSelect: (r: RankedRecruiter) => void;
}) {
  const q = useQuery({
    queryKey: ["recruiters", jobId],
    queryFn: () => api.jobs.recruiters(jobId),
  });

  const allMock =
    !!q.data && q.data.length > 0 && q.data.every((r) => r.source === "mock");

  return (
    <section>
      <SectionTitle hint={q.data ? `${q.data.length} matched` : undefined}>
        Recruiters
      </SectionTitle>
      {allMock && (
        <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <strong>Demo data.</strong> These recruiters come from the mock provider, not LinkedIn.
          Names and LinkedIn URLs are synthetic and the profiles do not exist. Set
          <code className="mx-1 rounded bg-amber-100 px-1 py-0.5 font-mono">RECRUITER_PROVIDER=contactout</code>
          (or wait for Apify integration) to get real recruiters.
        </div>
      )}
      {q.isLoading ? (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Spinner /> Loading recruiters…
        </div>
      ) : (
        <RecruiterList
          recruiters={q.data ?? []}
          selectedId={selectedId}
          onSelect={onSelect}
          jobId={jobId}
        />
      )}
    </section>
  );
}
