'use client';

import { useAgentStore } from '@/stores/agentStore';
import { Clock, Zap, BarChart3 } from 'lucide-react';

export default function MetricCard() {
  const metrics = useAgentStore((s) => s.metrics);

  const hasData = metrics.ttftMs !== null || metrics.workflowDurationMs !== null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-indigo-600" />
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          Workflow Metrics
        </h3>
      </div>

      {hasData ? (
        <div className="grid grid-cols-2 divide-x divide-gray-100">
          <div className="p-5 space-y-1">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-gray-400 uppercase tracking-wide">
              <Zap className="w-3 h-3" />
              TTFT
            </div>
            <p className="text-lg font-semibold text-gray-900 tabular-nums font-mono">
              {metrics.ttftMs !== null
                ? `${metrics.ttftMs.toFixed(0)}ms`
                : '—'}
            </p>
          </div>
          <div className="p-5 space-y-1">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-gray-400 uppercase tracking-wide">
              <Clock className="w-3 h-3" />
              Duration
            </div>
            <p className="text-lg font-semibold text-gray-900 tabular-nums font-mono">
              {metrics.workflowDurationMs !== null
                ? metrics.workflowDurationMs >= 1000
                  ? `${(metrics.workflowDurationMs / 1000).toFixed(1)}s`
                  : `${metrics.workflowDurationMs.toFixed(0)}ms`
                : '—'}
            </p>
          </div>
        </div>
      ) : (
        <div className="p-6 text-center">
          <p className="text-sm text-gray-400">No metrics recorded yet. Start a workflow to see performance data.</p>
        </div>
      )}
    </div>
  );
}