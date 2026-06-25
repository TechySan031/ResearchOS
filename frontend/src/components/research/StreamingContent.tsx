'use client';

import React, { useEffect, useRef, useMemo, memo } from 'react';
import { Edit3, Loader2 } from 'lucide-react';

interface StreamingContentProps {
  /** Map of section name → accumulated text content */
  content: Record<string, string>;
  /** Currently active agent name */
  activeAgent?: string | null;
}

/**
 * Renders streaming LLM output as it arrives token-by-token.
 * Shows active agent indicator, word count, and blinking cursor.
 */
function StreamingContent({ content, activeAgent }: StreamingContentProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);

  const sections = Object.entries(content);

  const totalWords = useMemo(
    () => sections.reduce((sum, [, text]) => sum + text.split(/\s+/).filter(Boolean).length, 0),
    [content]
  );

  useEffect(() => {
    if (shouldAutoScroll.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [content]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    shouldAutoScroll.current = scrollHeight - scrollTop - clientHeight < 40;
  };

  if (sections.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-2">
        <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
        <p className="text-sm text-gray-400">Waiting for draft output...</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Status bar */}
      <div className="flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-2">
          {activeAgent && (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600 border border-indigo-200 font-medium capitalize">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-indigo-600" />
              </span>
              {activeAgent.replace(/_/g, ' ')}
            </span>
          )}
          <span className="text-gray-400 flex items-center gap-1">
            <Edit3 className="w-3 h-3" />
            Drafting in progress
          </span>
        </div>
        <span className="text-gray-400 font-mono tabular-nums">
          {totalWords.toLocaleString()} words
        </span>
      </div>

      {/* Content */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="max-h-[400px] overflow-y-auto space-y-5"
      >
        {sections.map(([sectionName, text], index) => {
          const isLast = index === sections.length - 1;

          return (
            <div key={sectionName} className="space-y-1.5">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-1.5">
                {sectionName.replace(/_/g, ' ')}
                {isLast && (
                  <Loader2 className="w-3 h-3 text-indigo-500 animate-spin" />
                )}
              </h4>
              <div className="text-sm text-gray-800 leading-[1.8] whitespace-pre-wrap select-text">
                {text}
                {isLast && <span className="streaming-cursor" />}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default memo(StreamingContent);
