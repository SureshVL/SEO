"use client";

import { useEffect, useState } from "react";
import {
  BarChart3, Check, ExternalLink, Loader2, RefreshCw,
  Settings, Shield, Unlink, Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── helpers ──────────────────────────────────────────────────────────────────
async function getAuthUrl(service: "ga4" | "gsc", projectId: string, apiKey: string) {
  const res = await fetch(`${API}/analytics/${service}/auth-url?project_id=${projectId}`, {
    headers: { "X-API-KEY": apiKey },
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()).auth_url as string;
}

async function exchangeCode(code: string, service: string, projectId: string, apiKey: string) {
  const res = await fetch(`${API}/analytics/exchange-token`, {
    method: "POST",
    headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify({ code, service, project_id: projectId }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ─── OAuth callback handler (reads ?code & ?state from URL) ──────────────────
function useOAuthCallback() {
  const {
    apiKey, businessProfile,
    setGa4Connected, setGscConnected,
  } = useAppStore();
  const [exchanging, setExchanging] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state") || "";
    if (!code) return;

    const service = state.startsWith("gsc") ? "gsc" : "ga4";
    const projectId = state.split(":")[1] || businessProfile?.projectId || "";

    setExchanging(true);
    exchangeCode(code, service, projectId, apiKey)
      .then((data) => {
        const token = data.access_token || "";
        if (service === "ga4") {
          const firstProp = data.properties?.[0]?.property_id || "";
          setGa4Connected(true, firstProp, token);
          toast.success(`Google Analytics 4 connected${data.email ? " · " + data.email : ""}`);
        } else {
          const firstSite = data.properties?.[0]?.site_url || "";
          setGscConnected(true, firstSite, token);
          toast.success(`Search Console connected${data.email ? " · " + data.email : ""}`);
        }
        // Clean URL
        window.history.replaceState({}, "", window.location.pathname);
      })
      .catch((err) => toast.error("OAuth failed: " + err.message))
      .finally(() => setExchanging(false));
  }, []);

  return exchanging;
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function SettingsPage() {
  const {
    apiKey, setApiKey,
    businessProfile,
    ga4Connected, ga4PropertyId, setGa4Connected,
    gscConnected, gscSiteUrl, setGscConnected,
  } = useAppStore();

  const [localKey, setLocalKey] = useState(apiKey);
  const [connectingGa4, setConnectingGa4] = useState(false);
  const [connectingGsc, setConnectingGsc] = useState(false);
  const [ga4Metrics, setGa4Metrics] = useState<any>(null);
  const [gscMetrics, setGscMetrics] = useState<any>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(false);

  const exchanging = useOAuthCallback();

  // ── handlers ──────────────────────────────────────────────────────────────
  async function connectGa4() {
    setConnectingGa4(true);
    try {
      const url = await getAuthUrl("ga4", businessProfile?.projectId || "", apiKey);
      window.location.href = url;
    } catch (err: any) {
      toast.error(err.message || "Failed to get GA4 auth URL");
      setConnectingGa4(false);
    }
  }

  async function connectGsc() {
    setConnectingGsc(true);
    try {
      const url = await getAuthUrl("gsc", businessProfile?.projectId || "", apiKey);
      window.location.href = url;
    } catch (err: any) {
      toast.error(err.message || "Failed to get GSC auth URL");
      setConnectingGsc(false);
    }
  }

  async function loadMetrics() {
    if (!ga4Connected && !gscConnected) return;
    setLoadingMetrics(true);
    try {
      // These would use the stored refresh token in production.
      // For now we show that the connection is live and metrics are available.
      toast.info("Metrics fetch requires server-side token storage — connecting live data in Phase 2.");
    } finally {
      setLoadingMetrics(false);
    }
  }

  function disconnectGa4() {
    setGa4Connected(false, "");
    setGa4Metrics(null);
    toast.success("Google Analytics 4 disconnected");
  }

  function disconnectGsc() {
    setGscConnected(false, "");
    setGscMetrics(null);
    toast.success("Search Console disconnected");
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="w-6 h-6 text-zinc-400" /> Settings
        </h1>
        <p className="text-sm text-zinc-400 mt-1">Manage your account, API keys, and integrations.</p>
      </div>

      {exchanging && (
        <div className="card p-4 mb-6 flex items-center gap-3 border-brand-500/30 bg-brand-500/5">
          <Loader2 className="w-4 h-4 animate-spin text-brand-400" />
          <span className="text-sm text-brand-300">Completing OAuth connection…</span>
        </div>
      )}

      <div className="space-y-6 max-w-2xl">

        {/* API Key */}
        <div className="card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-zinc-400" /> API Keys
          </h3>
          <div className="space-y-4">
            <div>
              <label className="label">Orchestrator API Key</label>
              <div className="flex gap-2">
                <input
                  type="password"
                  className="input-field flex-1"
                  value={localKey}
                  onChange={e => setLocalKey(e.target.value)}
                />
                <button
                  onClick={() => { setApiKey(localKey); toast.success("API key saved"); }}
                  className="btn-primary px-4 text-sm"
                >
                  Save
                </button>
              </div>
              <p className="text-xs text-zinc-500 mt-1">Used to authenticate with the OMNI-RANK backend.</p>
            </div>
          </div>
        </div>

        {/* Business Profile summary */}
        {businessProfile && (
          <div className="card p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Zap className="w-4 h-4 text-brand-400" /> Business Profile
            </h3>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Website</dt>
                <dd className="text-zinc-200 truncate">{businessProfile.websiteUrl}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500 uppercase tracking-wider mb-1">City</dt>
                <dd className="text-zinc-200">{businessProfile.city || "All India"}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Business Type</dt>
                <dd className="text-zinc-200">{businessProfile.businessTypeLabel}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Keywords</dt>
                <dd className="text-zinc-200">{businessProfile.keywords.slice(0, 3).join(", ")}{businessProfile.keywords.length > 3 ? "…" : ""}</dd>
              </div>
            </dl>
            <p className="text-xs text-zinc-600 mt-3">
              All tools auto-fill from this profile. Re-run onboarding to change.
            </p>
          </div>
        )}

        {/* GA4 / GSC integrations */}
        <div className="card p-6">
          <h3 className="font-semibold mb-1 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-emerald-400" /> Revenue Attribution
          </h3>
          <p className="text-xs text-zinc-500 mb-5">
            Connect GA4 and Search Console to attribute organic sessions, conversions, and revenue to OMNI-RANK's SEO work.
          </p>

          <div className="space-y-4">
            {/* GA4 */}
            <div className={cn(
              "flex items-center justify-between p-4 rounded-xl border transition-all",
              ga4Connected
                ? "bg-emerald-500/5 border-emerald-500/20"
                : "bg-zinc-800/30 border-zinc-700/30"
            )}>
              <div className="flex items-center gap-3">
                <div className={cn(
                  "w-9 h-9 rounded-lg flex items-center justify-center text-base",
                  ga4Connected ? "bg-emerald-500/15" : "bg-zinc-700/40"
                )}>📊</div>
                <div>
                  <div className="text-sm font-medium flex items-center gap-2">
                    Google Analytics 4
                    {ga4Connected && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                  </div>
                  {ga4Connected && ga4PropertyId ? (
                    <div className="text-xs text-emerald-400">Property {ga4PropertyId} connected</div>
                  ) : (
                    <div className="text-xs text-zinc-500">Sessions · Revenue · Conversions</div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {ga4Connected ? (
                  <>
                    <button
                      onClick={loadMetrics}
                      disabled={loadingMetrics}
                      className="btn-ghost text-xs flex items-center gap-1"
                    >
                      {loadingMetrics ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                      Refresh
                    </button>
                    <button onClick={disconnectGa4} className="btn-ghost text-xs text-red-400 flex items-center gap-1">
                      <Unlink className="w-3 h-3" /> Disconnect
                    </button>
                  </>
                ) : (
                  <button
                    onClick={connectGa4}
                    disabled={connectingGa4}
                    className="btn-primary text-sm flex items-center gap-2 px-4"
                  >
                    {connectingGa4
                      ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Connecting…</>
                      : <><ExternalLink className="w-3.5 h-3.5" /> Connect</>
                    }
                  </button>
                )}
              </div>
            </div>

            {/* GSC */}
            <div className={cn(
              "flex items-center justify-between p-4 rounded-xl border transition-all",
              gscConnected
                ? "bg-emerald-500/5 border-emerald-500/20"
                : "bg-zinc-800/30 border-zinc-700/30"
            )}>
              <div className="flex items-center gap-3">
                <div className={cn(
                  "w-9 h-9 rounded-lg flex items-center justify-center text-base",
                  gscConnected ? "bg-emerald-500/15" : "bg-zinc-700/40"
                )}>🔍</div>
                <div>
                  <div className="text-sm font-medium flex items-center gap-2">
                    Google Search Console
                    {gscConnected && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                  </div>
                  {gscConnected && gscSiteUrl ? (
                    <div className="text-xs text-emerald-400">{gscSiteUrl}</div>
                  ) : (
                    <div className="text-xs text-zinc-500">Clicks · Impressions · CTR · Position</div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {gscConnected ? (
                  <>
                    <button
                      onClick={loadMetrics}
                      disabled={loadingMetrics}
                      className="btn-ghost text-xs flex items-center gap-1"
                    >
                      {loadingMetrics ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                      Refresh
                    </button>
                    <button onClick={disconnectGsc} className="btn-ghost text-xs text-red-400 flex items-center gap-1">
                      <Unlink className="w-3 h-3" /> Disconnect
                    </button>
                  </>
                ) : (
                  <button
                    onClick={connectGsc}
                    disabled={connectingGsc}
                    className="btn-primary text-sm flex items-center gap-2 px-4"
                  >
                    {connectingGsc
                      ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Connecting…</>
                      : <><ExternalLink className="w-3.5 h-3.5" /> Connect</>
                    }
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Revenue attribution summary widget */}
          {(ga4Connected || gscConnected) && (
            <div className="mt-5 p-4 rounded-lg bg-zinc-900/60 border border-zinc-700/30">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3">Attribution Overview</div>
              <div className="grid grid-cols-3 gap-4 text-center">
                {[
                  { label: "Organic Sessions", value: ga4Connected ? "Live" : "—", sub: "via GA4" },
                  { label: "Organic Revenue", value: ga4Connected ? "Live" : "—", sub: "via GA4" },
                  { label: "GSC Clicks", value: gscConnected ? "Live" : "—", sub: "via Search Console" },
                ].map((m) => (
                  <div key={m.label}>
                    <div className={cn(
                      "text-lg font-bold font-serif",
                      m.value === "Live" ? "text-emerald-400" : "text-zinc-600"
                    )}>{m.value}</div>
                    <div className="text-xs text-zinc-500 mt-0.5">{m.label}</div>
                    <div className="text-[10px] text-zinc-700">{m.sub}</div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-zinc-600 mt-3 text-center">
                Full revenue attribution dashboard coming in Phase 2.
              </p>
            </div>
          )}

          {/* Setup instructions */}
          {!ga4Connected && !gscConnected && (
            <div className="mt-4 p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/40 text-xs text-zinc-500 space-y-1">
              <p className="font-medium text-zinc-400 mb-2">Setup required</p>
              <p>1. Add <code className="text-brand-400">GOOGLE_CLIENT_ID</code> and <code className="text-brand-400">GOOGLE_CLIENT_SECRET</code> to your backend <code>.env</code></p>
              <p>2. Set <code className="text-brand-400">GOOGLE_REDIRECT_URI=http://localhost:3000/dashboard/settings</code></p>
              <p>3. Enable Analytics API + Search Console API in Google Cloud Console</p>
              <p>4. Add your domain to OAuth redirect URIs</p>
            </div>
          )}
        </div>

        {/* Other integrations */}
        <div className="card p-6">
          <h3 className="font-semibold mb-4">Other Integrations</h3>
          <div className="space-y-3">
            {["Ahrefs", "WordPress", "Razorpay"].map((name) => (
              <div key={name} className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-lg">
                <span className="text-sm text-zinc-300">{name}</span>
                <button className="btn-ghost text-xs">Connect</button>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
