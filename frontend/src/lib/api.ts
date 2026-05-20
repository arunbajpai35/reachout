// Typed API client. Hand-written rather than codegen -- backend surface is small
// and seeing the request/response shapes inline keeps changes obvious during MVP.

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let body: { error?: { code?: string; message?: string } } = {};
    try { body = await res.json(); } catch { /* non-json error */ }
    throw new ApiError(
      res.status,
      body.error?.code ?? "http_error",
      body.error?.message ?? res.statusText,
    );
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------- Types (mirror backend Pydantic schemas) ----------

export type JobStatus =
  | "pending"
  | "extracted"
  | "recruiters_pending"
  | "recruiters_found"
  | "failed";

export type ParsedJob = {
  title?: string | null;
  seniority?: string | null;
  yoe_min?: number | null;
  yoe_max?: number | null;
  location?: string | null;
  work_mode?: string | null;
  employment_type?: string | null;
  skills?: string[];
  tech_stack?: string[];
  responsibilities?: string[];
  compensation?: string | null;
  company_name?: string;
  team?: string | null;
};

export type JobCompany = {
  id: string;
  name: string;
  linkedin_slug: string | null;
  domain: string | null;
};

export type Job = {
  id: string;
  source_url: string;
  source: string | null;
  title: string | null;
  status: JobStatus;
  error: string | null;
  company: JobCompany | null;
  company_slug_suggestion: string | null;
  parsed: ParsedJob | null;
  created_at: string;
};

export type RecruiterContact = {
  kind: string;
  value: string;
  verified: boolean;
  source: string | null;
  confidence: number | null;
};

export type RankedRecruiter = {
  id: string;
  full_name: string;
  title: string | null;
  linkedin_url: string | null;
  location: string | null;
  source: string | null;
  score: number;
  rationale: string;
  contacts: RecruiterContact[];
  enriched_at: string | null;
  last_seen_at: string;
};

export type EnrichRecruiterResult = {
  recruiter_id: string;
  enriched_at: string | null;
  contacts: RecruiterContact[];
};

export type CandidateProject = {
  name: string;
  description: string;
  stack: string[];
};

export type Candidate = {
  id: string;
  summary: string | null;
  years_experience: number | null;
  target_role: string | null;
  skills: string[] | null;
  notable_projects: CandidateProject[] | null;
  resume_id: string | null;
  updated_at: string;
  created_at: string;
};

export type ParsedResumeFields = {
  summary: string | null;
  years_experience: number | null;
  target_role: string | null;
  skills: string[];
  notable_projects: CandidateProject[];
  extraction_notes: string;
};

export type ResumeParseResult = {
  resume_id: string;
  filename: string;
  raw_text_preview: string;
  parsed: ParsedResumeFields;
};

export type Channel = "recruiter_email" | "linkedin_dm" | "networking_intro";
export const ALL_CHANNELS: Channel[] = ["recruiter_email", "linkedin_dm", "networking_intro"];

export type Tone = "concise" | "technical" | "warm" | "founder-energy";
export const ALL_TONES: Tone[] = ["concise", "technical", "warm", "founder-energy"];

export type QualityViolation = {
  rule: string;
  detail: string;
  severity: "block" | "warn";
};

export type QualityReport = {
  channel: string;
  word_count: number;
  sentence_count: number;
  avg_sentence_words: number;
  max_sentence_words: number;
  score: number;
  violations: QualityViolation[];
};

export type OutreachDraft = {
  id: string;
  job_id: string;
  recruiter_id: string;
  channel: Channel;
  subject: string | null;
  body: string;
  status: string;
  model: string | null;
  prompt_version: string | null;
  tone: string | null;
  created_at: string;
  quality: QualityReport | null;
};

// ---------- Endpoints ----------

export const api = {
  jobs: {
    create: (input: { url?: string; text?: string }) =>
      request<Job>("/jobs", { method: "POST", body: JSON.stringify(input) }),
    get: (id: string) => request<Job>(`/jobs/${id}`),
    list: () => request<Job[]>("/jobs"),
    confirmCompany: (id: string, payload: { linkedin_slug: string; name?: string }) =>
      request<Job>(`/jobs/${id}/company`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    recruiters: (id: string) => request<RankedRecruiter[]>(`/jobs/${id}/recruiters`),
  },
  recruiters: {
    enrich: (id: string) =>
      request<EnrichRecruiterResult>(`/recruiters/${id}/enrich`, { method: "POST" }),
  },
  candidate: {
    get: () => request<Candidate | null>("/candidate"),
    upsert: (payload: Partial<Candidate>) =>
      request<Candidate>("/candidate", { method: "PUT", body: JSON.stringify(payload) }),
    uploadResume: async (file: File): Promise<ResumeParseResult> => {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${BASE}/candidate/resume`, { method: "POST", body: fd });
      if (!res.ok) {
        let body: { error?: { code?: string; message?: string } } = {};
        try { body = await res.json(); } catch { /* */ }
        throw new ApiError(
          res.status,
          body.error?.code ?? "http_error",
          body.error?.message ?? res.statusText,
        );
      }
      return res.json();
    },
  },
  outreach: {
    generate: (payload: {
      job_id: string;
      recruiter_id: string;
      channels?: Channel[];
      tone?: Tone;
    }) =>
      request<{ drafts: OutreachDraft[] }>("/outreach", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    regenerate: (id: string, tone?: Tone) =>
      request<{ drafts: OutreachDraft[] }>(
        `/outreach/${id}/regenerate${tone ? `?tone=${tone}` : ""}`,
        { method: "POST" },
      ),
    listForPair: (jobId: string, recruiterId: string) =>
      request<OutreachDraft[]>(`/outreach/by-pair/${jobId}/${recruiterId}`),
    evaluate: (payload: { channel: Channel; subject?: string | null; body: string }) =>
      request<{ quality: QualityReport }>("/outreach/evaluate", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
};
