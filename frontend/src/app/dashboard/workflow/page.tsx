"use client";

import { useCallback, useEffect, useState } from "react";
import { Calendar, CheckCircle2, CircleDashed, FolderOpen, Loader2, Play, XCircle } from "lucide-react";
import { useAppStore } from "@/lib/store";
import {
  getWorkflowSchedule,
  listProjects,
  listWorkflowRuns,
  runWorkflow,
  type WorkflowRun,
  type WorkflowSchedule,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { toast } from "sonner";

const TASK_LABELS: Record<string, string> = {
  technical_audit: "Technical audit",
  schema_review: "Schema markup review",
  content_brief: "Content brief",
  content_draft_score: "Score pending drafts",
  content_refresh: "Content decay check",
  rank_check: "Rank check",
  keyword_expansion: "Keyword expansion",
  link_outreach: "Link outreach follow-ups",
  monthly_report: "Monthly report",
};

const WEEK_COLORS: Record<number, string> = {
  1: "#A3E635", // lime — technical
  2: "#F97316", // orange — content
  3: "#EC4899", // magenta — rankings
  4: "#22D3EE", // cyan — links & report
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

  const weekAccent = schedule ? WEEK_COLORS[schedule.week] || "#8B5CF6" : "#FACC15";

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Monthly Workflow"
        subtitle="The Week 1-4 SEO cadence — technical → content → rankings → links & report. Runs automatically on cron."
        icon={Calendar}
        accent="#FACC15"
        actions={
          <Select
            icon={FolderOpen}
            accent="#8B5CF6"
            placeholder="Select a project…"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            options={projects.map((p) => ({ value: p.id, label: p.name }))}
            widthClass="min-w-[260px]"
          />
        }
      />

      {loading ? (
        <div className="card p-10 flex items-center justify-center" style={{ color: "var(--text-muted)" }}>
          <Loader2 className="w-5 h-5 animate-spin" />
        </div>
      ) : schedule ? (
        <>
          {/* Hero week card */}
          <div
            className="relative rounded-2xl p-6 mb-6 overflow-hidden"
            style={{
              background: `linear-gradient(135deg, ${weekAccent}1f, ${weekAccent}08)`,
              border: `1px solid ${weekAccent}55`,
            }}
          >
            <div className="absolute top-0 left-0 right-0 h-1" style={{ background: weekAccent }} />
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] font-semibold mb-2" style={{ color: weekAccent }}>
                  This week
                </div>
                <div className="flex items-baseline gap-3">
                  <div className="text-5xl font-extrabold tracking-tight" style={{ color: weekAccent }}>
                    W{schedule.week}
                  </div>
                  <div className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
                    {schedule.week_label.replace(/^Week \d+ — /, "")}
                  </div>
                </div>
                <div className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
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

            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-2">
              {schedule.tasks.map((t) => (
                <div
                  key={t}
                  className="flex items-center gap-3 p-3 rounded-xl transition-colors"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                >
                  <span
                    className="w-7 h-7 rounded-lg flex items-center justify-center"
                    style={{ background: `${weekAccent}22`, color: weekAccent }}
                  >
                    <CircleDashed className="w-4 h-4" />
                  </span>
                  <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                    {TASK_LABELS[t] || t}
                  </span>
                </div>
              ))}
              {schedule.tasks.length === 0 && (
                <div className="text-sm" style={{ color: "var(--text-muted)" }}>
                  No tasks scheduled for this week.
                </div>
              )}
            </div>
          </div>

          {/* History */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid var(--border)" }}>
              <h3 className="font-semibold" style={{ color: "var(--text-primary)" }}>Recent runs</h3>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>{runs.length} total</span>
            </div>
            {runs.length === 0 ? (
              <div className="p-8 text-sm text-center" style={{ color: "var(--text-muted)" }}>
                No runs recorded yet. Hit <em>Run now</em> or wait for the next scheduled cycle.
              </div>
            ) : (
              <div>
                {runs.map((r, i) => {
                  const accent = WEEK_COLORS[r.week] || "#8B5CF6";
                  return (
                    <div key={i} className="p-5" style={{ borderTop: i ? "1px solid var(--border)" : undefined }}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span
                            className="px-2 py-0.5 rounded-md text-[11px] font-bold text-white"
                            style={{ background: accent }}
                          >
                            W{r.week}
                          </span>
                          <div className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                            {r.week_label.replace(/^Week \d+ — /, "")}
                          </div>
                        </div>
                        <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                          {r.started_at && new Date(r.started_at).toLocaleString()}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mb-3 flex-wrap">
                        <Pill tone="good" icon={<CheckCircle2 className="w-3 h-3" />}>{r.completed} done</Pill>
                        <Pill tone="warn" icon={<CircleDashed className="w-3 h-3" />}>{r.skipped} skipped</Pill>
                        <Pill tone="bad" icon={<XCircle className="w-3 h-3" />}>{r.failed} failed</Pill>
                      </div>
                      <div className="space-y-1.5">
                        {r.tasks?.map((t, j) => (
                          <div key={j} className="flex items-start gap-2 text-xs">
                            <StatusIcon status={t.status} />
                            <div className="flex-1">
                              <span style={{ color: "var(--text-secondary)" }}>{TASK_LABELS[t.name] || t.name}</span>
                              {t.detail && (
                                <span style={{ color: "var(--text-muted)" }}> · {t.detail}</span>
                              )}
                              <TaskData data={t.data as any} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="card p-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          Select a project to see its workflow.
        </div>
      )}
    </div>
  );
}

function Pill({ tone, icon, children }: {
  tone: "good" | "warn" | "bad"; icon: React.ReactNode; children: React.ReactNode;
}) {
  const cls = tone === "good" ? "badge-success" : tone === "warn" ? "badge-warning" : "badge-error";
  return (
    <span className={`${cls} inline-flex items-center gap-1`}>
      {icon}{children}
    </span>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="w-3.5 h-3.5 mt-0.5" style={{ color: "#A3E635" }} />;
  if (status === "failed") return <XCircle className="w-3.5 h-3.5 mt-0.5" style={{ color: "#F43F5E" }} />;
  return <CircleDashed className="w-3.5 h-3.5 mt-0.5" style={{ color: "#FACC15" }} />;
}

/** Render the quantified artifacts a task returned: rank movers, keyword
 *  candidates, draft scores, and the deep link to the page that owns them. */
function TaskData({ data }: { data?: Record<string, any> }) {
  if (!data || Object.keys(data).length === 0) return null;
  const movers: Array<{ keyword: string; from: number | null; to: number | null }> = data.movers || [];
  const candidates: string[] = data.candidates || [];
  const scores: Array<{ title: string; score: number }> = data.scores || [];
  const hasChips = movers.length > 0 || candidates.length > 0 || scores.length > 0;
  if (!hasChips && !data.link) return null;
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
      {movers.map((m, i) => {
        const up = (m.from ?? 99) > (m.to ?? 99);
        return (
          <span
            key={`m${i}`}
            className="px-1.5 py-0.5 rounded-md border text-[10px] font-medium"
            style={{
              color: up ? "#A3E635" : "#F43F5E",
              borderColor: up ? "#A3E63544" : "#F43F5E44",
              background: up ? "#A3E6350d" : "#F43F5E0d",
            }}
          >
            {m.keyword} {m.from ?? "—"}→{m.to ?? "—"} {up ? "↑" : "↓"}
          </span>
        );
      })}
      {candidates.map((c, i) => (
        <span
          key={`c${i}`}
          className="px-1.5 py-0.5 rounded-md text-[10px]"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
        >
          {c}
        </span>
      ))}
      {scores.map((s, i) => (
        <span
          key={`s${i}`}
          className="px-1.5 py-0.5 rounded-md text-[10px]"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
        >
          {s.title?.slice(0, 40)}: {s.score}/100
        </span>
      ))}
      {data.link && (
        <a
          href={data.link}
          className="text-[10px] font-semibold hover:underline"
          style={{ color: "#8B5CF6" }}
        >
          View →
        </a>
      )}
    </div>
  );
}
