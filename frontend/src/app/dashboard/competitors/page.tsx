"use client";

import { useState } from "react";
import { Eye, Loader2, RefreshCw, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CompetitorsPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [projectId, setProjectId] = useState("");
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);

  async function loadCompetitors() {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/projects/${projectId}/competitors/check`, { headers: { "X-API-KEY": apiKey } });
      // Also load existing competitor intel
      const intelRes = await fetch(`${API}/projects/${projectId}/content`, { headers: { "X-API-KEY": apiKey } });
    } catch {} finally { setLoading(false); }
  }

  async function triggerScan() {
    setScanning(true);
    try {
      const res = await fetch(`${API}/projects/${projectId}/competitors/check`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) toast.success("Competitor scan queued! Changes will be logged.");
      else toast.error("Failed to start scan");
    } catch { toast.error("Failed"); }
    finally { setScanning(false); }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2"><Eye className="w-6 h-6 text-coral-400" /> Competitor Monitor</h1>
        <p className="text-sm text-zinc-400 mt-1">Track competitor page changes, content updates, and entity shifts.</p>
      </div>

      <div className="card p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <input type="text" value={projectId} onChange={e => setProjectId(e.target.value)} className="input-field" placeholder="Project ID" />
          </div>
          <button onClick={triggerScan} disabled={!projectId || scanning} className="btn-primary flex items-center gap-2">
            {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Scan Competitors
          </button>
        </div>
      </div>

      <div className="card p-8 text-center">
        <Eye className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
        <h3 className="font-semibold text-lg mb-2">Competitor intelligence</h3>
        <p className="text-sm text-zinc-400 max-w-lg mx-auto mb-2">
          Competitors are automatically discovered when you run an AI Research job. 
          Their pages are scraped, entities extracted, and content profiles stored.
        </p>
        <p className="text-sm text-zinc-400 max-w-lg mx-auto">
          Use "Scan Competitors" to check for recent changes — new sections, 
          content expansions, entity shifts — and get AI-powered strategy recommendations.
        </p>
      </div>
    </div>
  );
}
