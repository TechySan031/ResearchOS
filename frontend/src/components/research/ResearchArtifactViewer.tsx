'use client';

import React, { useState, memo } from 'react';
import { WorkflowState } from '@/types';
import { AnimatePresence, motion } from 'framer-motion';
import {
  FileText,
  ShieldCheck,
  Package,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  AlertTriangle,
  Download,
} from 'lucide-react';

interface ResearchArtifactViewerProps {
  workflowState: WorkflowState;
}

interface ArtifactSection {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  data: any;
  accentColor: string;
  borderColor: string;
  bgColor: string;
}

/**
 * Displays final research artifacts: formatted paper, hallucination report,
 * and submission package. Each section is collapsible with copy + download.
 */
function ResearchArtifactViewer({ workflowState }: ResearchArtifactViewerProps) {
  const artifacts: ArtifactSection[] = [
    {
      id: 'formatted_paper',
      label: `Formatted Paper${workflowState.format_style ? ` (${workflowState.format_style.toUpperCase()})` : ''}`,
      icon: FileText,
      data: workflowState.formatted_paper,
      accentColor: 'text-indigo-600',
      borderColor: 'border-indigo-200',
      bgColor: 'bg-indigo-50/50',
    },
    {
      id: 'hallucination_report',
      label: 'Hallucination Report',
      icon: ShieldCheck,
      data: workflowState.hallucination_report,
      accentColor: 'text-amber-600',
      borderColor: 'border-amber-200',
      bgColor: 'bg-amber-50/50',
    },
    {
      id: 'submission_package',
      label: 'Submission Package',
      icon: Package,
      data: workflowState.submission_package,
      accentColor: 'text-emerald-600',
      borderColor: 'border-emerald-200',
      bgColor: 'bg-emerald-50/50',
    },
  ].filter((a) => a.data != null && a.data !== '' && !(typeof a.data === 'object' && Object.keys(a.data).length === 0));

  const [expandedId, setExpandedId] = useState<string | null>(
    artifacts.length > 0 ? artifacts[0].id : null
  );

  if (artifacts.length === 0) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          Research Artifacts
        </h3>
        <span className="text-[11px] text-gray-400 font-mono tabular-nums">
          {artifacts.length} artifact{artifacts.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="p-4 space-y-2">
        {artifacts.map((artifact) => (
          <ArtifactAccordion
            key={artifact.id}
            artifact={artifact}
            isExpanded={expandedId === artifact.id}
            onToggle={() => setExpandedId(expandedId === artifact.id ? null : artifact.id)}
          />
        ))}
      </div>

      {/* Workflow Errors */}
      {workflowState.errors?.length > 0 && (
        <div className="px-4 pb-4">
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg space-y-2">
            <div className="flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
              <span className="text-xs font-medium text-red-700">Workflow Errors</span>
            </div>
            {workflowState.errors.map((err, idx) => (
              <div key={idx} className="text-xs text-red-600 font-mono whitespace-pre-wrap select-text">
                {typeof err === 'string' ? err : JSON.stringify(err, null, 2)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Accordion Item ───────────────────────────────────────────────────

function ArtifactAccordion({
  artifact,
  isExpanded,
  onToggle,
}: {
  artifact: ArtifactSection;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const Icon = artifact.icon;

  const contentString =
    typeof artifact.data === 'string'
      ? artifact.data
      : JSON.stringify(artifact.data, null, 2);

  const wordCount = typeof artifact.data === 'string'
    ? artifact.data.split(/\s+/).filter(Boolean).length
    : null;

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(contentString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore clipboard errors
    }
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    const blob = new Blob([contentString], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.id}.${typeof artifact.data === 'string' ? 'txt' : 'json'}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className={`border rounded-lg overflow-hidden transition-all ${
        isExpanded ? artifact.borderColor : 'border-gray-100 hover:border-gray-200'
      }`}
    >
      {/* Header */}
      <div
        onClick={onToggle}
        role="button"
        tabIndex={0}
        className={`w-full flex items-center justify-between px-4 py-3 text-left cursor-pointer transition-colors ${
          isExpanded ? artifact.bgColor : 'hover:bg-gray-50'
        }`}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 ${isExpanded ? artifact.bgColor : 'bg-gray-50'}`}>
            <Icon className={`w-3.5 h-3.5 ${artifact.accentColor}`} />
          </div>
          <div className="min-w-0">
            <span className="text-sm font-semibold text-gray-800 block truncate">
              {artifact.label}
            </span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-600 border border-emerald-200">
                Generated
              </span>
              {wordCount != null && (
                <span className="text-[11px] text-gray-400 font-mono tabular-nums">
                  {wordCount.toLocaleString()} words
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-white/60 transition-colors"
            title="Copy content"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={handleDownload}
            className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-white/60 transition-colors"
            title="Download"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400 ml-1" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400 ml-1" />
          )}
        </div>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t border-gray-100">
              <div className="pt-4 max-h-[500px] overflow-y-auto">
                {artifact.id === 'formatted_paper' && typeof artifact.data === 'string' ? (
                  /* Render formatted paper as prose — not monospace */
                  <div className="text-sm text-gray-800 leading-[1.8] whitespace-pre-wrap select-text prose-compact">
                    {artifact.data}
                  </div>
                ) : typeof artifact.data === 'string' ? (
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono leading-relaxed select-text">
                    {artifact.data}
                  </pre>
                ) : (
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono leading-relaxed select-text">
                    {JSON.stringify(artifact.data, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default memo(ResearchArtifactViewer);