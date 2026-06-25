'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Beaker, ShieldCheck, Mail, Lock, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    try {
      await login(email, password);
      router.push('/');
    } catch (err: any) {
      setLocalError(err.info?.detail || err.message || 'Login failed');
    }
  };

  const displayError = localError || error;

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#05060e] text-zinc-100 relative overflow-hidden select-none">
      {/* Background Orbs */}
      <div className="glow-orb-primary top-[15%] left-[20%]" />
      <div className="glow-orb-secondary bottom-[15%] right-[20%]" />

      <div className="w-full max-w-md p-8 glass-panel border border-zinc-800/40 rounded-2xl shadow-2xl relative z-10 space-y-8 animate-fade-in">
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="mx-auto w-12 h-12 rounded-xl bg-gradient-to-tr from-violet-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-violet-500/20">
            <Beaker className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
              ResearchOS
            </h1>
            <p className="text-xs text-zinc-500 mt-1">
              Multi-agent academic research workflow automation
            </p>
          </div>
        </div>

        {/* Error Display */}
        {displayError && (
          <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {displayError}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-5">
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
              Research Identity (Email)
            </label>
            <div className="relative flex items-center">
              <Mail className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@researchos.ai"
                className="w-full glass-input pl-10 pr-4 py-2 text-xs rounded-lg placeholder-zinc-600"
                suppressHydrationWarning
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                Access Token (Password)
              </label>
              <a href="#" className="text-[10px] text-violet-400 hover:text-violet-300">
                Forgot Token?
              </a>
            </div>
            <div className="relative flex items-center">
              <Lock className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full glass-input pl-10 pr-4 py-2 text-xs rounded-lg placeholder-zinc-600"
                suppressHydrationWarning
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold tracking-wide shadow-lg shadow-violet-500/20 transition-all flex items-center justify-center gap-2"
            suppressHydrationWarning
          >
            {isLoading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                Authenticate Session
              </>
            )}
          </button>
        </form>

        {/* Register Link */}
        <div className="text-center">
          <p className="text-[11px] text-zinc-500">
            Don&apos;t have an account?{' '}
            <a
              href="/register"
              className="text-violet-400 hover:text-violet-300 font-medium"
            >
              Register
            </a>
          </p>
        </div>

        {/* Footer */}
        <div className="text-center border-t border-zinc-800/20 pt-4">
          <p className="text-[10px] text-zinc-500">
            Authorized personnel only. Logs are recorded under auditing namespace.
          </p>
        </div>
      </div>
    </div>
  );
}
