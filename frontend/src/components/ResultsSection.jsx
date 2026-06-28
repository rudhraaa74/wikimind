import React, { useEffect, useRef } from 'react';
import AnswerPanel from './AnswerPanel';
import KnowledgeGraph from './KnowledgeGraph';
import PipelineTrace from './PipelineTrace';
import SkeletonLoader from './SkeletonLoader';

const ResultsSection = ({ loading, result, error }) => {
  const sectionRef = useRef(null);

  // Smooth scroll into view when this section mounts or updates
  useEffect(() => {
    if (sectionRef.current) {
      setTimeout(() => {
        sectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, []);

  return (
    <div 
      ref={sectionRef} 
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 min-h-screen animate-in fade-in duration-1000 slide-in-from-bottom-8"
    >
      {loading ? (
        <SkeletonLoader />
      ) : error ? (
        <div className="bg-space-800 border border-space-error/50 rounded-lg p-8 text-center">
          <p className="text-space-error font-medium">{error}</p>
        </div>
      ) : result ? (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="w-full lg:w-1/2">
              <AnswerPanel 
                answer={result.answer} 
                sources={result.sources} 
                retrievalSources={result.retrieval_sources}
              />
            </div>
            <div className="w-full lg:w-1/2">
              <KnowledgeGraph 
                nodes={result.graph_data?.nodes || []} 
                edges={result.graph_data?.edges || []} 
              />
            </div>
          </div>
          <PipelineTrace 
            trace={result.trace} 
            totalDuration={result.total_duration_ms} 
          />
        </div>
      ) : null}
    </div>
  );
};

export default ResultsSection;
