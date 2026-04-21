"use client";

import { useCallback, useEffect, useState } from "react";
import { Calendar, CheckCircle2, CircleDashed, Loader2, Play, XCircle } from "lucide-react";
import { useAppStore } from "@/lib/store";
import {
  getWorkflowSchedule,
  listProjects,
  listWorkflowRuns,
  runWorkflow,
  type WorkflowRun,
  type WorkflowSchedule,
} from "@/lib/api";
import { toast } from "sonner";

const TASK_LABELS: Record<string, string> = {
  technical_audit: "Technical audit",
  schema_review: "Schema markup review",
  content_brief: "Content brief",
  content_draft_score: "Score pending drafts",
  rank_check: "Rank check",
  keyword_expansion: "Keyword expansion",
  link_outreach: "Link outreach follow-ups",
  monthly_report: "Monthly report",
};

export default function WorkflowPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState(businessProfile?.projectId || "");
  const [schedule, setSchedule] = useState<WorkflowSchedule | null>(null);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listProjects(apiKey).then(setProjects).catch(() => {});
  }, [apiKey]);

  const load = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [sched, hist] = await Promise.all([
        getWorkflowSchedule(projectId, apiKey),
        listWorkflowRuns(projectId, apiKey, 10).catch(() => ({ runs: [] })),
      ]);
      setSchedule(sched);
      setRuns(hist.runs as any);
    } catch (err: any) {
      toast.error(err.message || "Failed to load workflow");
    } finally {
      setLoading(false);
    }
  }, [projectId, apiKey]);

  useEffect(() => { load(); }, [load]);

  async function handleRun() {
    if (!projectId) {
      toast.error("Select a project");
      return;
    }
    setRunning(true);
    try {
      const run = await runWorkflow(projectId, apiKey);
      toast.success(
        `${run.week_label}: ${run.completed} done, ${run.skipped} skipped, ${run.failed} failed`,
      );
      await load();
    } catch (err: any) {
      toast.error(err.message || "Run failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Calendar className="w-6 h-6 text-sky-400" /> Monthly Workflow
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          The Week 1-4 SEO cadence: technical → content → rankings → links & report.
          Runs automatically on cron; manual trigger available below.
        </p>
      </div>

      <div className="card p-4 mb-6">
        <label className="text-xs text-zinc-500 uppercase tracking-wider block mb-1">
          Project
        </label>
        <select
          value={projectId}
          onChange={e => setProjectId(e.target.value)}
          className="input-field"
        >
          <option value="">Select a project…</option>
          {projects.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="card p-10 flex items-center justify-center text-zinc-400">
          <Loader2 className="w-5 h-5 animate-spin" />
        </div>
      ) : schedule ? (
        <>
          <div className="card p-6 mb-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  This week
                </div>
                <div className="text-xl font-semibold text-zinc-100">
                  {schedule.week_label}
                </div>
                <div className="text-xs text-zinc-500 mt-1">
                  As of {new Date(schedule.as_of).toLocaleString()}
                </div>
              </div>
              <button
                onClick={handleRun}
                disabled={running || !projectId}
                className="btn-primary flex items-center gap-2"
              >
                {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Run now
              </button>
            </div>

            <div className="mt-5 space-y-2">
              {schedule.tasks.map(t => (
                <div
                  key={t}
                  className="flex items-center gap-3 p-3 rounded border border-zinc-800 bg-zinc-900/30"
                >
                  <CircleDashed className="w-4 h-4 text-sky-300" />
                  <span className="text-sm text-zinc-200">{TASK_LABELS[t] || t}</span>
                </div>
              ))}
              {schedule.tasks.length === 0 && (
                <div className="text-sm text-zinc-500">
                  No tasks scheduled for this week.
                </div>
              )}
            </div>
          </div>

          <div className="card p-0 overflow-hidden">
            <div className="px-6 py-4 border-b border-zinc-800">
              <h3 className="font-semibold text-zinc-200">Recent runs</h3>
            </div>
            {runs.length === 0 ? (
              <div className="p-6 text-sm text-zinc-500">
                No runs recorded yet. Hit <em>Run now</em> or wait for the next scheduled cycle.
              </div>
            ) : (
              <div className="divide-y divide-zinc-800">
                {runs.map((r, i) => (
                  <div key={i} className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-sm font-semibold text-zinc-200">{r.week_label}</div>
                      <div className="text-xs text-zinc-500">
                        {r.started_at && new Date(r.started_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs mb-2">
                      <Pill tone="good" icon={<CheckCircle2 className="w-3 h-3" />}>
                        {r.completed} done
                      </Pill>
                      <Pill tone="warn" icon={<CircleDashed className="w-3 h-3" />}>
                        {r.skipped} skipped
                      </Pill>
                      <Pill tone="bad" icon={<XCircle className="w-3 h-3" />}>
                        {r.failed} failed
                      </Pill>
                    </div>
                    <div className="space-y-1">
                      {r.tasks?.map((t, j) => (
                        <div key={j} className="flex items-start gap-2 text-xs">
                          <StatusIcon status={t.status} />
                          <div className="flex-1">
                            <span className="text-zinc-300">{TASK_LABELS[t.name] || t.name}</span>
                            {t.detail && (
                              <span className="text-zinc-500"> · {t.detail}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="card p-10 text-center text-sm text-zinc-500">
          Select a project to see its workflow.
        </div>
      )}
    </div>
  );
}

function Pill({
  tone, icon, children,
}: {
  tone: "good" | "warn" | "bad"; icon: React.ReactNode; children: React.ReactNode;
}) {
  const color =
    tone === "good" ? "bg-emerald-500/10 text-emerald-300" :
    tone === "warn" ? "bg-amber-500/10 text-amber-300" :
    "bg-red-500/10 text-red-300";
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded ${color}`}>
      {icon}{children}
    </span>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="w-3 h-3 text-emerald-400 mt-0.5" />;
  if (status === "failed") return <XCircle className="w-3 h-3 text-red-400 mt-0.5" />;
  return <CircleDashed className="w-3 h-3 text-amber-400 mt-0.5" />;
}
