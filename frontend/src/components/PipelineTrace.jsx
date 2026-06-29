import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ArrowRight, Zap } from 'lucide-react';

const PipelineTrace = ({ trace, totalDuration }) => {
  const [expanded, setExpanded] = useState(false);

  if (!trace || trace.length === 0) return null;

  const hasCache = trace.some(step => step.detail.toLowerCase().includes('skipped') || step.detail.toLowerCase().includes('reusing'));
  const isError = trace.some(step => step.detail.toLowerCase().includes('fail') || step.detail.toLowerCase().includes('error'));
  
  return (
    <div className="mt-6 flex flex-col pt-4">
      {/* Header / Summary Row */}
      <div 
        className="py-4 flex items-center justify-between cursor-pointer group transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-space-muted m-0">PIPELINE TRACE</h3>
          <div className="flex items-center gap-2 text-sm text-space-muted ml-4 border-l border-space-border pl-4">
            <span>Completed in {(totalDuration / 1000).toFixed(2)}s</span>
            {hasCache && (
              <div className="flex items-center gap-1.5 ml-2 opacity-80">
                <Zap className="w-3.5 h-3.5 text-space-cached fill-space-cached/20" />
                <span className="text-[11px] text-space-cached font-medium tracking-wide uppercase">Fast Cache</span>
              </div>
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
        <div className="py-6 overflow-x-auto">
          <div className="flex items-stretch min-w-max pb-2">
            {trace.map((step, idx) => {
              const isStepCached = step.detail.toLowerCase().includes('skipped') || step.detail.toLowerCase().includes('reusing');
              const isStepError = step.detail.toLowerCase().includes('fail') || step.detail.toLowerCase().includes('error');
              
              let dotColor = 'bg-space-success';
              if (isStepError) dotColor = 'bg-space-error';
              else if (isStepCached) dotColor = 'bg-space-cached';

              return (
                <React.Fragment key={idx}>
                  {/* Step Card */}
                  <div className="flex flex-col w-[220px] flex-shrink-0 bg-space-900/40 rounded-lg p-4 border border-space-border/50">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${dotColor}`}></div>
                        <span className="font-semibold text-white text-sm">{step.step}</span>
                      </div>
                    </div>
                    <p className="text-xs text-space-muted leading-relaxed mb-3 flex-grow">
                      {step.detail}
                    </p>
                    <div className="text-[11px] text-space-muted font-medium bg-space-800 inline-block px-2 py-1 rounded-md self-start border border-space-border">
                      {step.duration_ms}ms
                    </div>
                  </div>

                  {/* Arrow connector */}
                  {idx < trace.length - 1 && (
                    <div className="flex items-center justify-center px-3 flex-shrink-0">
                      <ArrowRight className="w-5 h-5 text-space-border" />
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PipelineTrace;
