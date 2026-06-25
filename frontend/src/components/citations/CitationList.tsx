'use client';

import React, { useState, useEffect } from 'react';
import { Paper, Citation } from '@/types';
import { useAgentStore } from '@/stores/agentStore';
import { 
  BookOpen, 
  ExternalLink, 
  CheckCircle2, 
  AlertCircle, 
  HelpCircle,
  Hash,
  UploadCloud,
  FilePlus2,
  Bookmark
} from 'lucide-react';
import { api } from '@/lib/api';

interface CitationListProps {
  projectId: string;
}

export default function CitationList({ projectId }: CitationListProps) {
  const { papers, citations, fetchPapers, fetchCitations } = useAgentStore();
  const [activeTab, setActiveTab] = useState<'papers' | 'citations'>('papers');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchPapers(projectId);
    fetchCitations(projectId);
  }, [projectId, fetchPapers, fetchCitations]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadMessage(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Endpoint `/api/v1/projects/{project_id}/papers/upload`
      const res = await fetch(`${api.baseUrl}/api/v1/projects/${projectId}/papers/upload`, {
        method: 'POST',
        body: formData,
      });
      
      if (!res.ok) {
        throw new Error('Upload failed');
      }

      const data = await res.json();
      setUploadMessage(data.message || 'File uploaded successfully!');
      fetchPapers(projectId);
    } catch (err: any) {
      setUploadMessage(`Error: ${err.message || 'Failed to upload PDF'}`);
    } finally {
      setIsUploading(false);
    }
  };

  const citationStatusIcons = {
    verified: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />,
    failed: <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />,
    unverified: <HelpCircle className="w-4 h-4 text-amber-400 shrink-0" />,
  };

  const citationStatusStyles = {
    verified: 'border-emerald-500/20 bg-emerald-950/10 text-emerald-400',
    failed: 'border-red-500/20 bg-red-950/10 text-red-400',
    unverified: 'border-amber-500/20 bg-amber-950/10 text-amber-400',
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 min-h-[500px]">
      {/* Upload and controls card (left) */}
      <div className="lg:col-span-1 space-y-6">
        {/* PDF Ingestion Card */}
        <div className="glass-panel border border-zinc-800/40 rounded-xl p-6 space-y-4 select-none">
          <h3 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
            <UploadCloud className="w-4 h-4 text-violet-400" />
            PDF Ingestion & Indexing
          </h3>
          <p className="text-[11px] text-zinc-500 leading-relaxed">
            Upload custom academic papers (PDFs) to include them in the project RAG vector database. 
            They will be chunked, embedded, and mapped into vector index stores.
          </p>

          <label className={`border-2 border-dashed border-zinc-800/80 rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer hover:border-violet-500/30 transition-all duration-300 ${
            isUploading ? 'opacity-50 pointer-events-none' : ''
          }`}>
            <FilePlus2 className="w-8 h-8 text-zinc-600 mb-2" />
            <span className="text-xs font-semibold text-zinc-300">Select academic PDF</span>
            <span className="text-[9px] text-zinc-500 mt-1">Maximum size: 25MB</span>
            <input 
              type="file" 
              accept=".pdf" 
              onChange={handleFileUpload} 
              className="hidden" 
            />
          </label>

          {isUploading && (
            <div className="flex items-center justify-center gap-2 text-xs text-violet-400">
              <span className="w-4 h-4 border-2 border-t-transparent border-violet-500 rounded-full animate-spin" />
              Ingesting and indexing PDF...
            </div>
          )}

          {uploadMessage && (
            <p className={`p-2.5 rounded-lg text-[10px] font-semibold border ${
              uploadMessage.startsWith('Error') 
                ? 'border-red-500/10 bg-red-950/10 text-red-400' 
                : 'border-emerald-500/10 bg-emerald-950/10 text-emerald-400'
            }`}>
              {uploadMessage}
            </p>
          )}
        </div>
      </div>

      {/* Main Table view of Papers/Citations (right) */}
      <div className="lg:col-span-2 glass-panel border border-zinc-800/40 rounded-xl flex flex-col h-[500px]">
        {/* Navigation Tabs */}
        <div className="h-14 bg-zinc-950/40 border-b border-zinc-800/20 px-6 flex items-center justify-between">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('papers')}
              className={`pb-4 pt-4 px-2 text-xs font-semibold tracking-wide border-b-2 transition-all select-none ${
                activeTab === 'papers'
                  ? 'border-violet-500 text-white'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              Retrieved Papers ({papers.length})
            </button>
            <button
              onClick={() => setActiveTab('citations')}
              className={`pb-4 pt-4 px-2 text-xs font-semibold tracking-wide border-b-2 transition-all select-none ${
                activeTab === 'citations'
                  ? 'border-violet-500 text-white'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              Citation Grounding ({citations.length})
            </button>
          </div>
        </div>

        {/* Tab contents list scroll container */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#030409]">
          {activeTab === 'papers' ? (
            papers.length === 0 ? (
              <div className="h-full flex items-center justify-center text-zinc-600 italic select-none">
                No papers indexed yet. Start the research retrieval agent...
              </div>
            ) : (
              <div className="space-y-4">
                {papers.map((paper) => (
                  <div key={paper.id} className="glass-card rounded-lg p-4 flex gap-4 items-start select-text">
                    <div className="p-2 rounded bg-zinc-900 border border-zinc-800 text-violet-400">
                      <BookOpen className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <h4 className="font-semibold text-xs text-zinc-200 leading-snug break-words">
                        {paper.title}
                      </h4>
                      <p className="text-[10px] text-zinc-500 truncate font-medium">
                        Authors: {Array.isArray(paper.authors) ? paper.authors.join(', ') : 'Unknown'}
                      </p>
                      <div className="flex items-center gap-3 text-[9px] font-semibold text-zinc-600 uppercase tracking-wider">
                        <span>Source: {paper.source}</span>
                        {paper.year && <span>Year: {paper.year}</span>}
                        {paper.doi && (
                          <span className="flex items-center gap-0.5 truncate">
                            DOI: {paper.doi}
                          </span>
                        )}
                      </div>
                    </div>
                    {paper.url && (
                      <a 
                        href={paper.url} 
                        target="_blank" 
                        rel="noreferrer"
                        className="p-1 rounded text-zinc-600 hover:text-violet-400 hover:bg-violet-600/10 transition-all shrink-0"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )
          ) : (
            citations.length === 0 ? (
              <div className="h-full flex items-center justify-center text-zinc-600 italic select-none">
                No citation links mapped to generated claims yet.
              </div>
            ) : (
              <div className="space-y-4">
                {citations.map((citation) => (
                  <div 
                    key={citation.id} 
                    className={`border rounded-lg p-4 flex gap-4 items-start select-text ${citationStatusStyles[citation.status] || 'border-zinc-800'}`}
                  >
                    <div className="p-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
                      <Bookmark className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-zinc-200">
                          [{citation.citation_key}]
                        </span>
                        <span className="text-[9px] font-semibold uppercase tracking-wider">
                          Status: {citation.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-zinc-400 leading-relaxed font-sans mt-1">
                        {citation.formatted_text || 'No formatted citation details recorded.'}
                      </p>
                    </div>
                    {citationStatusIcons[citation.status]}
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
