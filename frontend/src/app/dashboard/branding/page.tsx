"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Palette, Save, Sparkles } from "lucide-react";
import { useAppStore } from "@/lib/store";
import {
  getProjectBranding,
  listProjects,
  updateProjectBranding,
  type BrandingConfig,
} from "@/lib/api";
import { toast } from "sonner";

const EMPTY: BrandingConfig = {
  agency_name: "",
  logo_url: "",
  primary_color: "#8B5CF6",
  secondary_color: "#EC4899",
  accent_color: "#22D3EE",
  text_color: "#2c2723",
  background_color: "#faf8f5",
  cover_title: "",
  cover_subtitle: "",
  footer_text: "",
  website: "",
  email: "",
  enabled: false,
};

export default function BrandingPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState(businessProfile?.projectId || "");
  const [cfg, setCfg] = useState<BrandingConfig>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [previewHtml, setPreviewHtml] = useState<string>("");
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    listProjects(apiKey).then(setProjects).catch(() => {});
  }, [apiKey]);
  useEffect(() => {
    if (businessProfile?.projectId && !projectId) setProjectId(businessProfile.projectId);
  }, [businessProfile]);

  const load = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await getProjectBranding(projectId, apiKey);
      setCfg({ ...EMPTY, ...res.branding });
      setWarnings(res.validation_warnings);
    } catch (err: any) {
      toast.error(err.message || "Failed to load branding");
    } finally {
      setLoading(false);
    }
  }, [projectId, apiKey]);
  useEffect(() => {
    load();
  }, [load]);

  function patch(field: keyof BrandingConfig, value: any) {
    setCfg(c => ({ ...c, [field]: value }));
  }

  async function handleSave() {
    if (!projectId) {
      toast.error("Select a project");
      return;
    }
    setSaving(true);
    try {
      const res = await updateProjectBranding(projectId, cfg, apiKey);
      setCfg({ ...EMPTY, ...res.branding });
      toast.success("Branding saved");
    } catch (err: any) {
      const detail = err.message || "Save failed";
      toast.error(detail);
    } finally {
      setSaving(false);
    }
  }

  async function generatePreview() {
    if (!projectId) {
      toast.error("Select a project first");
      return;
    }
    setPreviewLoading(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      const res = await fetch(
        `${base}/projects/${projectId}/branding/preview`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-KEY": apiKey,
          },
          body: JSON.stringify(cfg),
        },
      );
      if (!res.ok) throw new Error(await res.text());
      const html = await res.text();
      setPreviewHtml(html);
    } catch (err: any) {
      toast.error(err.message || "Preview failed");
    } finally {
      setPreviewLoading(false);
    }
  }

  const previewSrcDoc = useMemo(() => previewHtml, [previewHtml]);

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Palette className="w-6 h-6 text-fuchsia-400" /> White-label Reports
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Drop in your agency's logo, colours, and cover copy. Branded PDF
          reports automatically use these settings for the selected project.
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
      ) : (
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="card p-6">
              <label className="flex items-center gap-2 text-sm text-zinc-300 mb-4">
                <input
                  type="checkbox"
                  checked={cfg.enabled}
                  onChange={e => patch("enabled", e.target.checked)}
                  className="w-4 h-4"
                />
                Enable white-label branding for this project
              </label>

              <div className="space-y-3">
                <Field label="Agency name">
                  <input
                    value={cfg.agency_name}
                    onChange={e => patch("agency_name", e.target.value)}
                    placeholder="Acme Digital"
                    className="input-field"
                  />
                </Field>
                <Field label="Logo URL (https://…)">
                  <input
                    value={cfg.logo_url}
                    onChange={e => patch("logo_url", e.target.value)}
                    placeholder="https://cdn.acme.com/logo.png"
                    className="input-field"
                  />
                </Field>
                <Field label="Website">
                  <input
                    value={cfg.website}
                    onChange={e => patch("website", e.target.value)}
                    placeholder="https://acme.com"
                    className="input-field"
                  />
                </Field>
                <Field label="Contact email">
                  <input
                    value={cfg.email}
                    onChange={e => patch("email", e.target.value)}
                    placeholder="hello@acme.com"
                    className="input-field"
                  />
                </Field>
              </div>
            </div>

            <div className="card p-6">
              <h3 className="font-semibold text-zinc-200 mb-3">Colour palette</h3>
              <div className="grid grid-cols-2 gap-3">
                <ColorField label="Primary" value={cfg.primary_color}
                  onChange={v => patch("primary_color", v)} />
                <ColorField label="Secondary" value={cfg.secondary_color}
                  onChange={v => patch("secondary_color", v)} />
                <ColorField label="Accent" value={cfg.accent_color}
                  onChange={v => patch("accent_color", v)} />
                <ColorField label="Text" value={cfg.text_color}
                  onChange={v => patch("text_color", v)} />
                <ColorField label="Background" value={cfg.background_color}
                  onChange={v => patch("background_color", v)} />
              </div>
            </div>

            <div className="card p-6">
              <h3 className="font-semibold text-zinc-200 mb-3">Cover & footer copy</h3>
              <div className="space-y-3">
                <Field label="Cover title">
                  <input
                    value={cfg.cover_title}
                    onChange={e => patch("cover_title", e.target.value)}
                    placeholder="Q2 2026 SEO Performance Review"
                    className="input-field"
                  />
                </Field>
                <Field label="Cover subtitle">
                  <input
                    value={cfg.cover_subtitle}
                    onChange={e => patch("cover_subtitle", e.target.value)}
                    placeholder="Prepared for Client Co."
                    className="input-field"
                  />
                </Field>
                <Field label="Footer text">
                  <input
                    value={cfg.footer_text}
                    onChange={e => patch("footer_text", e.target.value)}
                    placeholder="Confidential — prepared by Acme Digital"
                    className="input-field"
                  />
                </Field>
              </div>
            </div>

            {warnings.length > 0 && (
              <div className="card p-4 border border-amber-500/30 bg-amber-500/5 text-sm">
                <div className="font-semibold text-amber-300 mb-1">Validation warnings</div>
                <ul className="list-disc pl-5 text-amber-200">
                  {warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}

            <div className="flex items-center gap-2">
              <button onClick={handleSave} disabled={saving || !projectId}
                className="btn-primary flex items-center gap-2">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save branding
              </button>
              <button onClick={generatePreview} disabled={previewLoading || !projectId}
                className="btn-ghost flex items-center gap-2">
                {previewLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Generate preview
              </button>
            </div>
          </div>

          <div className="card p-0 overflow-hidden min-h-[600px]">
            {previewSrcDoc ? (
              <iframe
                srcDoc={previewSrcDoc}
                className="w-full h-[800px] bg-white"
                title="Branding preview"
              />
            ) : (
              <div className="p-10 text-sm text-zinc-500 flex flex-col items-center justify-center h-full text-center">
                <Sparkles className="w-8 h-8 mb-3 text-zinc-600" />
                Hit <em className="mx-1">Generate preview</em> to render a sample
                branded report using the current settings.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[11px] text-zinc-500 uppercase tracking-wider mb-1">{label}</span>
      {children}
    </label>
  );
}

function ColorField({
  label, value, onChange,
}: {
  label: string; value: string; onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="block text-[11px] text-zinc-500 uppercase tracking-wider mb-1">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={value || "#000000"}
          onChange={e => onChange(e.target.value)}
          className="w-10 h-10 rounded border border-zinc-800 bg-transparent"
        />
        <input
          value={value}
          onChange={e => onChange(e.target.value)}
          className="input-field font-mono text-sm"
          placeholder="#8B5CF6"
        />
      </div>
    </label>
  );
}
