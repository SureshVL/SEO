"use client";

import Link from "next/link";
import { ArrowRight, Download, Book, Mail } from "lucide-react";
import { useState } from "react";

const engines = ["ChatGPT", "Perplexity", "Gemini", "Google AI"];
const verticals = [
  "saas", "ecommerce", "healthcare", "fintech", "b2b", "legal",
  "realestate", "local", "accounting", "consulting", "education",
  "insurance", "nonprofit"
];

const verticalTitles: Record<string, string> = {
  "saas": "SaaS",
  "ecommerce": "Ecommerce",
  "healthcare": "Healthcare",
  "fintech": "Fintech",
  "b2b": "B2B",
  "legal": "Legal",
  "realestate": "Real Estate",
  "local": "Local Services",
  "accounting": "Accounting",
  "consulting": "Consulting",
  "education": "Education",
  "insurance": "Insurance",
  "nonprofit": "Nonprofit",
};

interface Guide {
  engine: string;
  vertical: string;
  title: string;
  description: string;
  pages: number;
}

const guides: Guide[] = [];

for (const engine of engines) {
  for (const vertical of verticals) {
    guides.push({
      engine,
      vertical,
      title: `How to Rank in ${engine} for ${verticalTitles[vertical]}`,
      description: `A practical guide to optimizing your ${verticalTitles[vertical]} business for ${engine} AI search.`,
      pages: 32,
    });
  }
}

export default function GuidesPage() {
  const [email, setEmail] = useState("");
  const [selectedGuide, setSelectedGuide] = useState<Guide | null>(null);
  const [downloadEmail, setDownloadEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleDownload = async (guide: Guide) => {
    if (!downloadEmail || !downloadEmail.includes("@")) {
      alert("Please enter a valid email");
      return;
    }

    try {
      await fetch("/email/subscribe", {
        method: "POST",
        body: JSON.stringify({
          email: downloadEmail,
          vertical: guide.vertical,
        }),
      });

      const link = document.createElement("a");
      link.href = "#";
      link.download = `${guide.title.replace(/\s+/g, "-").toLowerCase()}.pdf`;
      link.click();

      setSubmitted(true);
      setTimeout(() => {
        setDownloadEmail("");
        setSelectedGuide(null);
        setSubmitted(false);
      }, 3000);
    } catch (error) {
      console.error("Error downloading guide:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            OR OMNI-RANK
          </Link>
          <Link href="/auth/signup" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Start free trial <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 py-24">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h1 className="text-5xl font-bold text-slate-900 mb-6">
            AI Ranking Guides
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto">
            52 industry-specific guides to ranking in ChatGPT, Perplexity, Gemini, and Google AI Overviews.
            Get actionable strategies for your vertical.
          </p>
        </div>
      </section>

      <div className="max-w-6xl mx-auto px-6 py-20">
        {selectedGuide ? (
          <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg border border-slate-200 shadow-lg">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">{selectedGuide.title}</h2>
            <p className="text-slate-600 mb-6">{selectedGuide.description}</p>
            
            <div className="flex items-center gap-4 mb-8 p-4 bg-slate-50 rounded-lg">
              <Book className="w-5 h-5 text-violet-600" />
              <span className="text-sm font-medium text-slate-900">{selectedGuide.pages} pages</span>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleDownload(selectedGuide);
              }}
              className="space-y-4 mb-6"
            >
              <div>
                <label className="block text-sm font-medium text-slate-900 mb-2">
                  Email address
                </label>
                <input
                  type="email"
                  value={downloadEmail}
                  onChange={(e) => setDownloadEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg"
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full bg-violet-600 text-white font-semibold py-3 rounded-lg hover:bg-violet-700 flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" /> Download PDF
              </button>
            </form>

            <button
              onClick={() => setSelectedGuide(null)}
              className="w-full text-slate-600 font-medium border-t border-slate-200 mt-6 pt-6"
            >
              Back
            </button>
          </div>
        ) : (
          <>
            <div className="mb-12">
              <h2 className="text-2xl font-bold text-slate-900 mb-6">Browse Guides</h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {guides.slice(0, 12).map((guide, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedGuide(guide)}
                    className="text-left bg-white p-6 rounded-lg border border-slate-200 hover:shadow-lg"
                  >
                    <p className="text-xs text-violet-600 font-semibold mb-2">
                      {guide.engine}
                    </p>
                    <h3 className="text-lg font-bold text-slate-900 mb-2">
                      {verticalTitles[guide.vertical]}
                    </h3>
                    <p className="text-sm text-slate-600 mb-4">{guide.pages} pages</p>
                    <span className="text-violet-600 font-semibold">Download →</span>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
