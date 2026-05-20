import { useState } from "react";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui";
import type { ParsedJob } from "@/lib/api";
import { ChevronDown, ChevronRight } from "lucide-react";

function yoeLabel(p: ParsedJob): string | null {
  if (p.yoe_min == null && p.yoe_max == null) return null;
  if (p.yoe_max == null) return `${p.yoe_min}+ yrs`;
  return `${p.yoe_min}–${p.yoe_max} yrs`;
}

export default function ExtractedRoleCard({ parsed }: { parsed: ParsedJob }) {
  const [open, setOpen] = useState(true);
  const yoe = yoeLabel(parsed);

  return (
    <Card>
      <CardHeader>
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-center justify-between text-sm font-medium text-slate-700"
        >
          <span>Extracted role detail</span>
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
      </CardHeader>
      {open && (
        <CardBody className="space-y-4">
          <div className="flex flex-wrap gap-2 text-xs">
            {parsed.seniority && parsed.seniority !== "unknown" && (
              <Badge tone="indigo">{parsed.seniority}</Badge>
            )}
            {yoe && <Badge>{yoe}</Badge>}
            {parsed.work_mode && parsed.work_mode !== "unknown" && (
              <Badge tone="blue">{parsed.work_mode}</Badge>
            )}
            {parsed.location && <Badge>{parsed.location}</Badge>}
            {parsed.employment_type && parsed.employment_type !== "unknown" && (
              <Badge tone="slate">{parsed.employment_type}</Badge>
            )}
          </div>

          {parsed.tech_stack && parsed.tech_stack.length > 0 && (
            <Detail label="Tech stack">
              <SkillChips items={parsed.tech_stack} tone="indigo" />
            </Detail>
          )}

          {parsed.skills && parsed.skills.length > 0 && (
            <Detail label="Skills">
              <SkillChips items={parsed.skills} />
            </Detail>
          )}

          {parsed.responsibilities && parsed.responsibilities.length > 0 && (
            <Detail label="Responsibilities">
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                {parsed.responsibilities.slice(0, 5).map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </Detail>
          )}

          {parsed.compensation && (
            <Detail label="Compensation">
              <span className="text-sm text-slate-700">{parsed.compensation}</span>
            </Detail>
          )}
        </CardBody>
      )}
    </Card>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      {children}
    </div>
  );
}

function SkillChips({ items, tone }: { items: string[]; tone?: "indigo" | "slate" }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((s) => (
        <Badge key={s} tone={tone ?? "slate"}>
          {s}
        </Badge>
      ))}
    </div>
  );
}
