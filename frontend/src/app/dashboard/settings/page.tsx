"use client";

import { Settings } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-zinc-400 mt-1">Manage your account and API configuration.</p>
      </div>

      <div className="space-y-6 max-w-2xl">
        <div className="card p-6">
          <h3 className="font-semibold mb-4">API Keys</h3>
          <div className="space-y-4">
            <div>
              <label className="label">Orchestrator API Key</label>
              <input type="password" className="input-field" defaultValue="dev-orchestrator-key" />
              <p className="text-xs text-zinc-500 mt-1">Used to authenticate with the OMNI-RANK backend API.</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="font-semibold mb-4">Profile</h3>
          <div className="space-y-4">
            <div>
              <label className="label">Full Name</label>
              <input type="text" className="input-field" placeholder="Your name" />
            </div>
            <div>
              <label className="label">Email</label>
              <input type="email" className="input-field" placeholder="you@company.com" disabled />
              <p className="text-xs text-zinc-500 mt-1">Managed by Supabase Auth.</p>
            </div>
            <button className="btn-primary">Save changes</button>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="font-semibold mb-4">Integrations</h3>
          <div className="space-y-3">
            {["Google Search Console", "Google Analytics 4", "Ahrefs", "WordPress"].map((name) => (
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
