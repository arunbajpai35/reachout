import { useState } from "react";
import { Badge, Button } from "@/components/ui";
import { cn, copy } from "@/lib/cn";
import type { OutreachDraft, QualityReport } from "@/lib/api";
import { AlertCircle, Check, Copy, RotateCw, ShieldCheck } from "lucide-react";

export default function DraftCard({
  draft,
  label,
  onRegenerate,
  regenerating,
}: {
  draft: OutreachDraft;
  label: string;
  onRegenerate: () => void;
  regenerating: boolean;
}) {
  const [copied, setCopied] = useState<"subject" | "body" | "full" | null>(null);

  async function doCopy(text: string, mark: "subject" | "body" | "full") {
    if (await copy(text)) {
      setCopied(mark);
      setTimeout(() => setCopied(null), 1500);
    }
  }

  const fullText = draft.subject ? `Subject: ${draft.subject}\n\n${draft.body}` : draft.body;
  const words = draft.quality?.word_count ?? draft.body.trim().split(/\s+/).filter(Boolean).length;

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
        <div className="flex items-center gap-2 text-xs">
          <span className="font-medium text-slate-700">{label}</span>
          <span className="text-slate-400">· {words} words</span>
          {draft.quality && <QualityChip q={draft.quality} />}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={onRegenerate}
            loading={regenerating}
            title="Regenerate"
          >
            <RotateCw className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => doCopy(fullText, "full")}
            title="Copy all"
          >
            {copied === "full" ? (
              <Check className="h-3 w-3 text-emerald-600" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
          </Button>
        </div>
      </div>
      <div className="space-y-2 px-3 py-3">
        {draft.subject && (
          <div>
            <div className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">
              Subject
            </div>
            <button
              onClick={() => doCopy(draft.subject!, "subject")}
              className="block w-full rounded px-1 py-0.5 text-left text-sm font-medium text-slate-800 hover:bg-slate-50"
              title="Click to copy"
            >
              {draft.subject}
              {copied === "subject" && (
                <span className="ml-2 text-xs text-emerald-600">copied</span>
              )}
            </button>
          </div>
        )}
        <div>
          {draft.subject && (
            <div className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">
              Body
            </div>
          )}
          <button
            onClick={() => doCopy(draft.body, "body")}
            className="block w-full whitespace-pre-wrap rounded px-1 py-0.5 text-left text-sm leading-relaxed text-slate-700 hover:bg-slate-50"
            title="Click to copy"
          >
            {draft.body}
            {copied === "body" && (
              <span className="ml-2 text-xs text-emerald-600">copied</span>
            )}
          </button>
        </div>
      </div>
      {draft.quality && draft.quality.violations.length > 0 && (
        <div className="flex flex-wrap gap-1 border-t border-slate-100 bg-amber-50/50 px-3 py-1.5">
          {draft.quality.violations.map((v, i) => (
            <Badge key={i} tone={v.severity === "block" ? "rose" : "amber"}>
              {v.severity === "block" ? "✕" : "!"} {v.rule}
              {v.detail && v.rule !== v.detail && (
                <span className="ml-1 font-mono opacity-70">{v.detail}</span>
              )}
            </Badge>
          ))}
        </div>
      )}
      {(draft.model || draft.prompt_version || draft.tone) && (
        <div className="border-t border-slate-100 px-3 py-1.5 text-[10px] text-slate-400">
          {[
            draft.model,
            draft.prompt_version,
            draft.tone && `tone:${draft.tone}`,
            new Date(draft.created_at).toLocaleTimeString(),
          ]
            .filter(Boolean)
            .join(" · ")}
        </div>
      )}
    </div>
  );
}

function QualityChip({ q }: { q: QualityReport }) {
  const blocks = q.violations.filter((v) => v.severity === "block").length;
  const tier = blocks > 0 ? "rose" : q.score >= 0.85 ? "emerald" : "amber";
  const Icon = blocks > 0 ? AlertCircle : ShieldCheck;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium",
        tier === "emerald" && "bg-emerald-100 text-emerald-700",
        tier === "amber" && "bg-amber-100 text-amber-700",
        tier === "rose" && "bg-rose-100 text-rose-700",
      )}
      title={`avg ${q.avg_sentence_words}w/sentence, max ${q.max_sentence_words}`}
    >
      <Icon className="h-2.5 w-2.5" />
      q={q.score}
    </span>
  );
}
