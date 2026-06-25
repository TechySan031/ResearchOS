'use client';

import React, { useState, useEffect } from 'react';
import { DocumentSection } from '@/types';
import { useAgentStore } from '@/stores/agentStore';
import {
  Save,
  Sparkles,
  FileText,
  RotateCw,
  Eye,
  Copy,
  Check,
  Download,
  Edit3,
  BookOpen,
} from 'lucide-react';

interface RichEditorProps {
  projectId: string;
  formattedPaper?: string;
}

export default function RichEditor({ projectId, formattedPaper }: RichEditorProps) {
  const {
    documentSections,
    fetchDocumentSections,
    updateSectionContent,
    streamingContent,
  } = useAgentStore();

  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const [editorTitle, setEditorTitle] = useState('');
  const [editorContent, setEditorContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  // Show formatted paper when no sections exist
  const showFormattedPaper = documentSections.length === 0 && !!formattedPaper;

  useEffect(() => {
    fetchDocumentSections(projectId);
  }, [projectId, fetchDocumentSections]);

  useEffect(() => {
    if (documentSections.length > 0 && !activeSectionId) {
      const firstSection = documentSections[0];
      setActiveSectionId(firstSection.id);
      setEditorTitle(firstSection.title);
      setEditorContent(firstSection.content || '');
    }
  }, [documentSections, activeSectionId]);

  const activeSection = documentSections.find(s => s.id === activeSectionId);
  const sectionType = activeSection?.section_type || '';
  const currentStreaming = streamingContent[sectionType] || '';

  useEffect(() => {
    if (currentStreaming) {
      setEditorContent(currentStreaming);
    }
  }, [currentStreaming]);

  const handleSelectSection = (section: DocumentSection) => {
    setActiveSectionId(section.id);
    setEditorTitle(section.title);
    setEditorContent(section.content || '');
    setIsEditing(false);
  };

  const handleSave = async () => {
    if (!activeSectionId) return;
    setIsSaving(true);
    try {
      await updateSectionContent(projectId, activeSectionId, editorContent);
      setIsEditing(false);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyPaper = async () => {
    if (!formattedPaper) return;
    try {
      await navigator.clipboard.writeText(formattedPaper);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  };

  const handleDownloadPaper = () => {
    if (!formattedPaper) return;
    const blob = new Blob([formattedPaper], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'formatted_paper.txt';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const wordCount = (text: string) => text.split(/\s+/).filter(Boolean).length;

  // ─── Formatted Paper Read-Only View ─────────────────────────────────
  if (showFormattedPaper) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden min-h-[500px] flex flex-col">
        {/* Toolbar */}
        <div className="h-14 bg-gray-50 border-b border-gray-200 px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md bg-indigo-100 flex items-center justify-center">
              <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
            </div>
            <div>
              <h2 className="font-semibold text-sm text-gray-900">Formatted Paper</h2>
              <p className="text-[10px] text-gray-400 font-medium">
                {wordCount(formattedPaper).toLocaleString()} words · Read-only
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyPaper}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-800 bg-white border border-gray-200 hover:bg-gray-50 rounded-md transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              onClick={handleDownloadPaper}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-800 bg-white border border-gray-200 hover:bg-gray-50 rounded-md transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Download
            </button>
          </div>
        </div>

        {/* Paper Content */}
        <div className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-3xl mx-auto text-sm text-gray-800 leading-[1.8] whitespace-pre-wrap select-text prose-compact">
            {formattedPaper}
          </div>
        </div>
      </div>
    );
  }

  // ─── Standard Section Editor ────────────────────────────────────────
  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-[500px]">
      {/* Sidebar Outline */}
      <div className="lg:col-span-1 bg-white border border-gray-200 rounded-lg p-4 flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 mb-2 flex items-center gap-1.5 select-none">
          <FileText className="w-3.5 h-3.5 text-indigo-500" />
          Document Outline
        </h3>
        {documentSections.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 gap-2">
            <Sparkles className="w-6 h-6 text-gray-300" />
            <p className="text-xs text-gray-400 text-center px-2">
              No sections generated yet. Start the research workflow to generate draft sections.
            </p>
          </div>
        ) : (
          documentSections.map((section) => {
            const isActive = section.id === activeSectionId;
            const isStreamingThis = streamingContent[section.section_type];

            return (
              <button
                key={section.id}
                onClick={() => handleSelectSection(section)}
                className={`w-full text-left px-3 py-2.5 rounded-md text-xs font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-indigo-50 border-l-2 border-indigo-500 text-indigo-700'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                } flex items-center justify-between`}
              >
                <span className="truncate flex-1">{section.title}</span>
                {isStreamingThis && (
                  <span className="flex h-2 w-2 relative ml-2 shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500" />
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>

      {/* Editor Panel */}
      <div className="lg:col-span-3 bg-white border border-gray-200 rounded-lg overflow-hidden flex flex-col min-h-[450px]">
        {activeSection ? (
          <>
            {/* Toolbar */}
            <div className="h-14 bg-gray-50 border-b border-gray-200 px-6 flex items-center justify-between shrink-0">
              <div>
                <h2 className="font-semibold text-sm text-gray-900">{editorTitle}</h2>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-500 border border-gray-200 uppercase">
                    {activeSection.section_type}
                  </span>
                  <span className="text-[10px] text-gray-400 font-mono tabular-nums">
                    {wordCount(editorContent).toLocaleString()} words
                  </span>
                  {isEditing && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-600 border border-amber-200">
                      Editing
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {currentStreaming ? (
                  <div className="flex items-center gap-1.5 text-xs text-indigo-500 font-medium">
                    <RotateCw className="w-3.5 h-3.5 animate-spin" />
                    Agent drafting...
                  </div>
                ) : isEditing ? (
                  <>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={isSaving}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-xs font-semibold transition-all disabled:opacity-50"
                    >
                      <Save className="w-3.5 h-3.5" />
                      {isSaving ? 'Saving...' : 'Save'}
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 hover:bg-gray-50 text-gray-600 rounded-md text-xs font-medium transition-all"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Edit
                  </button>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 p-6 flex flex-col bg-white">
              {isEditing ? (
                <textarea
                  value={editorContent}
                  onChange={(e) => setEditorContent(e.target.value)}
                  className="flex-1 w-full bg-transparent text-sm text-gray-800 font-sans leading-relaxed resize-none focus:outline-none placeholder-gray-300 selection:bg-indigo-100"
                  placeholder="Write section content in markdown..."
                />
              ) : (
                <div className="flex-1 overflow-y-auto text-sm text-gray-800 font-sans leading-[1.8] whitespace-pre-wrap select-text prose-compact selection:bg-indigo-100">
                  {editorContent || (
                    <div className="h-full flex flex-col items-center justify-center text-gray-400 select-none gap-2">
                      <Sparkles className="w-6 h-6 text-gray-300" />
                      <p className="text-xs text-center">
                        Section is empty. Run the workflow to generate content, or click Edit to write manually.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-gray-400 select-none">
            <FileText className="w-8 h-8 text-gray-300" />
            <p className="text-sm font-medium">Select a section from the outline</p>
          </div>
        )}
      </div>
    </div>
  );
}
