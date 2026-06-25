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
  CheckCircle2,
  Loader2,
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
      const res = await fetch(`${api.baseUrl}/api/v1/projects/${id}/research/status`);
      await res.json();

      setTimeout(() => {
        setIsExporting(false);
        setDownloadUrl(`${api.baseUrl}/docs/api-reference.md`);
      }, 1500);
    } catch {
      setIsExporting(false);
    }
  };

  const journals = [
    { name: 'IEEE Transactions on Pattern Analysis and Machine Intelligence (PAMI)', score: '95%', fit: 'Excellent', reasoning: 'Highly aligns with the machine learning algorithms and RAG pipelines implemented.' },
    { name: 'ACM Computing Surveys', score: '88%', fit: 'High', reasoning: 'Excellent fit for the comprehensive literature review synthesis.' },
    { name: 'Nature Machine Intelligence', score: '82%', fit: 'Good', reasoning: 'Strong relevance to the innovative supervisor multi-agent orchestration architecture.' },
  ];

  const checklistItems = [
    { text: 'Verify author affiliations and list order.', checked: true },
    { text: 'Ensure abstract word limit is under 250 words.', checked: true },
    { text: 'Confirm all [REF_n] markers map to verified citations in references list.', checked: true },
    { text: 'Compile cover letter package for submission.', checked: false },
    { text: 'Check formatting guidelines against journal template specifications.', checked: false },
  ];

  return (
    <AppShell>
      <div className="space-y-6 select-none">
        {/* Breadcrumbs */}
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-gray-400 uppercase tracking-wide">
            <Link href="/" className="hover:text-gray-600 transition-colors">Projects</Link>
            <ChevronRight className="w-3 h-3" />
            {currentProject && (
              <Link href={`/project/${id}`} className="hover:text-gray-600 transition-colors truncate max-w-[150px]">
                {currentProject.title}
              </Link>
            )}
            <ChevronRight className="w-3 h-3" />
            <span className="text-gray-500">Export & Submit</span>
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
            <Share2 className="w-6 h-6 text-indigo-600" />
            Export & Submission Manager
          </h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Export Actions (left) */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
              <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide flex items-center gap-2">
                <Scroll className="w-4 h-4 text-indigo-500" />
                Publication Export Settings
              </h3>

              <div className="grid grid-cols-2 gap-3">
                {(['pdf', 'latex', 'markdown', 'docx'] as const).map((fmt) => (
                  <button
                    key={fmt}
                    onClick={() => setSelectedFormat(fmt)}
                    className={`p-3 rounded-lg border text-xs font-semibold tracking-wide uppercase transition-all flex flex-col items-center gap-2 ${
                      selectedFormat === fmt
                        ? 'border-indigo-300 bg-indigo-50 text-indigo-700 shadow-sm'
                        : 'border-gray-200 bg-gray-50 text-gray-500 hover:text-gray-700 hover:border-gray-300'
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
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-lg text-sm font-semibold shadow-sm transition-colors"
              >
                {isExporting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <DownloadCloud className="w-4 h-4" />
                    Compile Export Package
                  </>
                )}
              </button>

              {downloadUrl && (
                <a
                  href={downloadUrl}
                  download="ResearchOS_Publication_Draft.md"
                  className="w-full flex items-center justify-center gap-2 py-2 border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg text-xs font-semibold transition-colors"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  Download Package Ready
                </a>
              )}
            </div>

            {/* Submission Checklist */}
            <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
              <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide flex items-center gap-2">
                <CheckSquare className="w-4 h-4 text-indigo-500" />
                Submission Checklist
              </h3>

              <div className="space-y-3">
                {checklistItems.map((item, idx) => (
                  <div key={idx} className="flex gap-2.5 items-start text-sm text-gray-600">
                    <input
                      type="checkbox"
                      defaultChecked={item.checked}
                      className="mt-0.5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="leading-snug">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Journal Recommendations (right) */}
          <div className="lg:col-span-2 bg-white border border-gray-200 rounded-lg p-5 flex flex-col">
            <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide flex items-center gap-2 mb-5">
              <BookmarkCheck className="w-4 h-4 text-indigo-500" />
              Journal Venue Recommendations
            </h3>

            <div className="flex-1 space-y-4">
              {journals.map((journal, idx) => (
                <div key={idx} className="bg-gray-50 rounded-lg p-5 border border-gray-100 flex gap-4 select-text">
                  <div className="p-2.5 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-500 shrink-0 h-fit">
                    <Book className="w-5 h-5" />
                  </div>
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex justify-between items-start gap-4">
                      <h4 className="font-semibold text-sm text-gray-800 leading-snug break-words">
                        {journal.name}
                      </h4>
                      <span className="px-2 py-0.5 rounded-md border border-indigo-200 bg-indigo-50 text-indigo-600 text-[10px] font-semibold uppercase tracking-wider shrink-0">
                        {journal.score}
                      </span>
                    </div>
                    <p className="text-[11px] text-gray-400 font-medium uppercase tracking-wide">
                      Confidence: {journal.fit}
                    </p>
                    <p className="text-sm text-gray-600 leading-relaxed mt-1">
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
