'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { 
  Beaker, 
  Folder, 
  FileText, 
  BookOpen, 
  Award, 
  Share2, 
  LogOut, 
  User, 
  Bell, 
  Search 
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import ProtectedRoute from './ProtectedRoute';

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Folder },
  ];

  // If inside a project workspace, add nested workspace nav items
  const isProjectWorkspace = pathname?.startsWith('/project/');
  const projectId = isProjectWorkspace ? pathname.split('/')[2] : null;

  const projectNavigation = projectId ? [
    { name: 'Overview', href: `/project/${projectId}`, icon: Beaker },
    { name: 'Workflow', href: `/project/${projectId}/research`, icon: Award },
    { name: 'Draft Editor', href: `/project/${projectId}/editor`, icon: FileText },
    { name: 'Citations', href: `/project/${projectId}/citations`, icon: BookOpen },
    { name: 'Export', href: `/project/${projectId}/export`, icon: Share2 },
  ] : [];

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const displayName = user?.name || 'Researcher';
  const displayEmail = user?.email || 'researcher@lab.edu';
  const displayRole = user?.role || 'researcher';

  return (
    <ProtectedRoute>
      <div className="min-h-screen flex flex-col bg-white text-gray-900">
        <div className="flex flex-1">
          {/* Sidebar */}
          <aside className="w-60 bg-gray-50 border-r border-gray-200 flex flex-col justify-between select-none shrink-0">
            <div>
              {/* Logo */}
              <div className="h-14 flex items-center gap-2.5 px-5 border-b border-gray-200">
                <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
                  <Beaker className="w-4 h-4 text-white" />
                </div>
                <span className="font-semibold text-base tracking-tight text-gray-900">
                  ResearchOS
                </span>
              </div>

              {/* Navigation links */}
              <nav className="p-3 space-y-0.5">
                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wide px-3 block mb-2 mt-1">
                  Navigation
                </span>
                {navigation.map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors duration-150 ${
                        isActive 
                          ? 'bg-indigo-50 text-indigo-700 font-medium' 
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                      }`}
                    >
                      <item.icon className={`w-4 h-4 ${isActive ? 'text-indigo-600' : 'text-gray-400'}`} />
                      {item.name}
                    </Link>
                  );
                })}

                {isProjectWorkspace && projectNavigation.length > 0 && (
                  <>
                    <div className="h-px bg-gray-200 my-3 mx-1" />
                    <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wide px-3 block mb-2">
                      Workspace
                    </span>
                    {projectNavigation.map((item) => {
                      const isActive = pathname === item.href;
                      return (
                        <Link
                          key={item.name}
                          href={item.href}
                          className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors duration-150 ${
                            isActive 
                              ? 'bg-indigo-50 text-indigo-700 font-medium' 
                              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                          }`}
                        >
                          <item.icon className={`w-4 h-4 ${isActive ? 'text-indigo-600' : 'text-gray-400'}`} />
                          {item.name}
                        </Link>
                      );
                    })}
                  </>
                )}
              </nav>
            </div>

            {/* User profile / Bottom bar */}
            <div className="p-3 border-t border-gray-200 space-y-1">
              <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-md">
                <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center">
                  <User className="w-3.5 h-3.5 text-indigo-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-900 truncate">{displayName}</p>
                  <p className="text-[11px] text-gray-400 truncate">{displayEmail}</p>
                </div>
                {displayRole === 'admin' && (
                  <span className="text-[9px] font-semibold bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full uppercase">
                    Admin
                  </span>
                )}
              </div>
              <button 
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-500 hover:text-gray-700 rounded-md hover:bg-gray-100 transition-colors duration-150"
                suppressHydrationWarning
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </div>
          </aside>

          {/* Main Work Content Area */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* Header */}
            <header className="h-14 bg-white border-b border-gray-200 px-8 flex items-center justify-between shrink-0">
              {/* Search Bar */}
              <div className="w-80 relative flex items-center">
                <Search className="w-4 h-4 text-gray-400 absolute left-3 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search projects, citations, papers..."
                  className="w-full bg-gray-50 border border-gray-200 pl-9 pr-4 py-1.5 text-sm rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
                  suppressHydrationWarning
                />
              </div>

              {/* Topbar Actions */}
              <div className="flex items-center gap-3">
                <button 
                  className="p-2 rounded-md bg-white border border-gray-200 hover:bg-gray-50 text-gray-500 hover:text-gray-700 transition-colors relative"
                  suppressHydrationWarning
                >
                  <Bell className="w-4 h-4" />
                  <span className="w-2 h-2 rounded-full bg-indigo-500 absolute top-1.5 right-1.5 border-2 border-white" />
                </button>
                <div className="h-5 w-px bg-gray-200" />
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="text-[11px] font-medium tracking-wide text-gray-500">
                    Engine Connected
                  </span>
                </div>
              </div>
            </header>

            {/* Page body */}
            <main className="flex-1 overflow-y-auto p-8 bg-white">
              <div className="max-w-6xl mx-auto">
                {children}
              </div>
            </main>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
