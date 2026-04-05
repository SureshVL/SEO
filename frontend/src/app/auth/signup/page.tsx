"use client";

import Link from "next/link";
import { useState } from "react";
import { createClient } from "@/lib/supabase";
import { toast } from "sonner";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { data: { full_name: name } },
      });
      if (error) throw error;
      setSent(true);
    } catch (err: any) {
      toast.error(err.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-surface-1">
        <div className="text-center max-w-sm">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-2xl mx-auto mb-6">✓</div>
          <h1 className="text-2xl font-bold mb-2">Check your email</h1>
          <p className="text-zinc-400 text-sm">We sent a verification link to <strong className="text-zinc-200">{email}</strong>. Click the link to activate your account.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-surface-1">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-brand-600 flex items-center justify-center font-bold text-lg mx-auto mb-4">OR</div>
          <h1 className="text-2xl font-bold">Create your account</h1>
          <p className="text-sm text-zinc-400 mt-1">Start ranking #1 with AI in under 2 minutes</p>
        </div>

        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label className="label">Full name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-field" placeholder="Amit Sharma" required />
          </div>
          <div>
            <label className="label">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" placeholder="you@company.com" required />
          </div>
          <div>
            <label className="label">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="input-field" placeholder="Min 8 characters" minLength={8} required />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Creating account..." : "Create free account"}
          </button>
        </form>

        <p className="text-center text-xs text-zinc-500 mt-4">14-day free trial · No credit card required</p>
        <p className="text-center text-sm text-zinc-400 mt-4">
          Already have an account? <Link href="/auth/login" className="text-brand-400 hover:text-brand-300">Log in</Link>
        </p>
      </div>
    </div>
  );
}
