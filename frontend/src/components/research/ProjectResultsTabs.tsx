'use client';

import React, { useState, useMemo } from 'react';
import { WorkflowState, RetrievedPaper } from '@/types';
import { AnimatePresence, motion } from 'framer-motion';
import {
  BookOpen,
  FileSearch,
  FlaskConical,
  PenTool,
  Quote,
  Users,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Hash,
  Calendar,
  User,
} from 'lucide-react';

interface ProjectResultsTabsProps {
  workflowState: WorkflowState;
}

type TabId = 'papers' | 'review' | 'gaps' | 'methodology' | 'draft' | 'citations' | 'reviews';

interface TabDef {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  hasData: (ws: WorkflowState) => boolean;
}

const TABS: TabDef[] = [
  {
    id: 'papers',
    label: 'Papers',
    icon: BookOpen,
    hasData: (ws) => (ws.retrieved_papers?.length ?? 0) > 0,
  },
  {
    id: 'review',
    label: 'Literature Review',
    icon: FileSearch,
    hasData: (ws) => !!ws.literature_review,
  },
  {
    id: 'gaps',
    label: 'Gap Analysis',
    icon: FileSearch,
    hasData: (ws) => (ws.research_gaps?.length ?? 0) > 0,
  },
  {
    id: 'methodology',
    label: 'Methodology',
    icon: FlaskConical,
    hasData: (ws) => (ws.suggested_methodologies?.length ?? 0) > 0 || !!ws.selected_methodology,
  },
  {
    id: 'draft',
    label: 'Draft',
    icon: PenTool,
    hasData: (ws) => Object.keys(ws.paper_sections ?? {}).length > 0,
  },
  {
    id: 'citations',
    label: 'Citations',
    icon: Quote,
    hasData: (ws) => (ws.citations?.length ?? 0) > 0,
  },
  {
    id: 'reviews',
    label: 'Reviews',
    icon: Users,
    hasData: (ws) => (ws.reviewer_feedback?.length ?? 0) > 0 || (ws.journal_recommendations?.length ?? 0) > 0,
  },
];

/**
 * Tabbed interface for browsing research workflow results.
 * Only shows tabs that have data. Content transitions use framer-motion.
 */
export default function ProjectResultsTabs({ workflowState }: ProjectResultsTabsProps) {
  const availableTabs = useMemo(
    () => TABS.filter((tab) => tab.hasData(workflowState)),
    [workflowState]
  );

  const [activeTab, setActiveTab] = useState<TabId>(
    availableTabs.length > 0 ? availableTabs[0].id : 'papers'
  );

  // If the active tab no longer has data, fall back to the first available tab
  const effectiveTab = availableTabs.find((t) => t.id === activeTab)
    ? activeTab
    : availableTabs[0]?.id ?? 'papers';

  if (availableTabs.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-12 text-center">
        <p className="text-sm text-gray-400 italic">
          No results available yet. Start the workflow to generate research outputs.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* ── Tab Bar ── */}
      <div className="border-b border-gray-200 px-1 overflow-x-auto">
        <nav className="flex gap-0 -mb-px" aria-label="Result tabs">
          {availableTabs.map((tab) => {
            const isActive = tab.id === effectiveTab;
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex items-center gap-1.5 px-4 py-3 text-xs font-medium transition-colors whitespace-nowrap ${
                  isActive
                    ? 'text-indigo-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-600' : 'text-gray-400'}`} />
                {tab.label}
                {/* Active underline */}
                {isActive && (
                  <motion.div
                    layoutId="tab-underline"
                    className="absolute bottom-0 left-2 right-2 h-0.5 bg-indigo-600 rounded-full"
                    transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                  />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* ── Tab Content ── */}
      <div className="p-5 min-h-[200px]">
        <AnimatePresence mode="wait">
          <motion.div
            key={effectiveTab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            {effectiveTab === 'papers' && (
              <PapersTab papers={workflowState.retrieved_papers ?? []} />
            )}
            {effectiveTab === 'review' && (
              <LiteratureReviewTab
                review={workflowState.literature_review}
                themes={workflowState.key_themes ?? []}
              />
            )}
            {effectiveTab === 'gaps' && (
              <GapAnalysisTab gaps={workflowState.research_gaps ?? []} />
            )}
            {effectiveTab === 'methodology' && (
              <MethodologyTab
                suggestions={workflowState.suggested_methodologies ?? []}
                selected={workflowState.selected_methodology}
              />
            )}
            {effectiveTab === 'draft' && (
              <DraftTab
                sections={workflowState.paper_sections ?? {}}
                outline={workflowState.paper_outline ?? {}}
              />
            )}
            {effectiveTab === 'citations' && (
              <CitationsTab
                citations={workflowState.citations ?? []}
                verifications={workflowState.citation_verification_results ?? []}
              />
            )}
            {effectiveTab === 'reviews' && (
              <ReviewsTab
                feedback={workflowState.reviewer_feedback ?? []}
                journals={workflowState.journal_recommendations ?? []}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// Tab Panel Components
// ═══════════════════════════════════════════════════════════════════════

// ── Papers Tab ────────────────────────────────────────────────────────

function PapersTab({ papers }: { papers: RetrievedPaper[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-400 font-medium">
        {papers.length} paper{papers.length !== 1 ? 's' : ''} retrieved
      </p>
      <div className="space-y-2">
        {papers.map((paper, idx) => {
          const isExpanded = expandedIdx === idx;
          return (
            <div
              key={`${paper.doi || idx}`}
              className="border border-gray-100 rounded-lg hover:border-gray-200 transition-colors"
            >
              <button
                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                className="w-full text-left px-4 py-3 flex items-start gap-3"
              >
                <span className="text-[11px] text-gray-400 font-mono tabular-nums mt-0.5 shrink-0">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <div className="flex-1 min-w-0 space-y-1">
                  <h4 className="text-sm font-medium text-gray-900 leading-snug line-clamp-2">
                    {paper.title}
                  </h4>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-400">
                    {paper.authors?.length > 0 && (
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {paper.authors.slice(0, 3).join(', ')}
                        {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
                      </span>
                    )}
                    {paper.year > 0 && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {paper.year}
                      </span>
                    )}
                    {paper.source && (
                      <span className="flex items-center gap-1">
                        <Hash className="w-3 h-3" />
                        {paper.source}
                      </span>
                    )}
                    {paper.citation_count > 0 && (
                      <span className="text-indigo-500 font-medium">
                        {paper.citation_count} citations
                      </span>
                    )}
                  </div>
                </div>
                <div className="shrink-0 mt-1">
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  )}
                </div>
              </button>

              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="px-4 pb-4 pl-12 space-y-3 border-t border-gray-50">
                      {paper.abstract && (
                        <div className="pt-3 space-y-1">
                          <h5 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">Abstract</h5>
                          <p className="text-sm text-gray-700 leading-relaxed select-text">
                            {paper.abstract}
                          </p>
                        </div>
                      )}
                      <div className="flex items-center gap-3">
                        {paper.doi && (
                          <a
                            href={`https://doi.org/${paper.doi}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                          >
                            <ExternalLink className="w-3 h-3" />
                            DOI
                          </a>
                        )}
                        {paper.url && (
                          <a
                            href={paper.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                          >
                            <ExternalLink className="w-3 h-3" />
                            Source
                          </a>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Literature Review Tab ─────────────────────────────────────────────

function LiteratureReviewTab({ review, themes }: { review: string; themes: string[] }) {
  return (
    <div className="space-y-4">
      {themes.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
            Identified Themes
          </h4>
          <div className="flex flex-wrap gap-2">
            {themes.map((theme, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-md bg-violet-50 text-violet-700 text-xs font-medium border border-violet-100"
              >
                {theme}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
          Literature Review
        </h4>
        <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap select-text prose-compact">
          {review}
        </div>
      </div>
    </div>
  );
}

// ── Gap Analysis Tab ──────────────────────────────────────────────────

function GapAnalysisTab({ gaps }: { gaps: any[] }) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-400 font-medium">
        {gaps.length} research gap{gaps.length !== 1 ? 's' : ''} identified
      </p>
      <div className="space-y-2">
        {gaps.map((gap, idx) => (
          <div
            key={idx}
            className="px-4 py-3 border border-amber-100 bg-amber-50/50 rounded-lg space-y-1"
          >
            {typeof gap === 'string' ? (
              <p className="text-sm text-gray-800 leading-relaxed select-text">{gap}</p>
            ) : (
              <>
                {gap.title && (
                  <h4 className="text-sm font-medium text-gray-900">{gap.title}</h4>
                )}
                {gap.description && (
                  <p className="text-sm text-gray-700 leading-relaxed select-text">{gap.description}</p>
                )}
                {gap.importance && (
                  <span className="inline-block text-[11px] text-amber-700 font-medium mt-1">
                    Importance: {gap.importance}
                  </span>
                )}
                {/* Fallback for unknown shape: render as JSON */}
                {!gap.title && !gap.description && typeof gap === 'object' && (
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono select-text">
                    {JSON.stringify(gap, null, 2)}
                  </pre>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Methodology Tab ───────────────────────────────────────────────────

function MethodologyTab({ suggestions, selected }: { suggestions: any[]; selected: any }) {
  return (
    <div className="space-y-4">
      {selected && (
        <div className="space-y-2">
          <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
            <FlaskConical className="w-3 h-3 text-emerald-500" />
            Selected Methodology
          </h4>
          <div className="p-4 border border-emerald-200 bg-emerald-50/50 rounded-lg">
            {typeof selected === 'string' ? (
              <p className="text-sm text-gray-800 leading-relaxed select-text">{selected}</p>
            ) : (
              <>
                {selected.name && (
                  <h4 className="text-sm font-semibold text-gray-900 mb-1">{selected.name}</h4>
                )}
                {selected.description && (
                  <p className="text-sm text-gray-700 leading-relaxed select-text">{selected.description}</p>
                )}
                {!selected.name && !selected.description && typeof selected === 'object' && (
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono select-text">
                    {JSON.stringify(selected, null, 2)}
                  </pre>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {suggestions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
            Suggested Methodologies ({suggestions.length})
          </h4>
          <div className="space-y-2">
            {suggestions.map((method, idx) => (
              <div
                key={idx}
                className="px-4 py-3 border border-gray-100 rounded-lg hover:border-gray-200 transition-colors"
              >
                {typeof method === 'string' ? (
                  <p className="text-sm text-gray-800 select-text">{method}</p>
                ) : (
                  <>
                    {method.name && (
                      <h5 className="text-sm font-medium text-gray-900 mb-1">{method.name}</h5>
                    )}
                    {method.description && (
                      <p className="text-sm text-gray-600 leading-relaxed select-text">{method.description}</p>
                    )}
                    {!method.name && !method.description && typeof method === 'object' && (
                      <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono select-text">
                        {JSON.stringify(method, null, 2)}
                      </pre>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Draft Tab ─────────────────────────────────────────────────────────

function DraftTab({ sections, outline }: { sections: Record<string, string>; outline: Record<string, any> }) {
  const sectionEntries = Object.entries(sections);
  const [expandedSection, setExpandedSection] = useState<string | null>(
    sectionEntries.length > 0 ? sectionEntries[0][0] : null
  );

  if (sectionEntries.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">
        Draft sections have not been generated yet.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Outline summary */}
      {Object.keys(outline).length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
            Paper Outline
          </h4>
          <div className="p-3 bg-gray-50 rounded-lg">
            <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono select-text">
              {JSON.stringify(outline, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Sections accordion */}
      <div className="space-y-2">
        <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
          Draft Sections ({sectionEntries.length})
        </h4>
        <div className="space-y-1">
          {sectionEntries.map(([name, content]) => {
            const isExpanded = expandedSection === name;
            return (
              <div key={name} className="border border-gray-100 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedSection(isExpanded ? null : name)}
                  className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-gray-50 transition-colors"
                >
                  <span className="text-sm font-medium text-gray-800 capitalize">
                    {name.replace(/_/g, ' ')}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[11px] text-gray-400 font-mono tabular-nums">
                      {content.split(/\s+/).length} words
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-3.5 h-3.5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
                    )}
                  </div>
                </button>
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 pb-4 border-t border-gray-50">
                        <div className="pt-3 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap select-text max-h-[400px] overflow-y-auto">
                          {content}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Citations Tab ─────────────────────────────────────────────────────

function CitationsTab({ citations, verifications }: { citations: any[]; verifications: any[] }) {
  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-400 font-medium">
        {citations.length} citation{citations.length !== 1 ? 's' : ''}
        {verifications.length > 0 && ` · ${verifications.length} verified`}
      </p>

      <div className="space-y-2">
        {citations.map((citation, idx) => (
          <div
            key={idx}
            className="px-4 py-3 border border-gray-100 rounded-lg space-y-1"
          >
            {typeof citation === 'string' ? (
              <p className="text-sm text-gray-800 select-text">{citation}</p>
            ) : (
              <>
                {(citation.citation_key || citation.key) && (
                  <span className="text-[11px] font-mono text-indigo-600 font-medium">
                    [{citation.citation_key || citation.key}]
                  </span>
                )}
                {(citation.formatted_text || citation.text || citation.title) && (
                  <p className="text-sm text-gray-700 leading-relaxed select-text">
                    {citation.formatted_text || citation.text || citation.title}
                  </p>
                )}
                {!citation.citation_key && !citation.key && !citation.formatted_text && !citation.text && !citation.title && typeof citation === 'object' && (
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono select-text">
                    {JSON.stringify(citation, null, 2)}
                  </pre>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      {/* Verification results */}
      {verifications.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
            Verification Results
          </h4>
          <div className="space-y-2">
            {verifications.map((result, idx) => (
              <div
                key={idx}
                className="px-4 py-2 border border-gray-100 rounded-lg text-sm"
              >
                {typeof result === 'string' ? (
                  <p className="text-gray-700 select-text">{result}</p>
                ) : (
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono select-text">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Reviews Tab ───────────────────────────────────────────────────────

function ReviewsTab({ feedback, journals }: { feedback: any[]; journals: any[] }) {
  return (
    <div className="space-y-6">
      {/* Reviewer Feedback */}
      {feedback.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
            <Users className="w-3 h-3 text-rose-500" />
            Simulated Peer Reviews ({feedback.length})
          </h4>
          <div className="space-y-2">
            {feedback.map((review, idx) => (
              <div
                key={idx}
                className="px-4 py-3 border border-gray-100 rounded-lg space-y-2"
              >
                {typeof review === 'string' ? (
                  <p className="text-sm text-gray-800 leading-relaxed select-text">{review}</p>
                ) : (
                  <>
                    {review.reviewer && (
                      <span className="text-[11px] font-medium text-gray-500">
                        Reviewer {review.reviewer}
                      </span>
                    )}
                    {review.score != null && (
                      <span className="ml-2 text-[11px] font-medium text-indigo-600">
                        Score: {review.score}
                      </span>
                    )}
                    {(review.feedback || review.comments || review.text) && (
                      <p className="text-sm text-gray-700 leading-relaxed select-text">
                        {review.feedback || review.comments || review.text}
                      </p>
                    )}
                    {!review.feedback && !review.comments && !review.text && !review.reviewer && typeof review === 'object' && (
                      <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono select-text">
                        {JSON.stringify(review, null, 2)}
                      </pre>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Journal Recommendations */}
      {journals.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
            <BookOpen className="w-3 h-3 text-orange-500" />
            Journal Recommendations ({journals.length})
          </h4>
          <div className="space-y-2">
            {journals.map((journal, idx) => (
              <div
                key={idx}
                className="px-4 py-3 border border-orange-100 bg-orange-50/30 rounded-lg"
              >
                {typeof journal === 'string' ? (
                  <p className="text-sm text-gray-800 select-text">{journal}</p>
                ) : (
                  <>
                    {journal.name && (
                      <h5 className="text-sm font-medium text-gray-900">{journal.name}</h5>
                    )}
                    {journal.reason && (
                      <p className="text-sm text-gray-600 leading-relaxed select-text mt-1">{journal.reason}</p>
                    )}
                    {journal.impact_factor != null && (
                      <span className="inline-block text-[11px] text-orange-700 font-medium mt-1">
                        Impact Factor: {journal.impact_factor}
                      </span>
                    )}
                    {!journal.name && !journal.reason && typeof journal === 'object' && (
                      <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono select-text">
                        {JSON.stringify(journal, null, 2)}
                      </pre>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
