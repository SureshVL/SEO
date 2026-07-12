"use client";

import { useState, useEffect } from "react";
import {
  Plus, Loader2, Globe, AlertCircle, MapPin, Link2, Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Language {
  id: number;
  language_code: string;
  region_code: string | null;
  display_name: string;
  is_default: boolean;
}

interface LocalizedContent {
  source_url: string;
  localized_url: string;
  title: string;
  description: string;
  translation_status: string;
  needs_human_review: boolean;
}

interface HreflangLink {
  source_url: string;
  target_url: string;
  target_language: string;
  relationship_type: string;
}

interface RegionalTarget {
  region_code: string;
  region_name: string;
  target_keywords: string[];
  local_content_needed: boolean;
  seo_priority: number;
}

interface HealthAnalysis {
  health_score: number;
  overall_assessment: string;
  priorities: Array<{
    priority: number;
    area: string;
    recommendation: string;
  }>;
}

export default function MultilingualPage() {
  const { apiKey } = useAppStore();

  const [tab, setTab] = useState<"languages" | "content" | "hreflang" | "regional" | "health">("languages");
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const [languages, setLanguages] = useState<Language[]>([]);
  const [localizedContent, setLocalizedContent] = useState<LocalizedContent[]>([]);
  const [hreflangLinks, setHreflangLinks] = useState<HreflangLink[]>([]);
  const [regionalTargets, setRegionalTargets] = useState<RegionalTarget[]>([]);
  const [healthAnalysis, setHealthAnalysis] = useState<HealthAnalysis | null>(null);

  const [showAddLanguageModal, setShowAddLanguageModal] = useState(false);
  const [showLocalizeModal, setShowLocalizeModal] = useState(false);

  const [newLanguage, setNewLanguage] = useState({
    language_code: "",
    region_code: "",
    display_name: "",
    is_default: false,
  });

  const [localizeForm, setLocalizeForm] = useState({
    source_url: "",
    source_title: "",
    source_keywords: "",
    source_content: "",
    target_language_id: 0,
    target_region: "",
  });

  const commonLanguages = [
    { code: "en", name: "English" },
    { code: "es", name: "Spanish" },
    { code: "fr", name: "French" },
    { code: "de", name: "German" },
    { code: "it", name: "Italian" },
    { code: "pt", name: "Portuguese" },
    { code: "ja", name: "Japanese" },
    { code: "zh", name: "Chinese" },
  ];

  const commonRegions = [
    { code: "US", name: "United States" },
    { code: "GB", name: "United Kingdom" },
    { code: "CA", name: "Canada" },
    { code: "AU", name: "Australia" },
    { code: "IN", name: "India" },
    { code: "DE", name: "Germany" },
    { code: "FR", name: "France" },
    { code: "ES", name: "Spain" },
  ];

  const fetchLanguages = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/multilingual/languages`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setLanguages(data.languages || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchLocalizedContent = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/multilingual/content`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setLocalizedContent(data.localized_content || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHreflangConfig = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/multilingual/hreflang`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setHreflangLinks(data.hreflang_config || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRegionalTargeting = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/multilingual/regional-targeting`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setRegionalTargets(data.regional_targeting || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHealthAnalysis = async () => {
    setAnalyzing(true);
    try {
      const res = await apiFetch(`/multilingual/analyze`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setHealthAnalysis(data);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    if (tab === "languages") {
      fetchLanguages();
    } else if (tab === "content") {
      fetchLocalizedContent();
    } else if (tab === "hreflang") {
      fetchHreflangConfig();
    } else if (tab === "regional") {
      fetchRegionalTargeting();
    } else if (tab === "health") {
      fetchHealthAnalysis();
    }
  }, [tab, apiKey]);

  const handleAddLanguage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey || !newLanguage.language_code) {
      toast.error("Language code required");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch(`/multilingual/languages`, {
        method: "POST",
        headers: {
          "X-API-KEY": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          language_code: newLanguage.language_code,
          region_code: newLanguage.region_code || null,
          display_name: newLanguage.display_name || newLanguage.language_code,
          is_default: newLanguage.is_default,
        }),
      });

      if (res.ok) {
        toast.success("Language added");
        setNewLanguage({ language_code: "", region_code: "", display_name: "", is_default: false });
        setShowAddLanguageModal(false);
        fetchLanguages();
      } else {
        toast.error("Failed to add language");
      }
    } catch (err) {
      console.error("Failed:", err);
      toast.error("Error adding language");
    } finally {
      setLoading(false);
    }
  };

  const handleLocalizeContent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey || !localizeForm.source_url || !localizeForm.target_language_id) {
      toast.error("Source URL and target language required");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch(`/multilingual/localize`, {
        method: "POST",
        headers: {
          "X-API-KEY": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source_url: localizeForm.source_url,
          source_content: localizeForm.source_content,
          source_title: localizeForm.source_title,
          source_keywords: localizeForm.source_keywords.split(",").map((k) => k.trim()),
          target_language_id: parseInt(localizeForm.target_language_id.toString()),
          target_region: localizeForm.target_region || null,
        }),
      });

      if (res.ok) {
        toast.success("Content localized");
        setLocalizeForm({
          source_url: "",
          source_title: "",
          source_keywords: "",
          source_content: "",
          target_language_id: 0,
          target_region: "",
        });
        setShowLocalizeModal(false);
        fetchLocalizedContent();
      } else {
        toast.error("Failed to localize content");
      }
    } catch (err) {
      console.error("Failed:", err);
      toast.error("Error localizing content");
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 8) return "bg-red-100 text-red-800";
    if (priority >= 5) return "bg-orange-100 text-orange-800";
    return "bg-yellow-100 text-yellow-800";
  };

  const tabs = [
    { id: "languages", label: "Languages", icon: Globe },
    { id: "content", label: "Content", icon: Zap },
    { id: "hreflang", label: "Hreflang", icon: Link2 },
    { id: "regional", label: "Regions", icon: MapPin },
    { id: "health", label: "Health", icon: AlertCircle },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Multilingual SEO"
        description="Manage translations, localization, hreflang tags, and regional targeting"
      />

      <div className="flex gap-2 border-b overflow-x-auto">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={cn(
                "px-4 py-2 font-medium text-sm border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap",
                tab === t.id
                  ? "border-cyan-500 text-cyan-600"
                  : "border-transparent text-gray-600 hover:text-gray-900",
              )}
            >
              <Icon className="w-4 h-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      <div className="bg-white rounded-lg border">
        {tab === "languages" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">Languages & Regions</h3>
                <p className="text-sm text-gray-600">Configure languages for your site</p>
              </div>
              <button
                onClick={() => setShowAddLanguageModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition"
              >
                <Plus className="w-4 h-4" />
                Add Language
              </button>
            </div>

            {languages.length === 0 ? (
              <div className="text-center py-12">
                <Globe className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No languages configured yet</p>
                <button
                  onClick={() => setShowAddLanguageModal(true)}
                  className="mt-4 text-cyan-600 hover:text-cyan-700 font-medium"
                >
                  Add your first language
                </button>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {languages.map((lang) => (
                  <div
                    key={`${lang.language_code}-${lang.region_code || 'base'}`}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold text-gray-900">{lang.display_name}</h4>
                      {lang.is_default && <span className="text-xs bg-cyan-100 text-cyan-800 px-2 py-1 rounded">Default</span>}
                    </div>
                    <p className="text-sm text-gray-600">
                      Code: {lang.language_code}
                      {lang.region_code && ` · Region: ${lang.region_code}`}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "content" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">Localized Content</h3>
                <p className="text-sm text-gray-600">Translated content for each language</p>
              </div>
              <button
                onClick={() => setShowLocalizeModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition"
              >
                <Plus className="w-4 h-4" />
                Localize Content
              </button>
            </div>

            {localizedContent.length === 0 ? (
              <div className="text-center py-12">
                <Zap className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No localized content yet</p>
                <button
                  onClick={() => setShowLocalizeModal(true)}
                  className="mt-4 text-cyan-600 hover:text-cyan-700 font-medium"
                >
                  Translate your first content
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {localizedContent.map((content) => (
                  <div
                    key={content.localized_url}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900">{content.title}</h4>
                        <p className="text-sm text-gray-600">{content.localized_url}</p>
                      </div>
                      <span className={cn(
                        "px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap",
                        content.translation_status === "completed"
                          ? "bg-green-100 text-green-800"
                          : "bg-yellow-100 text-yellow-800",
                      )}>
                        {content.translation_status}
                      </span>
                    </div>
                    {content.needs_human_review && (
                      <p className="text-xs text-orange-600 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Needs human review
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "hreflang" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">Hreflang Configuration</h3>
                <p className="text-sm text-gray-600">Language version relationships</p>
              </div>
            </div>

            {hreflangLinks.length === 0 ? (
              <div className="text-center py-12">
                <Link2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No hreflang links configured</p>
              </div>
            ) : (
              <div className="space-y-4">
                {hreflangLinks.map((link, idx) => (
                  <div
                    key={idx}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition"
                  >
                    <p className="text-sm text-gray-600 mb-2">From: {link.source_url}</p>
                    <p className="font-medium text-gray-900 mb-1">To: {link.target_url}</p>
                    <div className="flex gap-4 text-xs text-gray-600">
                      <span>Language: {link.target_language}</span>
                      <span>Type: {link.relationship_type}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "regional" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">Regional Targeting</h3>
                <p className="text-sm text-gray-600">Region-specific keywords and content needs</p>
              </div>
            </div>

            {regionalTargets.length === 0 ? (
              <div className="text-center py-12">
                <MapPin className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No regional targeting configured</p>
              </div>
            ) : (
              <div className="space-y-4">
                {regionalTargets.map((region) => (
                  <div
                    key={`${region.region_code}`}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="font-semibold text-gray-900">{region.region_name}</h4>
                        <p className="text-sm text-gray-600">Code: {region.region_code}</p>
                      </div>
                      <span className={cn("px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap", getPriorityColor(region.seo_priority))}>
                        Priority {region.seo_priority}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">
                      Keywords: {region.target_keywords.slice(0, 3).join(", ")}
                      {region.target_keywords.length > 3 && `...`}
                    </p>
                    {region.local_content_needed && (
                      <p className="text-xs text-orange-600 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Local content needed
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "health" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">Multilingual SEO Health</h3>
                <p className="text-sm text-gray-600">Analysis and improvement recommendations</p>
              </div>
              <button
                onClick={fetchHealthAnalysis}
                disabled={analyzing}
                className="flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 transition"
              >
                {analyzing && <Loader2 className="w-4 h-4 animate-spin" />}
                {analyzing ? "Analyzing..." : "Analyze Setup"}
              </button>
            </div>

            {!healthAnalysis ? (
              <div className="text-center py-12">
                <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">Run analysis to get started</p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="bg-gradient-to-r from-cyan-50 to-blue-50 rounded-lg p-6 border border-cyan-200">
                  <div className="flex items-center gap-4">
                    <div className="text-5xl font-bold text-cyan-600">{healthAnalysis.health_score}</div>
                    <div>
                      <p className="text-sm text-gray-600">Multilingual SEO Health Score</p>
                      <p className="font-semibold text-gray-900">{healthAnalysis.overall_assessment}</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold text-gray-900 mb-4">Top Priorities</h4>
                  <div className="space-y-3">
                    {healthAnalysis.priorities?.slice(0, 5).map((priority) => (
                      <div key={priority.priority} className="border rounded-lg p-3 hover:bg-gray-50 transition">
                        <p className="font-medium text-gray-900 text-sm">{priority.recommendation}</p>
                        <p className="text-xs text-gray-600 mt-1">{priority.area}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {showAddLanguageModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Add Language</h3>
            <form onSubmit={handleAddLanguage} className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Language</label>
                <select
                  value={newLanguage.language_code}
                  onChange={(e) => setNewLanguage({ ...newLanguage, language_code: e.target.value })}
                  className="w-full mt-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                >
                  <option value="">Select language</option>
                  {commonLanguages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Region (optional)</label>
                <select
                  value={newLanguage.region_code}
                  onChange={(e) => setNewLanguage({ ...newLanguage, region_code: e.target.value })}
                  className="w-full mt-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                >
                  <option value="">No specific region</option>
                  {commonRegions.map((region) => (
                    <option key={region.code} value={region.code}>
                      {region.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newLanguage.is_default}
                  onChange={(e) => setNewLanguage({ ...newLanguage, is_default: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <label className="text-sm text-gray-700">Set as default language</label>
              </div>
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 transition"
                >
                  {loading ? "Adding..." : "Add Language"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddLanguageModal(false)}
                  className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showLocalizeModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4">Localize Content</h3>
            <form onSubmit={handleLocalizeContent} className="space-y-4">
              <input
                type="text"
                placeholder="Source URL"
                value={localizeForm.source_url}
                onChange={(e) => setLocalizeForm({ ...localizeForm, source_url: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <input
                type="text"
                placeholder="Title"
                value={localizeForm.source_title}
                onChange={(e) => setLocalizeForm({ ...localizeForm, source_title: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <input
                type="text"
                placeholder="Keywords (comma-separated)"
                value={localizeForm.source_keywords}
                onChange={(e) => setLocalizeForm({ ...localizeForm, source_keywords: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <textarea
                placeholder="Content"
                value={localizeForm.source_content}
                onChange={(e) => setLocalizeForm({ ...localizeForm, source_content: e.target.value })}
                className="w-full h-24 px-3 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <select
                value={localizeForm.target_language_id}
                onChange={(e) => setLocalizeForm({ ...localizeForm, target_language_id: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
              >
                <option value={0}>Select target language</option>
                {languages.map((lang) => (
                  <option key={lang.id} value={lang.id}>
                    {lang.display_name}
                  </option>
                ))}
              </select>
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 transition"
                >
                  {loading ? "Localizing..." : "Localize"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowLocalizeModal(false)}
                  className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
