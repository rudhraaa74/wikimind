import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const PipelineTrace = ({ trace, totalDuration }) => {
  const [expanded, setExpanded] = useState(false);

  if (!trace || trace.length === 0) return null;

  const hasCache = trace.some(step => step.detail.toLowerCase().includes('skipped') || step.detail.toLowerCase().includes('reusing'));
  const isError = trace.some(step => step.detail.toLowerCase().includes('fail') || step.detail.toLowerCase().includes('error'));
  
  return (
    <div className="mt-6 bg-space-800 border border-space-border rounded-lg overflow-hidden">
      {/* Header / Summary Row */}
      <div 
        className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-space-900/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-space-muted m-0">PIPELINE TRACE</h3>
          <div className="flex items-center gap-2 text-sm text-space-muted ml-4 border-l border-space-border pl-4">
            <span>Completed in {(totalDuration / 1000).toFixed(2)}s</span>
            {hasCache && (
              <span className="bg-space-cached/20 text-space-cached text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                Cached
              </span>
            )}
            {isError && (
              <span className="bg-space-error/20 text-space-error text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                Error
              </span>
            )}
          </div>
        </div>
        <button className="text-space-muted hover:text-white transition-colors">
          {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      </div>

      {/* Expanded Content */}
      <div 
        className={`transition-all duration-500 ease-in-out ${expanded ? 'max-h-[1000px] opacity-100' : 'max-h-0 opacity-0'}`}
      >
        <div className="p-6 pt-2 border-t border-space-border">
          <div className="space-y-4">
            {trace.map((step, idx) => {
              const isStepCached = step.detail.toLowerCase().includes('skipped') || step.detail.toLowerCase().includes('reusing');
              const isStepError = step.detail.toLowerCase().includes('fail') || step.detail.toLowerCase().includes('error');
              
              let dotColor = 'bg-space-success';
              if (isStepError) dotColor = 'bg-space-error';
              else if (isStepCached) dotColor = 'bg-space-cached';

              return (
                <div key={idx} className="flex items-start gap-4">
                  <div className="mt-1.5">
                    <div className={`w-2.5 h-2.5 rounded-full ${dotColor}`}></div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white">{step.step}</span>
                      <span className="text-space-muted text-sm font-mono">{step.duration_ms}ms</span>
                    </div>
                    <p className="text-sm text-space-muted mt-1">{step.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PipelineTrace;
