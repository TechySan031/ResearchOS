'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string[];
}

/**
 * Wraps pages that require authentication.
 * Redirects to /login if the user is not authenticated.
 * Optionally enforces role-based access.
 */
export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const router = useRouter();
  const { isAuthenticated, user, initialize } = useAuthStore();
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const init = async () => {
      await initialize();
      setInitialized(true);
    };

    init();
  }, [initialize]);

  useEffect(() => {
    if (initialized && !isAuthenticated) {
      router.push('/login');
    }
  }, [initialized, isAuthenticated, router]);

  // Role check
  if (initialized && isAuthenticated && requiredRole && user) {
    if (!requiredRole.includes(user.role)) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-white">
          <div className="text-center space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">Access Denied</h2>
            <p className="text-sm text-gray-500">
              You do not have permission to view this page.
            </p>
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm"
              suppressHydrationWarning
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      );
    }
  }

  // Show loading while initializing
  if (!initialized || (!isAuthenticated && typeof window !== 'undefined')) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <span className="w-4 h-4 border-2 border-gray-300 border-t-indigo-500 rounded-full animate-spin" />
          Verifying session...
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
