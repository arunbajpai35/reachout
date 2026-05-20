import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { Button, Card, CardBody, Textarea, Badge } from "@/components/ui";
import { ArrowRight, Link2 } from "lucide-react";

export default function HomePage() {
  const [value, setValue] = useState("");
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const isUrl = /^https?:\/\//i.test(value.trim());
  const inputType = value.trim().length === 0 ? null : isUrl ? "url" : "text";

  const create = useMutation({
    mutationFn: () => {
      const trimmed = value.trim();
      if (isUrl) return api.jobs.create({ url: trimmed });
      return api.jobs.create({ text: trimmed });
    },
    onSuccess: (job) => navigate(`/jobs/${job.id}`),
    onError: (e: ApiError) => setError(e.message),
  });

  const ready = inputType === "url" || (inputType === "text" && value.trim().length >= 50);

  return (
    <div className="mx-auto max-w-2xl pt-10">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
          Find the right recruiters,
          <br />
          <span className="text-indigo-600">draft messages that don't sound like a robot.</span>
        </h1>
        <p className="mt-3 text-sm text-slate-500">
          Paste a job URL or the JD text. ReachOut handles the rest.
        </p>
      </div>

      <Card>
        <CardBody>
          <Textarea
            autoFocus
            placeholder="https://boards.greenhouse.io/...   or paste the JD text here"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setError(null);
            }}
            rows={6}
            className="resize-none border-0 p-0 text-base focus:ring-0"
          />
          <div className="mt-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              {inputType === "url" && (
                <Badge tone="indigo">
                  <Link2 className="mr-1 h-3 w-3" />
                  url detected
                </Badge>
              )}
              {inputType === "text" && (
                <Badge tone="slate">
                  {value.trim().length} chars{value.trim().length < 50 && " (50+ needed)"}
                </Badge>
              )}
              <span className="text-slate-400">
                Supported: Greenhouse, Lever, raw JD text. LinkedIn URLs: paste the text instead.
              </span>
            </div>
            <Button
              onClick={() => create.mutate()}
              disabled={!ready}
              loading={create.isPending}
            >
              Analyze
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardBody>
      </Card>

      {error && (
        <div className="mt-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}
    </div>
  );
}
