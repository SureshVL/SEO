"use client";

import { useEffect, useState } from "react";
import {
  Download, Loader2, Package, Plus, ShoppingCart, Sparkles, AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

interface ProductFeed {
  id: number;
  name: string;
  source_type: string;
  product_count: number;
  issue_count: number;
  optimized_count: number;
  truncated: boolean;
  last_imported: string;
}

interface FeedProduct {
  id: number;
  product_key: string;
  title: string;
  brand: string;
  issues: any;
  issue_count: number;
  optimized_title: string | null;
  optimization_status: string;
}

export default function FeedsPage() {
  const { apiKey } = useAppStore();
  const [feeds, setFeeds] = useState<ProductFeed[]>([]);
  const [selectedFeed, setSelectedFeed] = useState<ProductFeed | null>(null);
  const [products, setProducts] = useState<FeedProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importForm, setImportForm] = useState({ name: "", source_url: "", csv_text: "" });

  const fetchFeeds = async () => {
    if (!apiKey) return;
    try {
      const res = await apiFetch(`/feeds`);
      if (res.ok) setFeeds((await res.json()).feeds || []);
    } catch (e) { console.error(e); }
  };

  const fetchProducts = async (feed: ProductFeed) => {
    setSelectedFeed(feed);
    try {
      const res = await apiFetch(`/feeds/${feed.id}/products?only_issues=true&limit=100`);
      if (res.ok) setProducts((await res.json()).products || []);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchFeeds();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey]);

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importForm.source_url && !importForm.csv_text) {
      toast.error("Provide a feed URL or paste CSV content");
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch(`/feeds/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(importForm),
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Imported ${data.product_count} products — ${data.issue_count} issues found`);
        setShowImport(false);
        setImportForm({ name: "", source_url: "", csv_text: "" });
        fetchFeeds();
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Import failed");
      }
    } catch { toast.error("Import failed"); }
    finally { setLoading(false); }
  };

  const handleOptimize = async () => {
    if (!selectedFeed) return;
    setOptimizing(true);
    try {
      const res = await apiFetch(`/feeds/${selectedFeed.id}/optimize`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Optimized ${data.optimized} products (plan budget: ${data.budget} SKUs)`);
        fetchProducts(selectedFeed);
        fetchFeeds();
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Optimization failed");
      }
    } catch { toast.error("Optimization failed"); }
    finally { setOptimizing(false); }
  };

  const handleExport = () => {
    if (!selectedFeed) return;
    apiFetch(`/feeds/${selectedFeed.id}/export`)
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `omnirank-supplemental-feed-${selectedFeed.id}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Product Feeds"
        description="SKU-scale listing optimization — import your catalog, fix listing issues, export a supplemental feed"
        icon={ShoppingCart}
        accent="#F97316"
      />

      <div className="flex justify-end gap-2">
        <button
          onClick={() => setShowImport(true)}
          className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition"
        >
          <Plus className="w-4 h-4" /> Import Feed
        </button>
      </div>

      {feeds.length === 0 ? (
        <div className="bg-white rounded-lg border p-12 text-center">
          <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-600 font-medium">No product feeds yet</p>
          <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">
            Import your Google Merchant feed URL or a CSV export. OMNI-RANK checks every SKU
            against Shopping listing rules and AI-rewrites the worst titles and descriptions.
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-4">
          {feeds.map((feed) => (
            <button
              key={feed.id}
              onClick={() => fetchProducts(feed)}
              className={cn(
                "bg-white rounded-lg border p-4 text-left hover:shadow-md transition",
                selectedFeed?.id === feed.id && "ring-2 ring-orange-500",
              )}
            >
              <p className="font-semibold text-gray-900 truncate">{feed.name}</p>
              <div className="flex gap-3 mt-2 text-sm">
                <span className="text-gray-600">{feed.product_count.toLocaleString()} SKUs</span>
                <span className="text-orange-600">{feed.issue_count.toLocaleString()} issues</span>
                <span className="text-green-600">{feed.optimized_count} optimized</span>
              </div>
              {feed.truncated && (
                <p className="text-xs text-amber-600 mt-1">Feed truncated at import cap</p>
              )}
            </button>
          ))}
        </div>
      )}

      {selectedFeed && (
        <div className="bg-white rounded-lg border">
          <div className="p-4 border-b flex items-center justify-between flex-wrap gap-3">
            <h3 className="font-semibold text-gray-900">
              Products with issues — {selectedFeed.name}
            </h3>
            <div className="flex gap-2">
              <button
                onClick={handleOptimize}
                disabled={optimizing}
                className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 transition text-sm"
              >
                {optimizing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {optimizing ? "Optimizing..." : "AI-optimize listings"}
              </button>
              <button
                onClick={handleExport}
                className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50 transition text-sm"
              >
                <Download className="w-4 h-4" /> Export supplemental feed
              </button>
            </div>
          </div>
          <div className="divide-y max-h-[600px] overflow-y-auto">
            {products.length === 0 ? (
              <p className="p-8 text-center text-gray-500">No products with issues 🎉</p>
            ) : (
              products.map((p) => {
                const issues = typeof p.issues === "string" ? JSON.parse(p.issues || "[]") : (p.issues || []);
                return (
                  <div key={p.id} className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-mono text-gray-500">{p.product_key}</span>
                          {p.optimization_status === "optimized" && (
                            <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">Optimized</span>
                          )}
                        </div>
                        <p className="font-medium text-gray-900 truncate">{p.title || "(no title)"}</p>
                        {p.optimized_title && (
                          <p className="text-sm text-green-700 truncate">→ {p.optimized_title}</p>
                        )}
                      </div>
                      <span className="shrink-0 flex items-center gap-1 text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded-full">
                        <AlertTriangle className="w-3 h-3" /> {p.issue_count}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {issues.slice(0, 5).map((issue: any, i: number) => (
                        <span key={i} className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded" title={issue.detail}>
                          {issue.type.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {showImport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Import Product Feed</h3>
            <form onSubmit={handleImport} className="space-y-3">
              <input type="text" placeholder="Feed name (optional)" value={importForm.name}
                onChange={(e) => setImportForm({ ...importForm, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500" />
              <input type="text" placeholder="Feed URL (Google Merchant XML or CSV)" value={importForm.source_url}
                onChange={(e) => setImportForm({ ...importForm, source_url: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500" />
              <div className="text-center text-xs text-gray-400">— or paste CSV —</div>
              <textarea placeholder={"id,title,description,brand,price,link\nSKU1,Blue Shoes,...,Acme,29.99,https://..."}
                value={importForm.csv_text}
                onChange={(e) => setImportForm({ ...importForm, csv_text: e.target.value })}
                className="w-full h-32 px-3 py-2 border rounded-lg font-mono text-xs resize-none focus:outline-none focus:ring-2 focus:ring-orange-500" />
              <div className="flex gap-3">
                <button type="submit" disabled={loading}
                  className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 transition">
                  {loading ? "Importing..." : "Import & analyze"}
                </button>
                <button type="button" onClick={() => setShowImport(false)}
                  className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
