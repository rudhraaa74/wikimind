import React from 'react';

const SuggestedQueries = ({ onSelect, isLoading }) => {
  const queries = [
    "BLACK HOLES",
    "NEUTRON STARS",
    "JAMES WEBB TELESCOPE",
    "SUPERNOVAE"
  ];

  return (
    <div className="flex flex-wrap justify-center gap-4 mt-8 pb-12">
      {queries.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          disabled={isLoading}
          className="px-6 py-2 border border-space-border rounded text-xs font-semibold tracking-widest text-space-muted hover:text-white hover:border-space-accent transition-colors disabled:opacity-50 disabled:cursor-not-allowed uppercase"
        >
          {q}
        </button>
      ))}
    </div>
  );
};

export default SuggestedQueries;
