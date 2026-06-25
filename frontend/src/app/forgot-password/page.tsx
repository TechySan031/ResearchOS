'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Beaker, Mail, ArrowLeft, Loader2, CheckCircle2 } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { useToast } from '@/components/Toast';

export default function ForgotPasswordPage() {
  const { forgotPassword } = useAuthStore();
  const { showToast } = useToast();
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await forgotPassword(email);
      setSubmitted(true);
      showToast('Reset instructions sent', 'success');
    } catch (err: any) {
      // Always show success for security (don't reveal if email exists)
      setSubmitted(true);
      showToast('Reset instructions sent', 'success');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 select-none">
      <div className="w-full max-w-md p-8 bg-white border border-gray-200 rounded-xl shadow-sm space-y-7">
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="mx-auto w-11 h-11 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm">
            <Beaker className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-gray-900">
              Reset Password
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              {submitted
                ? 'Check your email for a reset link'
                : 'Enter your email to receive reset instructions'}
            </p>
          </div>
        </div>

        {submitted ? (
          /* ── Success State ── */
          <div className="space-y-5">
            <div className="flex flex-col items-center gap-3 py-4">
              <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-emerald-500" />
              </div>
              <div className="text-center space-y-1">
                <p className="text-sm font-medium text-gray-900">Email sent</p>
                <p className="text-sm text-gray-500 max-w-xs">
                  If an account exists for <span className="font-medium text-gray-700">{email}</span>,
                  you&apos;ll receive a password reset link shortly.
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <button
                onClick={() => { setSubmitted(false); setEmail(''); }}
                className="w-full py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-sm font-medium transition-colors"
              >
                Try another email
              </button>
              <Link
                href="/login"
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold shadow-sm transition-colors flex items-center justify-center gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to sign in
              </Link>
            </div>
          </div>
        ) : (
          /* ── Form ── */
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Email Address
              </label>
              <div className="relative flex items-center">
                <Mail className="w-4 h-4 text-gray-400 absolute left-3 pointer-events-none" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@university.edu"
                  className="w-full auth-input pl-10 pr-4 py-2.5 rounded-lg"
                  autoComplete="email"
                  autoFocus
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-lg text-sm font-semibold shadow-sm transition-colors flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Sending...
                </>
              ) : (
                'Send Reset Instructions'
              )}
            </button>

            <div className="text-center">
              <Link
                href="/login"
                className="text-sm text-indigo-600 hover:text-indigo-700 font-medium inline-flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to sign in
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
