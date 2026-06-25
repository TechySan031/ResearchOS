'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Beaker, UserPlus, Mail, Lock, User, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, router]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setLocalError('Password must be at least 8 characters');
      return;
    }

    try {
      await register(email, password, name);
      router.push('/');
    } catch (err: any) {
      setLocalError(err.info?.detail || err.message || 'Registration failed');
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
              Create Account
            </h1>
            <p className="text-xs text-zinc-500 mt-1">
              Join the AI research workspace
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
        <form onSubmit={handleRegister} className="space-y-5">
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
              Full Name
            </label>
            <div className="relative flex items-center">
              <User className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Dr. Jane Smith"
                className="w-full glass-input pl-10 pr-4 py-2 text-xs rounded-lg placeholder-zinc-600"
                suppressHydrationWarning
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
              Email Address
            </label>
            <div className="relative flex items-center">
              <Mail className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@university.edu"
                className="w-full glass-input pl-10 pr-4 py-2 text-xs rounded-lg placeholder-zinc-600"
                suppressHydrationWarning
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
              Password
            </label>
            <div className="relative flex items-center">
              <Lock className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                minLength={8}
                className="w-full glass-input pl-10 pr-4 py-2 text-xs rounded-lg placeholder-zinc-600"
                suppressHydrationWarning
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
              Confirm Password
            </label>
            <div className="relative flex items-center">
              <Lock className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                minLength={8}
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
                <UserPlus className="w-4 h-4" />
                Create Account
              </>
            )}
          </button>
        </form>

        {/* Login Link */}
        <div className="text-center">
          <p className="text-[11px] text-zinc-500">
            Already have an account?{' '}
            <a
              href="/login"
              className="text-violet-400 hover:text-violet-300 font-medium"
            >
              Sign In
            </a>
          </p>
        </div>

        {/* Footer */}
        <div className="text-center border-t border-zinc-800/20 pt-4">
          <p className="text-[10px] text-zinc-500">
            By registering you agree to the ResearchOS terms of service.
          </p>
        </div>
      </div>
    </div>
  );
}
