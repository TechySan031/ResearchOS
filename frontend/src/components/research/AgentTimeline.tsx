'use client';

import React, { useEffect, useRef, useState, memo } from 'react';
import { AgentLog } from '@/types';
import {
  Download, ArrowDown, Eye, Activity, X, Beaker,
  Search, BookOpen, CheckCircle2, Lightbulb, FlaskConical,
  PenTool, ShieldCheck, FileType2, BookMarked, Users, Package,
  Zap, AlertCircle, Info,
} from 'lucide-react';

interface AgentTimelineProps {
  logs: AgentLog[];
}

const AGENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  system: Activity,
  research_retrieval: Search,
  literature_review: BookOpen,
  citation_verification: CheckCircle2,
  gap_analysis: Lightbulb,
  methodology_suggestion: FlaskConical,
  draft_writing: PenTool,
  hallucination_detection: ShieldCheck,
  formatting: FileType2,
  journal_recommendation: BookMarked,
  reviewer_simulation: Users,
  submission_preparation: Package,
};

const AGENT_BADGE: Record<string, string> = {
  system: 'bg-gray-50 text-gray-600 border-gray-200',
  research_retrieval: 'bg-blue-50 text-blue-700 border-blue-200',
  literature_review: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  citation_verification: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  gap_analysis: 'bg-purple-50 text-purple-700 border-purple-200',
  methodology_suggestion: 'bg-teal-50 text-teal-700 border-teal-200',
  draft_writing: 'bg-violet-50 text-violet-700 border-violet-200',
  hallucination_detection: 'bg-amber-50 text-amber-700 border-amber-200',
  formatting: 'bg-sky-50 text-sky-700 border-sky-200',
  journal_recommendation: 'bg-orange-50 text-orange-700 border-orange-200',
  reviewer_simulation: 'bg-rose-50 text-rose-700 border-rose-200',
  submission_preparation: 'bg-emerald-50 text-emerald-700 border-emerald-200',
};

const EVENT_STYLES: Record<string, { label: string; style: string }> = {
  agent_started:   { label: 'Started',   style: 'bg-indigo-50 text-indigo-600 border-indigo-200' },
  agent_completed: { label: 'Completed', style: 'bg-emerald-50 text-emerald-600 border-emerald-200' },
  agent_error:     { label: 'Error',     style: 'bg-red-50 text-red-600 border-red-200' },
  agent_progress:  { label: 'Progress',  style: 'bg-cyan-50 text-cyan-600 border-cyan-200' },
  agent_event:     { label: 'Event',     style: 'bg-gray-50 text-gray-600 border-gray-200' },
  started:         { label: 'Started',   style: 'bg-indigo-50 text-indigo-600 border-indigo-200' },
  completed:       { label: 'Completed', style: 'bg-emerald-50 text-emerald-600 border-emerald-200' },
  failed:          { label: 'Error',     style: 'bg-red-50 text-red-600 border-red-200' },
};

const DEFAULT_EVENT = { label: 'Event', style: 'bg-gray-50 text-gray-500 border-gray-200' };
const DEFAULT_BADGE = 'bg-gray-50 text-gray-600 border-gray-200';

/** Individual log row — memoized */
const LogEntry = memo(function LogEntry({
  log,
  onViewDetails,
}: {
  log: AgentLog;
  onViewDetails: (log: AgentLog) => void;
}) {
  const AgentIcon = AGENT_ICONS[log.agent_name] || Activity;
  const badge = AGENT_BADGE[log.agent_name] || DEFAULT_BADGE;
  const eventCfg = EVENT_STYLES[log.event_type] || DEFAULT_EVENT;
  const badgeParts = badge.split(' ');
  const time = new Date(log.created_at).toLocaleTimeString([], {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  return (
    <div className="flex items-start gap-3 py-2 px-2 rounded-md hover:bg-gray-50/80 transition-colors group">
      {/* Agent icon */}
      <div className={`w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5 ${badgeParts[0]}`}>
        <AgentIcon className={`w-3 h-3 ${badgeParts[1]}`} />
      </div>

      <div className="flex-1 min-w-0">
        {/* Badges row */}
        <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border shrink-0 ${badge}`}>
            {log.agent_name.replace(/_/g, ' ')}
          </span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border shrink-0 ${eventCfg.style}`}>
            {eventCfg.label}
          </span>
          <span className="text-[11px] text-gray-400 font-mono tabular-nums ml-auto shrink-0 select-none">
            {time}
          </span>
        </div>

        {/* Message */}
        <div className="flex items-start gap-1">
          <span className="text-[13px] text-gray-700 leading-relaxed break-words flex-1">
            {log.message}
          </span>
          {log.data && Object.keys(log.data).length > 0 && (
            <button
              onClick={() => onViewDetails(log)}
              className="ml-1 inline-flex items-center gap-0.5 text-[11px] text-indigo-600 hover:text-indigo-700 font-medium shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <Eye className="w-2.5 h-2.5" /> Details
            </button>
          )}
        </div>
      </div>
    </div>
  );
});

function AgentTimeline({ logs }: AgentTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [selectedLog, setSelectedLog] = useState<AgentLog | null>(null);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 40);
  };

  const handleDownload = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2));
    const anchor = document.createElement('a');
    anchor.setAttribute('href', dataStr);
    anchor.setAttribute('download', 'researchos_agent_logs.json');
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden flex flex-col h-[420px] relative">
      {/* Header */}
      <div className="h-11 bg-gray-50/80 border-b border-gray-200 px-5 flex items-center justify-between select-none shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-indigo-100 flex items-center justify-center">
            <Activity className="w-3 h-3 text-indigo-600" />
          </div>
          <span className="text-xs font-semibold text-gray-700">Activity Feed</span>
          <span className="text-[11px] text-gray-400 font-mono tabular-nums">({logs.length})</span>
        </div>
        <button
          onClick={handleDownload}
          className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          title="Download Logs"
        >
          <Download className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Entries */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 px-4 py-3 overflow-y-auto space-y-0.5"
      >
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-3 py-8">
            <div className="w-10 h-10 rounded-xl bg-gray-50 border border-gray-200 flex items-center justify-center">
              <Beaker className="w-5 h-5 text-gray-300" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-gray-500">No agent activity yet</p>
              <p className="text-xs text-gray-400 mt-0.5">Start the workflow to see live agent events</p>
            </div>
          </div>
        ) : (
          logs.map((log) => (
            <LogEntry key={log.id} log={log} onViewDetails={setSelectedLog} />
          ))
        )}
      </div>

      {/* Auto-scroll button */}
      {!autoScroll && logs.length > 0 && (
        <button
          onClick={() => setAutoScroll(true)}
          className="absolute bottom-16 right-6 flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full text-[11px] font-medium shadow-lg transition-all"
        >
          <ArrowDown className="w-3 h-3" /> Follow
        </button>
      )}

      {/* Details Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-[2px] z-50 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-xl overflow-hidden shadow-xl flex flex-col max-h-[500px] border border-gray-200">
            <div className="h-11 bg-gray-50 border-b border-gray-200 px-5 flex items-center justify-between select-none">
              <span className="text-xs font-semibold text-gray-700">Event Payload</span>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="p-5 overflow-y-auto bg-gray-50 font-mono text-xs text-gray-700">
              <pre className="whitespace-pre-wrap">{JSON.stringify(selectedLog.data, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default memo(AgentTimeline);
