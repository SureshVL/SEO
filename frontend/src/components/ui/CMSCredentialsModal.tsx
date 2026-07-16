"use client";

import { useEffect, useState } from "react";
import { Copy, Loader2, Trash2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CMSCredentialsModalProps {
  isOpen: boolean;
  platform: "wordpress" | "shopify" | "webflow";
  onClose: () => void;
  onSave: () => void;
  apiKey: string;
}

export function CMSCredentialsModal({
  isOpen,
  platform,
  onClose,
  onSave,
  apiKey,
}: CMSCredentialsModalProps) {
  const [endpoint, setEndpoint] = useState("");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    fetchCredentials();
  }, [isOpen, platform]);

  async function fetchCredentials() {
    try {
      const res = await apiFetch(`/cms/credentials/${platform}`);
      const data = await res.json();
      if (data.saved) {
        setEndpoint(data.endpoint_url || "");
        setSaved(true);
      }
    } catch (err) {
      console.error("Failed to fetch credentials:", err);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!endpoint || !apiKeyInput) {
      toast.error("Endpoint and API key required");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch(`/cms/credentials`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          cms_platform: platform,
          endpoint_url: endpoint,
          api_key: apiKeyInput,
          api_secret: apiSecret,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Save failed");
      }

      toast.success(`${platform} credentials saved`);
      setSaved(true);
      onSave();
      setTimeout(onClose, 1000);
    } catch (err: any) {
      toast.error(err.message || "Failed to save credentials");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete ${platform} credentials?`)) return;

    setLoading(true);
    try {
      const res = await apiFetch(`/cms/credentials/${platform}`, {
        method: "DELETE",
      });

      if (!res.ok) throw new Error("Delete failed");
      toast.success("Credentials deleted");
      setEndpoint("");
      setApiKeyInput("");
      setApiSecret("");
      setSaved(false);
    } catch (err: any) {
      toast.error(err.message || "Delete failed");
    } finally {
      setLoading(false);
    }
  }

  if (!isOpen) return null;

  const platformLabel = platform.charAt(0).toUpperCase() + platform.slice(1);
  const platformColor =
    platform === "wordpress"
      ? "violet"
      : platform === "shopify"
        ? "cyan"
        : "indigo";

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-100">
            Connect {platformLabel}
          </h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {saved ? (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4">
            <div className="text-sm text-emerald-300 mb-3">
              ✓ Connected to {endpoint}
            </div>
            <button
              onClick={handleDelete}
              disabled={loading}
              className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300"
            >
              <Trash2 className="w-4 h-4" />
              Remove credentials
            </button>
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                WordPress Site URL
              </label>
              <input
                type="url"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="https://mysite.com"
                className="input-field w-full"
                required
              />
              <p className="text-xs text-zinc-600 mt-1">
                The base URL of your WordPress site (e.g., https://example.com)
              </p>
            </div>

            <div>
              <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                REST API Username
              </label>
              <input
                type="text"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="admin"
                className="input-field w-full"
                required
              />
              <p className="text-xs text-zinc-600 mt-1">
                WordPress user with REST API access
              </p>
            </div>

            <div>
              <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                REST API Application Password
              </label>
              <input
                type="password"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder="••••••••••••"
                className="input-field w-full"
                required
              />
              <p className="text-xs text-zinc-600 mt-1">
                Generate at: WordPress Admin → Users → Your Profile → Application Passwords
              </p>
            </div>

            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-xs text-blue-300">
              <strong>First time?</strong> Create an Application Password in WordPress:
              <ol className="list-decimal pl-5 mt-2 space-y-1">
                <li>Log in to WordPress admin</li>
                <li>Go to Users → Your Profile</li>
                <li>Scroll to "Application Passwords"</li>
                <li>Enter "OMNI-RANK" and click "Create Application Password"</li>
                <li>Copy the generated password here</li>
              </ol>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 btn-primary flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Credentials"
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
