'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useCopilotStore } from '@/stores/copilotStore';
import type { CopilotMessage } from '@/types';
import {
  MessageSquare,
  Send,
  Trash2,
  Loader2,
  BookOpen,
  AlertCircle,
} from 'lucide-react';

interface ResearchCopilotProps {
  projectId: string;
  /** Whether the workflow has produced results (controls the empty state). */
  hasWorkflowResults: boolean;
}

/**
 * Research Copilot — conversational Q&A grounded in workflow results.
 *
 * Renders inline on the project overview page between Research Results
 * and Agent History.  Follows the light-first design guidelines.
 */
export default function ResearchCopilot({
  projectId,
  hasWorkflowResults,
}: ResearchCopilotProps) {
  const { messages, isLoading, error, sendMessage, clearChat } =
    useCopilotStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to newest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    setInput('');
    await sendMessage(projectId, trimmed);
    inputRef.current?.focus();
  };

  // ── Empty state: no workflow results ──────────────────────────────

  if (!hasWorkflowResults) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-3">
          <MessageSquare className="w-4 h-4 text-indigo-600" />
          <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide">
            Research Copilot
          </h3>
        </div>
        <p className="text-sm text-gray-400 italic">
          The copilot will be available after the workflow produces results.
        </p>
      </div>
    );
  }

  // ── Active state ─────────────────────────────────────────────────

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-indigo-600" />
          <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">
            Research Copilot
          </span>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
            title="Clear conversation"
          >
            <Trash2 className="w-3 h-3" />
            Clear
          </button>
        )}
      </div>

      {/* Message Area */}
      <div className="max-h-[400px] overflow-y-auto p-5 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8 space-y-2">
            <BookOpen className="w-8 h-8 text-gray-300 mx-auto" />
            <p className="text-sm text-gray-400">
              Ask questions about your research results
            </p>
            <div className="flex flex-wrap justify-center gap-2 pt-2">
              {[
                'Summarize the literature review',
                'What research gaps were found?',
                'List the suggested methodologies',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="text-xs px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-full text-gray-500 hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-200 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Analyzing workflow results...</span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 text-sm text-red-500 bg-red-50 rounded-md p-3">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="px-5 py-3 border-t border-gray-100 flex items-center gap-3"
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your research..."
          disabled={isLoading}
          className="flex-1 text-sm bg-gray-50 border border-gray-200 rounded-md px-3 py-2 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 disabled:opacity-50 transition-colors"
          maxLength={2000}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="flex items-center justify-center w-8 h-8 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
}

// ── Message Bubble ────────────────────────────────────────────────────

function MessageBubble({ message }: { message: CopilotMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-indigo-600 text-white'
            : 'bg-gray-50 border border-gray-200 text-gray-800'
        }`}
      >
        <div className="whitespace-pre-wrap select-text">{message.content}</div>

        {/* Source badges */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-gray-200/60">
            {message.sources.map((source) => (
              <span
                key={source}
                className="inline-flex items-center gap-1 text-[10px] font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full"
              >
                <BookOpen className="w-2.5 h-2.5" />
                {source.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
