import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type CandidateProject, type ResumeParseResult } from "@/lib/api";
import { Badge, Button, Card, CardBody, CardHeader, Input, Spinner, Textarea } from "@/components/ui";
import { FileText, Info, Plus, Trash2, Upload, X } from "lucide-react";

type FormState = {
  summary: string;
  years_experience: string;
  target_role: string;
  skills: string;
  projects: CandidateProject[];
};

const EMPTY: FormState = {
  summary: "",
  years_experience: "",
  target_role: "",
  skills: "",
  projects: [],
};

export default function CandidatePage() {
  const qc = useQueryClient();
  const candidateQ = useQuery({ queryKey: ["candidate"], queryFn: () => api.candidate.get() });
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saved, setSaved] = useState(false);
  const [parseResult, setParseResult] = useState<ResumeParseResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  // Resume_id is set when the user uploads, persisted with save.
  const [pendingResumeId, setPendingResumeId] = useState<string | null>(null);

  useEffect(() => {
    if (candidateQ.data) {
      setForm({
        summary: candidateQ.data.summary ?? "",
        years_experience:
          candidateQ.data.years_experience != null ? String(candidateQ.data.years_experience) : "",
        target_role: candidateQ.data.target_role ?? "",
        skills: (candidateQ.data.skills ?? []).join(", "),
        projects: (candidateQ.data.notable_projects ?? []) as CandidateProject[],
      });
    }
  }, [candidateQ.data]);

  const save = useMutation({
    mutationFn: () =>
      api.candidate.upsert({
        summary: form.summary || null,
        years_experience: form.years_experience ? Number(form.years_experience) : null,
        target_role: form.target_role || null,
        skills: form.skills
          .split(",")
          .map((s) => s.trim().toLowerCase())
          .filter(Boolean),
        notable_projects: form.projects,
        ...(pendingResumeId ? { resume_id: pendingResumeId } : {}),
      } as Partial<typeof candidateQ.data> & object),
    onSuccess: (c) => {
      qc.setQueryData(["candidate"], c);
      setSaved(true);
      setPendingResumeId(null);
      setTimeout(() => setSaved(false), 1800);
    },
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.candidate.uploadResume(file),
    onSuccess: (res) => {
      setParseResult(res);
      setUploadError(null);
    },
    onError: (e: ApiError | Error) => {
      setUploadError(e instanceof ApiError ? e.message : e.message);
    },
  });

  function applyParsed() {
    if (!parseResult) return;
    const p = parseResult.parsed;
    setForm({
      summary: p.summary ?? "",
      years_experience: p.years_experience != null ? String(p.years_experience) : "",
      target_role: p.target_role ?? "",
      skills: p.skills.join(", "),
      projects: p.notable_projects,
    });
    setPendingResumeId(parseResult.resume_id);
    setParseResult(null);
  }

  if (candidateQ.isLoading) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-slate-500">
        <Spinner /> Loading profile…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">Your profile</h1>
        <p className="mt-1 text-sm text-slate-500">
          This is the context every outreach draft is grounded in. Sparse profile, sparse drafts.
        </p>
      </div>

      <div className="space-y-4">
        <ResumeUploadCard
          fileInputRef={fileInputRef}
          uploading={upload.isPending}
          error={uploadError}
          parseResult={parseResult}
          onPick={(f) => upload.mutate(f)}
          onApply={applyParsed}
          onDismiss={() => setParseResult(null)}
        />

        <Card>
          <CardHeader className="text-sm font-medium text-slate-700">Basics</CardHeader>
          <CardBody className="space-y-4">
            <Field label="Target role">
              <Input
                placeholder="Senior Backend Engineer (Payments)"
                value={form.target_role}
                onChange={(e) => setForm({ ...form, target_role: e.target.value })}
              />
            </Field>
            <Field label="Years of experience">
              <Input
                type="number"
                min={0}
                step={0.5}
                placeholder="4"
                value={form.years_experience}
                onChange={(e) => setForm({ ...form, years_experience: e.target.value })}
              />
            </Field>
            <Field
              label="One-line summary"
              hint="What you do, and who you build for. The model uses this as your voice."
            >
              <Textarea
                rows={3}
                placeholder="Backend engineer building payment infra at an Indian fintech. Strong on distributed systems and exactly-once semantics."
                value={form.summary}
                onChange={(e) => setForm({ ...form, summary: e.target.value })}
              />
            </Field>
            <Field
              label="Skills"
              hint="Comma-separated. Lowercase, canonical names (e.g. postgres, kafka, go)."
            >
              <Input
                placeholder="python, go, postgres, kafka, redis, kubernetes"
                value={form.skills}
                onChange={(e) => setForm({ ...form, skills: e.target.value })}
              />
              {form.skills && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {form.skills.split(",").map((s) => s.trim()).filter(Boolean).slice(0, 30).map((s) => (
                    <Badge key={s}>{s}</Badge>
                  ))}
                </div>
              )}
            </Field>
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <div className="text-sm font-medium text-slate-700">Notable projects</div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setForm({
                  ...form,
                  projects: [...form.projects, { name: "", description: "", stack: [] }],
                })
              }
            >
              <Plus className="h-3 w-3" /> Add
            </Button>
          </CardHeader>
          <CardBody className="space-y-3">
            {form.projects.length === 0 && (
              <p className="text-sm text-slate-500">
                Up to 3 specific things you've shipped. One real project beats a long resume.
              </p>
            )}
            {form.projects.map((p, idx) => (
              <ProjectRow
                key={idx}
                value={p}
                onChange={(np) => {
                  const next = [...form.projects];
                  next[idx] = np;
                  setForm({ ...form, projects: next });
                }}
                onRemove={() =>
                  setForm({
                    ...form,
                    projects: form.projects.filter((_, i) => i !== idx),
                  })
                }
              />
            ))}
          </CardBody>
        </Card>

        <div className="flex items-start gap-2 rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-500">
          <Info className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
          <span>
            Manual edits always win. Uploading a resume populates the form but doesn't save
            until you click Save.
          </span>
        </div>

        <div className="flex items-center justify-end gap-3">
          {saved && <span className="text-xs text-emerald-600">Saved</span>}
          <Button onClick={() => save.mutate()} loading={save.isPending}>
            Save profile
          </Button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </label>
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
      {children}
    </div>
  );
}

function ResumeUploadCard({
  fileInputRef,
  uploading,
  error,
  parseResult,
  onPick,
  onApply,
  onDismiss,
}: {
  fileInputRef: React.MutableRefObject<HTMLInputElement | null>;
  uploading: boolean;
  error: string | null;
  parseResult: ResumeParseResult | null;
  onPick: (file: File) => void;
  onApply: () => void;
  onDismiss: () => void;
}) {
  if (parseResult) {
    const p = parseResult.parsed;
    return (
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <FileText className="h-4 w-4 text-indigo-600" />
            Parsed: {parseResult.filename}
          </div>
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            <X className="h-3 w-3" />
          </Button>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
            <strong>Extraction notes:</strong> {p.extraction_notes || "—"}
          </div>

          <ReviewRow k="Target role">{p.target_role || <em className="text-slate-400">none stated in resume</em>}</ReviewRow>
          <ReviewRow k="Years of experience">
            {p.years_experience != null ? `${p.years_experience} years` : <em className="text-slate-400">not detected</em>}
          </ReviewRow>
          <ReviewRow k="Summary">{p.summary || <em className="text-slate-400">—</em>}</ReviewRow>
          <ReviewRow k="Skills">
            {p.skills.length === 0 ? (
              <em className="text-slate-400">none extracted</em>
            ) : (
              <div className="flex flex-wrap gap-1">
                {p.skills.map((s) => <Badge key={s}>{s}</Badge>)}
              </div>
            )}
          </ReviewRow>
          <ReviewRow k="Projects">
            <ul className="space-y-1 text-sm">
              {p.notable_projects.length === 0 && (
                <li><em className="text-slate-400">none extracted</em></li>
              )}
              {p.notable_projects.map((proj, i) => (
                <li key={i}>
                  <span className="font-medium">{proj.name}</span> — {proj.description}
                  {proj.stack.length > 0 && (
                    <span className="ml-1 text-xs text-slate-400">[{proj.stack.join(", ")}]</span>
                  )}
                </li>
              ))}
            </ul>
          </ReviewRow>

          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-400">
              Applying overwrites the form below. You can edit before saving.
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={onDismiss}>
                Discard
              </Button>
              <Button size="sm" onClick={onApply}>
                Apply to form
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardBody>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Upload className="h-4 w-4 text-indigo-600" />
              Upload your resume
            </div>
            <p className="mt-1 text-xs text-slate-500">
              PDF only, under 10 MB. We extract text deterministically, then ask GPT-4o to
              normalize it into your profile. The file isn't stored.
            </p>
          </div>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onPick(f);
                e.target.value = "";  // allow re-picking the same file
              }}
            />
            <Button
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              loading={uploading}
            >
              {uploading ? "Parsing…" : "Choose PDF"}
            </Button>
          </div>
        </div>
        {error && (
          <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</div>
        )}
      </CardBody>
    </Card>
  );
}

function ReviewRow({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[140px_1fr] gap-3 border-t border-slate-100 pt-2">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{k}</dt>
      <dd className="text-sm text-slate-700">{children}</dd>
    </div>
  );
}

function ProjectRow({
  value,
  onChange,
  onRemove,
}: {
  value: CandidateProject;
  onChange: (v: CandidateProject) => void;
  onRemove: () => void;
}) {
  return (
    <div className="space-y-2 rounded-lg border border-slate-100 p-3">
      <div className="flex items-center gap-2">
        <Input
          placeholder="Project name"
          value={value.name}
          onChange={(e) => onChange({ ...value, name: e.target.value })}
        />
        <Button variant="ghost" size="sm" onClick={onRemove}>
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
      <Textarea
        rows={2}
        placeholder="What did you build, what changed because of it? One or two sentences."
        value={value.description}
        onChange={(e) => onChange({ ...value, description: e.target.value })}
      />
      <Input
        placeholder="Stack: go, postgres, kafka"
        value={value.stack.join(", ")}
        onChange={(e) =>
          onChange({
            ...value,
            stack: e.target.value
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
          })
        }
      />
    </div>
  );
}
