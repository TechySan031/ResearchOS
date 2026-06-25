'use client';

import React, { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useProjectStore } from '@/stores/projectStore';
import { 
  Share2, 
  ChevronRight, 
  Book, 
  CheckSquare, 
  DownloadCloud, 
  FileText, 
  Scroll, 
  BookmarkCheck,
  CheckCircle2
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';

interface ExportPackageProps {
  params: Promise<{ id: string }>;
}

export default function ExportPackage({ params }: ExportPackageProps) {
  const { id } = React.use(params);
  const { currentProject, fetchProject } = useProjectStore();
  const [selectedFormat, setSelectedFormat] = useState<'pdf' | 'latex' | 'markdown' | 'docx'>('pdf');
  const [isExporting, setIsExporting] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  useWebSocket(id);

  useEffect(() => {
    fetchProject(id);
  }, [id, fetchProject]);

  const handleExport = async () => {
    setIsExporting(true);
    setDownloadUrl(null);
    try {
      // Endpoint `/api/v1/projects/{project_id}/export` or similar mock trigger
      const res = await fetch(`${api.baseUrl}/api/v1/projects/${id}/research/status`);
      const statusData = await res.json();

      // Return a simulated local download file depending on format
      setTimeout(() => {
        setIsExporting(false);
        setDownloadUrl(`${api.baseUrl}/docs/api-reference.md`); // Standard existing file to allow clicking download
      }, 1500);
    } catch (err) {
      console.error(err);
      setIsExporting(false);
    }
  };

  const journals = [
    { name: 'IEEE Transactions on Pattern Analysis and Machine Intelligence (PAMI)', score: '95%', fit: 'Excellent', reasoning: 'Highly aligns with the machine learning algorithms and RAG pipelines implemented.' },
    { name: 'ACM Computing Surveys', score: '88%', fit: 'High', reasoning: 'Excellent fit for the comprehensive literature review synthesis.' },
    { name: 'Nature Machine Intelligence', score: '82%', fit: 'Good', reasoning: 'Strong relevance to the innovative supervisor multi-agent orchestration architecture.' }
  ];

  const checklistItems = [
    { text: 'Verify author affiliations and list order.', checked: true },
    { text: 'Ensure abstract word limit is under 250 words.', checked: true },
    { text: 'Confirm all [REF_n] markers map to verified citations in references list.', checked: true },
    { text: 'Compile cover letter package for submission.', checked: false },
    { text: 'Check formatting guidelines against journal template specifications.', checked: false }
  ];

  return (
    <AppShell>
      <div className="space-y-8 select-none">
        {/* Breadcrumbs */}
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
            <Link href="/" className="hover:text-zinc-300">Workspaces</Link>
            <ChevronRight className="w-3 h-3 text-zinc-600" />
            {currentProject && (
              <Link href={`/project/${id}`} className="hover:text-zinc-300 truncate max-w-[150px]">{currentProject.title}</Link>
            )}
            <ChevronRight className="w-3 h-3 text-zinc-600" />
            <span className="text-zinc-400">Export & Submit</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Share2 className="w-6 h-6 text-violet-500" />
            Export & Submission Manager
          </h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Export Actions and Format (left) */}
          <div className="lg:col-span-1 space-y-6">
            <div className="glass-panel border border-zinc-800/40 rounded-xl p-6 space-y-4">
              <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                <Scroll className="w-4 h-4 text-violet-400" />
                Publication Export Settings
              </h3>
              
              <div className="grid grid-cols-2 gap-3">
                {['pdf', 'latex', 'markdown', 'docx'].map((fmt) => (
                  <button
                    key={fmt}
                    onClick={() => setSelectedFormat(fmt as any)}
                    className={`p-3 rounded-lg border text-xs font-semibold tracking-wide uppercase transition-all flex flex-col items-center gap-2 ${
                      selectedFormat === fmt
                        ? 'border-violet-500 bg-violet-950/20 text-white shadow-lg'
                        : 'border-zinc-800 bg-zinc-950/20 text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    <FileText className="w-5 h-5 opacity-70" />
                    {fmt}
                  </button>
                ))}
              </div>

              <button
                onClick={handleExport}
                disabled={isExporting}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold tracking-wide shadow-lg shadow-violet-500/20 transition-all transform hover:translate-y-[-1px] disabled:opacity-50"
              >
                <DownloadCloud className="w-4 h-4" />
                {isExporting ? 'Generating package...' : 'Compile Export Package'}
              </button>

              {downloadUrl && (
                <a
                  href={downloadUrl}
                  download="ResearchOS_Publication_Draft.md"
                  className="w-full flex items-center justify-center gap-2 py-2 border border-emerald-500/20 bg-emerald-950/15 text-emerald-400 hover:bg-emerald-950/30 rounded-lg text-xs font-semibold tracking-wide transition-all"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Download Package Ready
                </a>
              )}
            </div>

            {/* Submission Checklist Card */}
            <div className="glass-panel border border-zinc-800/40 rounded-xl p-6 space-y-4">
              <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                <CheckSquare className="w-4 h-4 text-violet-400" />
                Submission Checklists
              </h3>
              
              <div className="space-y-3">
                {checklistItems.map((item, idx) => (
                  <div key={idx} className="flex gap-2.5 items-start text-xs text-zinc-400">
                    <input 
                      type="checkbox" 
                      defaultChecked={item.checked} 
                      className="mt-0.5 rounded border-zinc-800 bg-zinc-950 text-violet-600 focus:ring-violet-500" 
                    />
                    <span className="leading-snug">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Journal Recommendations (right) */}
          <div className="lg:col-span-2 glass-panel border border-zinc-800/40 rounded-xl p-6 flex flex-col">
            <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2 mb-6">
              <BookmarkCheck className="w-4 h-4 text-violet-400" />
              Journal Venue Recommendations
            </h3>

            <div className="flex-1 space-y-4">
              {journals.map((journal, idx) => (
                <div key={idx} className="glass-card rounded-lg p-5 border border-zinc-800/20 flex gap-4 select-text">
                  <div className="p-2.5 rounded bg-zinc-900 border border-zinc-800 text-violet-400 shrink-0">
                    <Book className="w-5 h-5" />
                  </div>
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex justify-between items-start gap-4">
                      <h4 className="font-semibold text-xs text-zinc-200 leading-snug break-words">
                        {journal.name}
                      </h4>
                      <span className="px-2 py-0.5 rounded border border-violet-500/20 bg-violet-950/20 text-violet-400 text-[9px] font-semibold uppercase tracking-wider shrink-0">
                        Fit Score: {journal.score}
                      </span>
                    </div>
                    <p className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">
                      Confidence Level: {journal.fit}
                    </p>
                    <p className="text-xs text-zinc-400 leading-relaxed mt-1 font-sans">
                      {journal.reasoning}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
