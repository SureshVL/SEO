"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, Loader2, Send, Sparkles, X } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { copilotChat, type CopilotResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  actionResult?: CopilotResponse["action_result"];
}

const STARTERS = [
  "Where do I start?",
  "Audit my site",
  "Check my rankings",
  "What's losing traffic?",
];

export function CopilotWidget() {
  const router = useRouter();
  const { apiKey, businessProfile } = useAppStore();
  const projectId = businessProfile?.projectId || "";
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs, busy]);

  async function send(text: string) {
    const content = text.trim();
    if (!content || busy) return;
    setInput("");
    const nextMsgs: ChatMsg[] = [...msgs, { role: "user", content }];
    setMsgs(nextMsgs);
    setBusy(true);
    try {
      const history = nextMsgs.slice(-8).map(({ role, content }) => ({ role, content }));
      const res = await copilotChat(history, projectId, apiKey);
      setMsgs(m => [...m, { role: "assistant", content: res.reply, actionResult: res.action_result }]);
      if (res.action?.type === "navigate" && res.action.params?.path?.startsWith("/dashboard")) {
        setTimeout(() => router.push(res.action.params.path), 600);
      }
    } catch (err: any) {
      setMsgs(m => [...m, { role: "assistant", content: err?.message || "Something went wrong — try again." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {/* Launcher */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Open OMNI-RANK Copilot"
          className="fixed bottom-6 right-6 z-50 w-13 h-13 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-105"
          style={{ width: 52, height: 52, background: "linear-gradient(135deg, #8B5CF6, #EC4899)" }}
        >
          <Sparkles className="w-5 h-5 text-white" />
        </button>
      )}

      {/* Panel */}
      {open && (
        <div
          className="fixed bottom-6 right-6 z-50 w-[380px] max-w-[calc(100vw-3rem)] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
          style={{ background: "var(--bg-secondary, #18181b)", border: "1px solid var(--border, #3f3f46)", height: 520 }}
        >
          <div
            className="px-4 py-3 flex items-center justify-between shrink-0"
            style={{ background: "linear-gradient(135deg, #8B5CF622, #EC489922)", borderBottom: "1px solid var(--border, #3f3f46)" }}
          >
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4" style={{ color: "#8B5CF6" }} />
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary, #fafafa)" }}>OMNI-RANK Copilot</span>
            </div>
            <button onClick={() => setOpen(false)} aria-label="Close copilot" className="opacity-60 hover:opacity-100">
              <X className="w-4 h-4" style={{ color: "var(--text-primary, #fafafa)" }} />
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
            {msgs.length === 0 && (
              <div className="space-y-3">
                <p className="text-xs" style={{ color: "var(--text-muted, #71717a)" }}>
                  Ask anything about SEO or this product — or tell me to run something for you.
                  I answer in your language.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {STARTERS.map(s => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="px-2.5 py-1 rounded-full text-[11px] transition-colors hover:border-violet-500/60"
                      style={{ background: "var(--bg-card, #27272a)", border: "1px solid var(--border, #3f3f46)", color: "var(--text-secondary, #d4d4d8)" }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {msgs.map((m, i) => (
              <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <div
                  className="max-w-[85%] rounded-xl px-3 py-2 text-[13px] leading-relaxed whitespace-pre-wrap"
                  style={m.role === "user"
                    ? { background: "#8B5CF6", color: "white" }
                    : { background: "var(--bg-card, #27272a)", border: "1px solid var(--border, #3f3f46)", color: "var(--text-secondary, #e4e4e7)" }}
                >
                  {m.content}
                  {m.actionResult && (
                    <div
                      className="mt-2 pt-2 text-[12px]"
                      style={{ borderTop: "1px solid var(--border, #3f3f46)" }}
                    >
                      <span className={cn(
                        "font-semibold mr-1",
                        m.actionResult.status === "completed" ? "text-emerald-400"
                          : m.actionResult.status === "failed" ? "text-rose-400" : "text-amber-400",
                      )}>
                        {m.actionResult.status === "completed" ? "✓ Done:" : m.actionResult.status === "failed" ? "✗ Failed:" : "◌ Skipped:"}
                      </span>
                      {m.actionResult.detail}
                      {m.actionResult.data?.link && (
                        <button
                          onClick={() => router.push(m.actionResult!.data!.link)}
                          className="block mt-1 font-semibold hover:underline"
                          style={{ color: "#8B5CF6" }}
                        >
                          View →
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {busy && (
              <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted, #71717a)" }}>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Working — audits can take ~20 seconds…
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); send(input); }}
            className="p-3 flex items-center gap-2 shrink-0"
            style={{ borderTop: "1px solid var(--border, #3f3f46)" }}
          >
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask or command…"
              className="flex-1 bg-transparent text-sm outline-none px-2 py-1.5 rounded-lg"
              style={{ border: "1px solid var(--border, #3f3f46)", color: "var(--text-primary, #fafafa)" }}
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              aria-label="Send"
              className="w-9 h-9 rounded-lg flex items-center justify-center disabled:opacity-40"
              style={{ background: "#8B5CF6" }}
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
