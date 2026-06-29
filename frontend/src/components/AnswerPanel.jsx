import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

const AnswerPanel = ({ answer, sources, retrievalSources }) => {
  const hasNeo4j = retrievalSources?.includes("Neo4j");
  const hasPinecone = retrievalSources?.includes("Pinecone");

  return (
    <div className="bg-[#07080f]/85 backdrop-blur-[12px] border border-white/[0.08] rounded-2xl p-8 flex flex-col h-full shadow-2xl">
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

      <div className="max-w-none flex-1 mt-4">
        <ReactMarkdown 
          remarkPlugins={[remarkMath]} 
          rehypePlugins={[[rehypeKatex, { output: 'html' }]]}
          components={{
            h1: ({node, ...props}) => <h1 className="text-2xl font-bold text-white border-b border-white/20 pb-2 mb-4 mt-8" {...props} />,
            h2: ({node, ...props}) => <h2 className="text-xl font-bold text-white border-b border-white/20 pb-2 mb-4 mt-8" {...props} />,
            h3: ({node, ...props}) => <h3 className="text-lg font-bold text-white border-b border-white/20 pb-2 mb-4 mt-8" {...props} />,
            p: ({node, ...props}) => <p className="text-slate-300 leading-[1.8] mb-6 first-of-type:text-[1.1rem] first-of-type:text-slate-200" {...props} />,
            ul: ({node, ...props}) => <ul className="space-y-3 mb-6" {...props} />,
            ol: ({node, ...props}) => <ol className="list-decimal pl-5 space-y-3 mb-6 text-slate-300 leading-[1.8]" {...props} />,
            li: ({node, ...props}) => (
              <li className="flex items-start gap-3 text-slate-300 leading-[1.8]">
                <span className="text-white mt-1.5 opacity-60 text-[10px]">●</span>
                <span className="flex-1">{props.children}</span>
              </li>
            ),
            a: ({node, ...props}) => {
              // Style citation links
              if (props.href?.startsWith('#source-')) {
                return <sup className="text-indigo-400 font-bold ml-0.5 text-xs">{props.children}</sup>;
              }
              return <a className="text-indigo-400 hover:underline" {...props} />;
            },
            strong: ({node, ...props}) => <strong className="text-white font-semibold" {...props} />
          }}
        >
          {answer?.replace(/\[(\d+)\]/g, '[$1](#source-$1)')}
        </ReactMarkdown>
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
