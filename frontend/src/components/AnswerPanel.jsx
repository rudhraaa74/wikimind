import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

const AnswerPanel = ({ answer, sources, retrievalSources }) => {
  const hasNeo4j = retrievalSources?.includes("Neo4j");
  const hasPinecone = retrievalSources?.includes("Pinecone");

  return (
    <div className="bg-space-800 border border-space-border rounded-lg p-6 flex flex-col h-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-space-muted m-0">ANSWER</h2>
        <div className="flex gap-2">
          {hasNeo4j && (
            <span className="bg-space-accent/10 border border-space-accent/30 text-space-accent text-[10px] px-2 py-1 rounded font-bold uppercase tracking-wider">
              NEO4J GRAPH
            </span>
          )}
          {hasPinecone && (
            <span className="bg-[#a855f7]/10 border border-[#a855f7]/30 text-[#a855f7] text-[10px] px-2 py-1 rounded font-bold uppercase tracking-wider">
              PINECONE VECTOR
            </span>
          )}
        </div>
      </div>

      <div className="prose prose-invert prose-headings:text-white prose-p:text-slate-300 prose-strong:text-white prose-li:text-slate-300 max-w-none flex-1">
        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[[rehypeKatex, { output: 'html' }]]}>{answer}</ReactMarkdown>
      </div>

      {sources && sources.length > 0 && (
        <div className="mt-8 pt-6 border-t border-space-border">
          <h3 className="text-[10px] font-semibold uppercase tracking-widest text-space-muted mb-3">SOURCES</h3>
          <div className="flex flex-wrap gap-2">
            {sources.map((source, idx) => (
              <a
                key={idx}
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 border border-space-border rounded text-xs text-space-muted hover:text-white hover:border-space-accent transition-colors truncate max-w-[200px]"
                title={source.title}
              >
                {source.title}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnswerPanel;
