'use client';

import { useAgentStore } from '@/stores/agentStore';

export default function MetricCard() {
    const metrics = useAgentStore((s) => s.metrics);

    return (
        <div className="rounded-lg border p-4 bg-white">
            <h3 className="font-semibold text-lg mb-3">
                Workflow Metrics
            </h3>

            <div className="space-y-2">
                <div>
                    <span className="font-medium">
                        TTFT:
                    </span>{' '}
                    {metrics.ttftMs !== null
                        ? `${metrics.ttftMs.toFixed(2)} ms`
                        : '--'}
                </div>

                <div>
                    <span className="font-medium">
                        Workflow Duration:
                    </span>{' '}
                    {metrics.workflowDurationMs !== null
                        ? `${metrics.workflowDurationMs.toFixed(2)} ms`
                        : '--'}
                </div>
            </div>
        </div>
    );
}