import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Job } from "@/lib/api";
import { Button, Card, CardBody, CardHeader, Input } from "@/components/ui";
import { Building2 } from "lucide-react";

export default function CompanyConfirmCard({ job }: { job: Job }) {
  const company = job.company!;
  // Pre-fill: prefer already-confirmed slug on the company row, fall back to
  // the heuristic suggestion. Either way the user can edit before confirming.
  const [slug, setSlug] = useState(
    company.linkedin_slug ?? job.company_slug_suggestion ?? "",
  );
  const [name, setName] = useState(company.name);
  const qc = useQueryClient();

  const confirm = useMutation({
    mutationFn: () =>
      api.jobs.confirmCompany(job.id, {
        linkedin_slug: slug.trim().toLowerCase(),
        name: name !== company.name ? name : undefined,
      }),
    onSuccess: (updated) => qc.setQueryData(["job", job.id], updated),
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <Building2 className="h-4 w-4 text-indigo-600" />
          Confirm company
        </div>
      </CardHeader>
      <CardBody className="space-y-4">
        <p className="text-sm text-slate-600">
          We'll search for recruiters at this company on LinkedIn. Confirm or correct the slug
          before we run discovery — this is the only step that spends recruiter-API credits.
        </p>

        <div className="space-y-2">
          <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Company name
          </label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
            LinkedIn slug
          </label>
          <div className="flex items-center gap-1">
            <span className="rounded-l-md border border-r-0 border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
              linkedin.com/company/
            </span>
            <Input
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              className="rounded-l-none"
              placeholder="razorpay"
            />
          </div>
          {job.company_slug_suggestion && slug !== job.company_slug_suggestion && (
            <p className="text-xs text-slate-400">
              Suggestion based on company name:{" "}
              <button
                onClick={() => setSlug(job.company_slug_suggestion!)}
                className="font-mono text-indigo-600 hover:underline"
              >
                {job.company_slug_suggestion}
              </button>
            </p>
          )}
        </div>

        {confirm.isError && (
          <div className="rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">
            Couldn't confirm: {(confirm.error as Error).message}
          </div>
        )}

        <div className="flex justify-end">
          <Button onClick={() => confirm.mutate()} loading={confirm.isPending} disabled={!slug.trim()}>
            Find recruiters
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
